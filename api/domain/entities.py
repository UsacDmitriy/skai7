"""Прочие сущности домена (контракт §3.4 / §7.5).

`Action` — тело POST /api/actions; `Ticket`/`DispatchAlert`/`TripDossier`/
`RebRecovery`/`SabotageEvent` — P1/P2 (§7.5), материализует только b5.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel

from api.domain.common import Severity, Status
from api.domain.incidents import IncidentDetail, TelemetryPoint

# Допустимые действия журнала (§3.4).
ActionType = Literal[
    "validate",
    "false_positive",
    "create_task",
    "export_report",
    "request_archive",
    "call_driver",
    "notify_hr",
    "stop_vehicle",
]


class Action(BaseModel):
    """Тело/ответ POST /api/actions (§3.4)."""

    incident_id: str
    action: ActionType
    comment: str = ""


class Ticket(BaseModel):
    """Заявка (§7.5). Читается из output/actions.csv (идея #6).

    is_overdue = deadline<now И status∉{closed}; «Просрочена» — не статус, а оверлей.
    """

    id: str
    created_at: str
    incident_id: str
    action: str
    comment: str
    status: Status
    deadline: str | None = None
    is_overdue: bool = False


class DispatchAlert(BaseModel):
    """Диспетчерский алерт (§7.5, идея #5): инцидент + видео ±N с."""

    incident: IncidentDetail
    video_window_sec: int = 15
    requested_at: str


class TimelineEvent(BaseModel):
    """Точка таймлайна видеодосье (§7.5 TripDossier.timeline)."""

    ts_offset: int
    alarm_code: str
    label: str
    has_video: bool


class TripDossier(BaseModel):
    """Видеодосье (§7.5, идея #7): трек + таймлайн событий."""

    vehicle_plate: str
    track: list[TelemetryPoint] = []
    timeline: list[TimelineEvent] = []


class GapPeriod(BaseModel):
    """GPS-разрыв (§7.5 RebRecovery.gap_periods)."""

    start: str
    end: str
    duration_sec: int


class GpsPoint(BaseModel):
    """Точка GPS-трека (§7.5 RebRecovery.gps_track)."""

    lat: float
    lon: float
    ts: str


class VideoFrame(BaseModel):
    """Соседний видеокадр (§7.5 RebRecovery.video_frames)."""

    ts: str
    channel: int
    url: str


class RebRecovery(BaseModel):
    """Восстановление при РЭБ (§7.5, идея #8): GPS-разрывы + соседние кадры."""

    vehicle_plate: str
    gps_track: list[GpsPoint] = []
    gap_periods: list[GapPeriod] = []
    video_frames: list[VideoFrame] = []


class SabotageEvent(BaseModel):
    """Событие саботажа (§7.5, идея #9): тёмный DMS + speed>0."""

    id: str
    vehicle_plate: str
    ts: str
    dms_dark: bool
    speed_kmh: float
    driver_name: str
    video_url: str | None = None


# ---------------------------------------------------------------------------
# Risk Zones (b19)
# ---------------------------------------------------------------------------


class RiskZone(BaseModel):
    """Зона риска (§8.4): кластер алармов или РЭБ-зона."""

    zone_id: str
    centroid: list[float]   # [lat, lon]
    radius_m: float
    alarm_count: int
    avg_risk: float         # 0..100
    top_alarm_code: str
    peak_hour: int          # 0..23
    kind: str               # incident | reb


# ---------------------------------------------------------------------------
# Fatigue Chain (b20)
# ---------------------------------------------------------------------------


class FatigueEvent(BaseModel):
    """Отдельное событие усталости внутри цепочки."""

    code: str   # alarm_code
    ts: str     # ISO timestamp string


class FatigueChain(BaseModel):
    """Цепочка событий усталости в скользящем окне 90 минут (b20)."""

    plate: str
    trip_id: str | None = None
    events: list[FatigueEvent]
    window_min: int
    severity: Severity


# ---------------------------------------------------------------------------
# REB Anomaly Zones (reb_anomaly_service)
# ---------------------------------------------------------------------------


class AnomalyType(str, Enum):
    gap = "gap"
    speed_spike = "speed_spike"
    coord_jump = "coord_jump"


class VehicleAnomaly(BaseModel):
    """Одно ТС в РЭБ-зоне с наиболее тяжёлой аномалией."""

    vehicle_plate: str
    anomaly_type: AnomalyType
    max_speed_kmh: float | None
    lat: float
    lon: float
    ts_start: str
    ts_end: str | None
    possible_route: list[list[float]]
    reb_link_id: str | None


class RebAnomalyZone(BaseModel):
    """Кластер аномалий телеметрии с оценкой достоверности РЭБ-подавления."""

    zone_id: str
    centroid: list[float]
    radius_m: float
    confidence: int
    confidence_label: str
    vehicles: list[VehicleAnomaly]
    event_count: int
    date_count: int
