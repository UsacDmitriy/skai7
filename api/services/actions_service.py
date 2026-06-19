"""Журнал действий (§3.4): запись в output/actions.csv + рантайм-статус инцидента.

POST /api/actions меняет `status` инцидента в рантайме — отдельной таблицы нет,
держим in-memory словарь (сбрасывается на рестарте; источник истины журнала — CSV).
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

_CSV_COLUMNS = ["created_at", "incident_id", "action", "comment"]

# Рантайм-переопределения статуса (incident_id → Status).
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


def record(action: Action) -> Action:
    """Дописывает действие в CSV и обновляет рантайм-статус инцидента."""
    path = _ensure_csv()
    created_at = datetime.now(timezone.utc).isoformat()
    with path.open("a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(
            [created_at, action.incident_id, action.action, action.comment]
        )

    new_status = _ACTION_TO_STATUS.get(action.action)
    if new_status is not None:
        _status_overrides[action.incident_id] = new_status

    return action


def status_for(incident_id: str) -> Status:
    """Текущий статус инцидента: рантайм-переопределение или дефолт «active» (§2)."""
    return _status_overrides.get(incident_id, "active")


def reset_overrides() -> None:
    """Сброс рантайм-статусов (для тестов)."""
    _status_overrides.clear()
