"""Прикладные срезы поверх домена incidents (§7.4/§7.5, идеи #5/#6/#7).

- `list_tickets` — журнал заявок из `output/actions.csv` (идея #6).
- `get_alert` — диспетчерская карточка инцидента + видео-окно ±15с (идея #5).
- `get_trip` — видеодосье поездки: трек + таймлайн событий ТС (идея #7).

Репозитории/обогащение не дублируем — переиспользуем `incidents_service` (b5)
и `incidents_repo`. Сервис не знает про HTTP — `None` отдаётся роутеру под 404.
"""

from __future__ import annotations

import csv
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

from api.core.config import settings
from api.domain.common import Status
from api.domain.entities import DispatchAlert, Ticket, TimelineEvent, TripDossier
from api.domain.incidents import TelemetryPoint
from api.repositories import incidents_repo as repo
from api.services import incidents_service

# Видео-окно диспетчерского алерта фиксировано контрактом (§7.5).
_VIDEO_WINDOW_SEC = 15

# Допустимые значения статуса заявки (единый enum §3.1). Дефолт — «active» (НЕ «new»).
_VALID_STATUSES: frozenset[str] = frozenset(
    {"active", "in_progress", "validated", "false_positive", "closed"}
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    """ISO-строка → aware datetime (UTC) или None при пустом/невалидном вводе."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Tickets (идея #6) — журнал заявок из output/actions.csv
# ---------------------------------------------------------------------------


def _actions_csv_path() -> Path:
    return settings.output_dir / "actions.csv"


def _status_from_csv(raw: str | None) -> Status:
    """Статус заявки из CSV или дефолт «active» (§3.1). Неизвестное → «active»."""
    if raw and str(raw).strip() in _VALID_STATUSES:
        return str(raw).strip()  # type: ignore[return-value]
    return "active"


def _is_overdue(deadline: str | None, status: Status) -> bool:
    """is_overdue = deadline<now И status∉{closed} (§7.5).

    `deadline=null`/невалидный → False; `status="closed"` → False даже при просрочке.
    """
    if status == "closed":
        return False
    due = _parse_dt(deadline)
    if due is None:
        return False
    return due < _now()


def _ticket_id(index: int, row: dict[str, Any]) -> str:
    """Детерминированный id заявки: crc32 строки CSV (стабилен между запросами)."""
    payload = "|".join(
        str(row.get(col) or "")
        for col in ("created_at", "incident_id", "action", "comment")
    )
    return f"TK-{zlib.crc32(payload.encode('utf-8')) & 0xFFFFFFFF:08x}"


def list_tickets(db: duckdb.DuckDBPyConnection) -> list[Ticket]:
    """GET /api/tickets: заявки из output/actions.csv (§7.5).

    Колонки CSV: `created_at,incident_id,action,comment` (от actions_service b5/b6);
    опциональные `status`/`deadline` используются, если присутствуют. Файла нет /
    пустой / только заголовок → `[]` (не ошибка). `db` не используется (срез по CSV),
    оставлен для единообразия DI и будущего переноса журнала в БД.
    """
    path = _actions_csv_path()
    if not path.exists():
        return []

    tickets: list[Ticket] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for index, row in enumerate(reader):
            status = _status_from_csv(row.get("status"))
            deadline = row.get("deadline") or None
            tickets.append(
                Ticket(
                    id=_ticket_id(index, row),
                    created_at=str(row.get("created_at") or ""),
                    incident_id=str(row.get("incident_id") or ""),
                    action=str(row.get("action") or ""),
                    comment=str(row.get("comment") or ""),
                    status=status,
                    deadline=deadline,
                    is_overdue=_is_overdue(deadline, status),
                )
            )
    return tickets


# ---------------------------------------------------------------------------
# Dispatch alert (идея #5) — карточка инцидента + видео-окно ±15с
# ---------------------------------------------------------------------------


def get_alert(db: duckdb.DuckDBPyConnection, incident_id: str) -> DispatchAlert | None:
    """GET /api/alerts/{id}: `IncidentDetail` в обёртке `DispatchAlert` (§7.5).

    `video_window_sec` всегда 15. Нет инцидента → `None` (роутер → 404).
    """
    detail = incidents_service.get_detail(db, incident_id)
    if detail is None:
        return None
    return DispatchAlert(
        incident=detail,
        video_window_sec=_VIDEO_WINDOW_SEC,
        requested_at=_now_iso(),
    )


# ---------------------------------------------------------------------------
# Trip dossier (идея #7) — трек поездки + таймлайн событий ТС
# ---------------------------------------------------------------------------


def _track_window(rows: list[dict[str, Any]]) -> tuple[datetime, datetime] | None:
    """Временное окно поездки [min, max] по точкам трека или None, если их нет."""
    moments: list[datetime] = []
    for row in rows:
        dt = _parse_dt(row.get("timestamp_utc") or row.get("Timestamp_utc"))
        if dt is not None:
            moments.append(dt)
    if not moments:
        return None
    return (min(moments), max(moments))


def _has_downloaded_video(db: duckdb.DuckDBPyConnection, alarm_id: str) -> bool:
    """True, только если у алярма есть скачанный видеоканал (§7.5 has_video)."""
    for vf in repo.video_files_for(db, alarm_id):
        if str(vf.get("download_status") or "").lower() == "downloaded":
            return True
    return False


def get_trip(db: duckdb.DuckDBPyConnection, trip_id: str) -> TripDossier | None:
    """GET /api/trips/{id}: видеодосье поездки (§7.5).

    `id` — алярм-якорь поездки. `track` — телеметрия его трека (как
    `incidents_service.get_telemetry`); `timeline` — алярмы того же ТС в окне трека.
    Нет данных по `id` → `None` (роутер → 404). Пустая поездка (ТС есть, точек нет) →
    `track=[]`/`timeline=[]` — валидный ответ, не 404.
    """
    row = repo.get_incident(db, trip_id)
    if row is None:
        return None

    plate = row.get("vehicle_plate") or ""
    ref_ts = row.get("ts") or ""

    track_rows = repo.track_points_for(db, trip_id)
    track: list[TelemetryPoint] = (
        incidents_service.get_telemetry(db, trip_id) if track_rows else []
    )

    timeline = _build_timeline(db, plate, ref_ts, _track_window(track_rows))
    return TripDossier(vehicle_plate=plate, track=track, timeline=timeline)


def _build_timeline(
    db: duckdb.DuckDBPyConnection,
    plate: str,
    ref_ts: str,
    window: tuple[datetime, datetime] | None,
) -> list[TimelineEvent]:
    """Таймлайн алярмов ТС в окне поездки, ts_offset — секунды от якоря (ref_ts)."""
    if window is None or not plate:
        return []  # пустая поездка / нет ТС → пустой таймлайн (валидно).

    ref_dt = _parse_dt(ref_ts)
    if ref_dt is None:
        return []

    win_start, win_end = window
    events: list[TimelineEvent] = []
    for s in incidents_service.list_summaries(db, {"vehicle_plate": plate}):
        at = _parse_dt(s.ts)
        if at is None or at < win_start or at > win_end:
            continue
        events.append(
            TimelineEvent(
                ts_offset=int((at - ref_dt).total_seconds()),
                alarm_code=s.alarm_code,
                label=s.alarm_label_ru,
                has_video=_has_downloaded_video(db, s.id),
            )
        )
    events.sort(key=lambda e: e.ts_offset)
    return events
