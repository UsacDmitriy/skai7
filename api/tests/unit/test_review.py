"""Unit-покрытие очереди верификации (b30) — §11.0–§11.4.

Статусная модель ревью инцидента: источник истины — ТОЛЬКО журнал
`output/review_queue.csv` (§11.0), последняя запись по `incident_id` побеждает,
нет записи → `pending`. Это НЕ AI-фича: без сети/ML, чтение детерминировано
(`decided_at` пишет сервер при записи, в чтении времени нет).

Изоляция (Check tu-review): журнал — только в `tmp_path` (`settings.output_dir`
переопределён), между тестами `review_service.reset_state()` (прецедент
`actions_service.reset_overrides`). Эмиттер метрик b25 нейтрализован (no-op),
`v_incidents`/`evidence_rate` — синтетические in-memory (без `make db`, без сети).
"""

from __future__ import annotations

import csv
from pathlib import Path
from types import SimpleNamespace
from typing import Callable, Iterator

import pytest

from api.services import review_service as rs

# Синтетические инциденты `v_incidents` (§11.2: id, alarm_code, severity,
# vehicle_plate, ts, video_available) — детерминированный набор из 4 строк.
_INCIDENTS = [
    {
        "id": "12345",
        "alarm_code": "DMS_DROWSY",
        "severity": "critical",
        "vehicle_plate": "T780РН198",
        "ts": "2026-05-14T08:12:00Z",
        "video_available": True,
    },
    {
        "id": "12346",
        "alarm_code": "ADAS_FCW",
        "severity": "high",
        "vehicle_plate": "A123ВС777",
        "ts": "2026-05-14T09:00:00Z",
        "video_available": False,
    },
    {
        "id": "12347",
        "alarm_code": "DMS_PHONE",
        "severity": "medium",
        "vehicle_plate": "К456ОР198",
        "ts": "2026-05-14T10:30:00Z",
        "video_available": True,
    },
    {
        "id": "12348",
        "alarm_code": "ADAS_LDW",
        "severity": "low",
        "vehicle_plate": "М789ТУ716",
        "ts": "2026-05-14T11:45:00Z",
        "video_available": False,
    },
]
_TOTAL = len(_INCIDENTS)
_EVIDENCE_RATE = 0.875  # фиксируем «контекст очереди» из §10 для проверки прозрачности


@pytest.fixture
def incidents_db(mem_db, load_rows) -> object:
    """In-memory DuckDB с синтетическим `v_incidents` (без `make db`)."""
    load_rows(mem_db, "v_incidents", _INCIDENTS)
    return mem_db


@pytest.fixture
def review_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Path]:
    """Журнал — только в tmp; эмиттер метрик и evidence_rate нейтрализованы.

    Источник истины статуса — CSV под `settings.output_dir`; переопределяем его
    на `tmp_path` и сбрасываем состояние (`reset_state()`) до и после теста, чтобы
    тесты не делили журнал. `consistency_service.report` подменён на лёгкий стаб
    (evidence_rate фиксирован) — синтетический `v_incidents` не несёт view §10.
    `metrics_service.track_event` → no-op: эмит b25 не должен трогать реальную БД.
    """
    from api.core.config import settings

    monkeypatch.setattr(settings, "output_dir", tmp_path)
    monkeypatch.setattr(
        rs.consistency_service,
        "report",
        lambda db: SimpleNamespace(evidence_rate=_EVIDENCE_RATE),
    )
    monkeypatch.setattr(
        rs.metrics_service, "track_event", lambda *a, **k: True
    )
    rs.reset_state()
    try:
        yield tmp_path
    finally:
        rs.reset_state()


@pytest.fixture
def review_client(incidents_db, review_env) -> Iterator[object]:
    """`TestClient` с `get_db`, подменённым на синтетический `incidents_db`.

    `review_env` уже изолировал журнал/эмиттер/evidence_rate (порядок важен).
    """
    from fastapi.testclient import TestClient

    from api.core.duckdb_conn import get_db
    from api.main import app

    app.dependency_overrides[get_db] = lambda: incidents_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


