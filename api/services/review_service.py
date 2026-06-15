"""Сервис очереди верификации (b30 · §11.0–§11.2, §11.4).

Каждый инцидент `v_incidents` получает статус ревью `pending|validated|dismissed`.
**Источник истины статуса — ТОЛЬКО журнал `output/review_queue.csv`** (паттерн
`actions_service`/`actions.csv`, §11.0): колонки `decided_at,incident_id,decision,note`,
append-only, статус = **последняя** запись по `incident_id`; нет записи → `pending`.
Легаси-экшен `validate` из §3.4 (`actions.csv`) НЕ трогаем — двух источников статуса
ревью быть не должно (§11.0).

`decided_at` пишет сервер при записи (прецедент `actions_service.record`) — в чтении
очереди времени нет, детерминизм чтения сохраняется. Битая строка журнала (мало
колонок/мусорный decision) пропускается, не роняет ответ (§11.4).
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import duckdb

from api.core.config import settings
from api.domain.review import (
    ReviewCounts,
    ReviewDecision,
    ReviewItem,
    ReviewQueue,
    ReviewStatus,
)
from api.repositories import rows_to_dicts
from api.services import consistency_service, metrics_service

# Имя события для эмиттера b25 (§11.1) — пишем литералом, metrics_service не трогаем.
_EVENT_REVIEW_DECISION = "review_decision"

_CSV_COLUMNS = ["decided_at", "incident_id", "decision", "note"]

# Поля инцидента для ReviewItem (§11.2) — берём только нужное из v_incidents.
_INCIDENT_COLUMNS = (
    '"id", "alarm_code", "severity", "vehicle_plate", "ts", "video_available"'
)


def _review_csv_path() -> Path:
    return settings.output_dir / "review_queue.csv"


def _ensure_csv() -> Path:
    """Гарантирует существование output/review_queue.csv с заголовком."""
    path = _review_csv_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(_CSV_COLUMNS)
    return path


def _read_decisions() -> dict[str, dict]:
    """Сворачивает журнал в `incident_id -> {decision, note, decided_at}`.

    Последняя запись по `incident_id` побеждает (append-only, §11.0). Битые строки
    (мало колонок или неизвестный `decision`) пропускаются (§11.4). Пустой/
    отсутствующий журнал → пустой словарь (все инциденты станут `pending`).
    """
    path = _review_csv_path()
    decisions: dict[str, dict] = {}
    if not path.exists():
        return decisions
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 4:
                continue  # битая строка (§11.4)
            decided_at, incident_id, decision, note = row[0], row[1], row[2], row[3]
            if decision not in ("validated", "dismissed"):
                continue  # заголовок или мусорный decision
            decisions[incident_id] = {
                "decided_at": decided_at,
                "decision": decision,
                "note": note or None,  # пустая note → null (§11.4)
            }
    return decisions


def _to_item(row: dict, decision: Optional[dict]) -> ReviewItem:
    """Строит ReviewItem из строки v_incidents + (опц.) записи журнала."""
    status: ReviewStatus = decision["decision"] if decision else "pending"
    return ReviewItem(
        incident_id=str(row["id"]),
        alarm_code=row["alarm_code"],
        severity=row["severity"],
        vehicle_plate=row["vehicle_plate"],
        ts=str(row["ts"]),
        video_available=bool(row["video_available"]),
        status=status,
        note=decision["note"] if decision else None,
        decided_at=decision["decided_at"] if decision else None,
    )


def _incident_row(db: duckdb.DuckDBPyConnection, incident_id: str) -> Optional[dict]:
    rows = rows_to_dicts(
        db.execute(
            f'SELECT {_INCIDENT_COLUMNS} FROM "v_incidents" WHERE "id" = ? LIMIT 1',
            [incident_id],
        )
    )
    return rows[0] if rows else None


def queue(
    db: duckdb.DuckDBPyConnection, status: Optional[ReviewStatus] = None
) -> ReviewQueue:
    """Очередь верификации (§11.1): все инциденты `v_incidents` + статус из журнала.

    `counts` считаются по ВСЕМ инцидентам (не по фильтру) — сумма == числу строк
    `v_incidents` (§11.2, не хардкод). Фильтр `status` сужает только `items`.
    `evidence_rate` берётся из `consistency_service.report()` (§10, b28), не
    пересчитывается здесь.
    """
    decisions = _read_decisions()
    counts = {"pending": 0, "validated": 0, "dismissed": 0}
    items: list[ReviewItem] = []
    for row in rows_to_dicts(
        db.execute(
            # ORDER BY обязателен — детерминизм ответа (§11.2, §3 чек-листа).
            # "ts" DESC — как список инцидентов (incidents_repo); "id" — тай-брейк.
            f'SELECT {_INCIDENT_COLUMNS} FROM "v_incidents" '
            'ORDER BY "ts" DESC, "id"'
        )
    ):
        item = _to_item(row, decisions.get(str(row["id"])))
        counts[item.status] += 1  # счётчики — по всем (до фильтра)
        items.append(item)

    if status is not None:
        items = [i for i in items if i.status == status]

    evidence_rate = consistency_service.report(db).evidence_rate
    return ReviewQueue(
        items=items, counts=ReviewCounts(**counts), evidence_rate=evidence_rate
    )


def decide(
    db: duckdb.DuckDBPyConnection,
    incident_id: str,
    decision: ReviewDecision,
    note: Optional[str] = None,
) -> Optional[ReviewItem]:
    """Записать решение по инциденту (§11.1). `None` → инцидента нет в v_incidents (404).

    Пишет строку в журнал (`decided_at` ставит сервер), затем best-effort эмит
    `review_decision` в `ai_metric_events` через эмиттер b25; недоступность/
    исключение эмиттера — тихий no-op, решение уже записано (§11.1).
    """
    row = _incident_row(db, incident_id)
    if row is None:
        return None  # роутер → 404 (§11.1)

    decided_at = datetime.now(timezone.utc).isoformat()
    path = _ensure_csv()
    with path.open("a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([decided_at, incident_id, decision, note or ""])

    # Эмит события — fire-and-forget: метрики не должны ронять решение (§11.1).
    try:
        metrics_service.track_event(
            _EVENT_REVIEW_DECISION,
            incident_id=incident_id,
            source=decision,
        )
    except Exception:  # noqa: BLE001 — эмит метрики не критичен (§11.1)
        pass

    return _to_item(
        row,
        {"decided_at": decided_at, "decision": decision, "note": note or None},
    )


def reset_state() -> None:
    """Сброс журнала (для тестов; прецедент `actions_service.reset_overrides`).

    Источник истины — CSV, поэтому «сброс» = удаление журнала → все `pending`.
    """
    path = _review_csv_path()
    if path.exists():
        path.unlink()
