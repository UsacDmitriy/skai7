"""Журнал действий (§3.4): запись в output/actions.csv + статус инцидента.

POST /api/actions меняет `status` инцидента. Отдельной таблицы нет — **источник
истины статуса — журнал `output/actions.csv`** (паттерн `review_service`): статус
пишется в колонку `status`, при чтении журнал сворачивается «последняя запись по
`incident_id` побеждает». Это переживает multi-worker (`api-prod`, `api_workers=0`):
воркер, не писавший действие, читает статус из журнала, а не теряет его.
In-memory `_status_overrides` — write-through кеш поверх журнала (ускорение чтения
в рамках процесса); при промахе кеша (другой воркер) статус берётся из CSV.
`incidents_service` читает статус через `status_for`.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from api.core.config import settings
from api.domain.common import Status
from api.domain.entities import Action

# Маппинг действия → новый статус инцидента.
_ACTION_TO_STATUS: dict[str, Status] = {
    "validate": "validated",
    "false_positive": "false_positive",
    "create_task": "in_progress",
    "export_report": "in_progress",
    "request_archive": "in_progress",
    "call_driver": "in_progress",
    "notify_hr": "in_progress",
    "stop_vehicle": "in_progress",
}

# `status` персистится в журнал — иначе статус не переживал бы multi-worker.
_CSV_COLUMNS = ["created_at", "incident_id", "action", "comment", "status"]

# Допустимые персистентные статусы (единый enum §3.1).
_VALID_STATUSES: frozenset[str] = frozenset(_ACTION_TO_STATUS.values()) | {"active"}

# Write-through кеш статуса поверх журнала (incident_id → Status).
_status_overrides: dict[str, Status] = {}


def _actions_csv_path() -> Path:
    return settings.output_dir / "actions.csv"


def _ensure_csv() -> Path:
    """Гарантирует существование output/actions.csv с заголовком."""
    path = _actions_csv_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(_CSV_COLUMNS)
    return path


def _csv_status_for(incident_id: str) -> Status | None:
    """Последний непустой валидный статус инцидента из журнала или None.

    Легаси-строки без колонки `status` (старый 4-колоночный формат) пропускаются →
    их инциденты остаются в дефолте «active». Битые строки не роняют чтение.
    """
    path = _actions_csv_path()
    if not path.exists():
        return None
    status: Status | None = None
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if str(row.get("incident_id") or "") != incident_id:
                continue
            raw = str(row.get("status") or "").strip()
            if raw in _VALID_STATUSES:
                status = raw  # type: ignore[assignment]  # последняя запись побеждает
    return status


def record(action: Action) -> Action:
    """Дописывает действие в CSV (со статусом) и обновляет кеш статуса."""
    path = _ensure_csv()
    created_at = datetime.now(timezone.utc).isoformat()
    new_status = _ACTION_TO_STATUS.get(action.action)
    with path.open("a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(
            [created_at, action.incident_id, action.action, action.comment,
             new_status or ""]
        )

    if new_status is not None:
        _status_overrides[action.incident_id] = new_status

    return action


def status_for(incident_id: str) -> Status:
    """Текущий статус инцидента: кеш → журнал CSV → дефолт «active» (§2).

    Фолбэк на журнал делает статус видимым для воркера, не писавшего действие
    (multi-worker safe). Дефолт — «active».
    """
    cached = _status_overrides.get(incident_id)
    if cached is not None:
        return cached
    return _csv_status_for(incident_id) or "active"


def reset_overrides() -> None:
    """Сброс in-memory кеша статусов (для тестов; журнал CSV не трогаем)."""
    _status_overrides.clear()