def _journal_rows(tmp_path: Path) -> list[list[str]]:
    """Строки журнала `review_queue.csv` без заголовка (или [] если файла нет)."""
    path = tmp_path / "review_queue.csv"
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    return rows[1:] if rows else []  # отрезаем строку-заголовок


# ---------------------------------------------------------------------------
# Пустой журнал — все pending; согласованность items/counts (§11.0, §11.2).
# ---------------------------------------------------------------------------


def test_empty_journal_all_pending(incidents_db, review_env) -> None:
    """Нет журнала → все инциденты `pending`; len(items)=число строк v_incidents."""
    q = rs.queue(incidents_db)

    assert len(q.items) == _TOTAL
    assert all(i.status == "pending" for i in q.items)
    assert q.counts.pending == _TOTAL
    assert q.counts.validated == 0 and q.counts.dismissed == 0


def test_counts_sum_equals_total(incidents_db, review_env) -> None:
    """Сумма `counts` == всего инцидентов (§11.2, не хардкод)."""
    q = rs.queue(incidents_db)

    assert q.counts.pending + q.counts.validated + q.counts.dismissed == _TOTAL


# ---------------------------------------------------------------------------
# decide() — запись в журнал, статус, note, decided_at (§11.1).
# ---------------------------------------------------------------------------


def test_decide_writes_row_and_status(incidents_db, review_env) -> None:
    """`decide(...,'validated','ок')` → строка в CSV, статус/note/decided_at заполнены."""
    item = rs.decide(incidents_db, "12345", "validated", "ок")

    assert item is not None
    assert item.incident_id == "12345"
    assert item.status == "validated"
    assert item.note == "ок"
    assert item.decided_at  # непустой — ставит сервер при записи

    rows = _journal_rows(review_env)
    assert len(rows) == 1
    decided_at, incident_id, decision, note = rows[0]
    assert (incident_id, decision, note) == ("12345", "validated", "ок")
    assert decided_at  # сервер записал время


def test_decide_status_visible_in_queue(incidents_db, review_env) -> None:
    """После `decide` статус инцидента виден в `queue()` (журнал — источник истины)."""
    rs.decide(incidents_db, "12345", "validated", "ок")

    q = rs.queue(incidents_db)
    decided = next(i for i in q.items if i.incident_id == "12345")
    assert decided.status == "validated" and decided.note == "ок"
    assert q.counts.validated == 1 and q.counts.pending == _TOTAL - 1


def test_empty_note_is_valid_and_null(incidents_db, review_env) -> None:
    """Пустая `note` валидна (§11.4) и нормализуется в `None`."""
    item = rs.decide(incidents_db, "12346", "dismissed")

    assert item is not None
    assert item.status == "dismissed"
    assert item.note is None


# ---------------------------------------------------------------------------
# Перезапись — append-only журнал, побеждает последняя; в counts один раз (§11.0).
# ---------------------------------------------------------------------------


def test_overwrite_last_wins(incidents_db, review_env) -> None:
    """`validated` затем `dismissed` по одному id → статус `dismissed`, в counts один раз."""
    rs.decide(incidents_db, "12345", "validated", "первое")
    rs.decide(incidents_db, "12345", "dismissed", "второе")

    q = rs.queue(incidents_db)
    item = next(i for i in q.items if i.incident_id == "12345")
    assert item.status == "dismissed" and item.note == "второе"

    # журнал append-only — обе строки на месте...
    assert len(_journal_rows(review_env)) == 2
    # ...но в counts инцидент учтён ровно один раз (сумма = всего).
    assert q.counts.dismissed == 1 and q.counts.validated == 0
    assert q.counts.pending + q.counts.validated + q.counts.dismissed == _TOTAL


# ---------------------------------------------------------------------------
# Фильтр по статусу — сужает items, counts остаются по всем (§11.2).
# ---------------------------------------------------------------------------


def test_filter_status_pending(incidents_db, review_env) -> None:
    """Фильтр `status='pending'` отдаёт только pending; `counts` — по всем (не по фильтру)."""
    rs.decide(incidents_db, "12345", "validated")
    rs.decide(incidents_db, "12346", "dismissed")

    q = rs.queue(incidents_db, status="pending")

    assert all(i.status == "pending" for i in q.items)
    assert len(q.items) == _TOTAL - 2
    # counts — по всем инцидентам, не по отфильтрованным items.
    assert q.counts.validated == 1 and q.counts.dismissed == 1
    assert q.counts.pending == _TOTAL - 2
    assert q.counts.pending + q.counts.validated + q.counts.dismissed == _TOTAL


# ---------------------------------------------------------------------------
# Негативы API-уровня — 404 / 422 (TestClient, §11.1, §11.4).
# ---------------------------------------------------------------------------


def test_unknown_incident_404(review_client) -> None:
    """Неизвестный `incident_id` → 404 (API-уровень)."""
    resp = review_client.post(
        "/api/review-queue/__nope__", json={"decision": "validated"}
    )
    assert resp.status_code == 404


def test_invalid_decision_422(review_client) -> None:
    """`decision='maybe'` → 422 (Literal в Pydantic, до сервиса)."""
    resp = review_client.post(
        "/api/review-queue/12345", json={"decision": "maybe"}
    )
    assert resp.status_code == 422


def test_decide_unknown_incident_returns_none(incidents_db, review_env) -> None:
    """Сервисный слой: неизвестный id → `None` (роутер превратит в 404), журнал пуст."""
    assert rs.decide(incidents_db, "__nope__", "validated") is None
    assert _journal_rows(review_env) == []


# ---------------------------------------------------------------------------
# Битая строка журнала — пропущена, сервис не падает (§11.4).
# ---------------------------------------------------------------------------


def test_broken_journal_line_skipped(incidents_db, review_env) -> None:
    """Битая строка (`x,y`) в журнале пропускается, валидное решение читается."""
    rs.decide(incidents_db, "12345", "validated", "ок")

    # вручную дописываем мусорную строку с недостатком колонок
    with (review_env / "review_queue.csv").open(
        "a", newline="", encoding="utf-8"
    ) as f:
        f.write("x,y\n")

    q = rs.queue(incidents_db)  # не должно падать

    assert len(q.items) == _TOTAL
    item = next(i for i in q.items if i.incident_id == "12345")
    assert item.status == "validated"
    assert q.counts.validated == 1 and q.counts.pending == _TOTAL - 1


# ---------------------------------------------------------------------------
# evidence_rate — из consistency_service.report(), не пересчитан (§11.2, §10).
# ---------------------------------------------------------------------------


def test_evidence_rate_from_consistency_report(incidents_db, review_env) -> None:
    """`evidence_rate` в ответе == значению из `consistency_service.report()`."""
    q = rs.queue(incidents_db)

    assert q.evidence_rate == _EVIDENCE_RATE


# ---------------------------------------------------------------------------
# Деградация эмиттера метрик — decide всё равно пишет решение (§11.1).
# ---------------------------------------------------------------------------


def test_metrics_emitter_failure_does_not_block_decision(
    incidents_db, review_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Эмиттер b25 кидает исключение → `decide` всё равно записывает решение (no-op)."""
    def _boom(*a, **k):
        raise RuntimeError("metrics down")

    monkeypatch.setattr(rs.metrics_service, "track_event", _boom)

    item = rs.decide(incidents_db, "12345", "validated", "несмотря на метрики")

    assert item is not None and item.status == "validated"
    rows = _journal_rows(review_env)
    assert len(rows) == 1 and rows[0][1] == "12345"


# ---------------------------------------------------------------------------
# Единый словарь — actions.csv не трогается операциями ревью (§11.0).
# ---------------------------------------------------------------------------


def test_actions_csv_untouched_by_review(incidents_db, review_env) -> None:
    """`actions.csv` не появляется/не меняется от операций ревью (§11.0: единый словарь)."""
    actions_path = review_env / "actions.csv"
    assert not actions_path.exists()  # старт — чисто

    rs.decide(incidents_db, "12345", "validated", "ок")
    rs.decide(incidents_db, "12346", "dismissed")
    rs.queue(incidents_db)

    # ревью пишет ТОЛЬКО review_queue.csv; actions.csv не создан.
    assert not actions_path.exists()
    assert (review_env / "review_queue.csv").exists()
