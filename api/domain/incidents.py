"""Схемы домена incidents (контракт §3.1).

`IncidentDetail` наследует `IncidentSummary`. Имена полей — строго по §3.1;
camelCase только там, где указано контрактом (`hasVideo`).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from api.domain.common import CameraStatus, Severity, Source, Status


class Camera(BaseModel):
    """Канонический слот камеры (§2/§3.1). Длина массива всегда 3 (ADAS/DMS/СНЗ)."""

    id: str
    label: str
    status: CameraStatus
    hasVideo: bool  # noqa: N815 — camelCase по контракту §3.1
    offline_from: str | None = None  # окно недоступности для offline/warning
    offline_to: str | None = None


class TelemetryPoint(BaseModel):
    """Точка телеметрии (§3.1). ax = производная скорости (§2), ay = 0.0 (нет данных)."""

    ts_offset: int
    speed: float
    ax: float
    ay: float


class CamExtra(BaseModel):
    """Доп. канал (ch2/ch3) для блока «Другие камеры» (§3.1 `cam_extra[]`)."""

    channel: int
    url: str


class IncidentSummary(BaseModel):
    """Строка ленты GET /api/incidents (§3.1)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    alarm_type: str
    alarm_code: str
    alarm_label_ru: str
    source: Source
    severity: Severity
    risk_level: Severity
    risk_score: int
    ts: str
    vehicle_plate: str
    driver: str
    vehicle_model: str
    speed_kmh: float
    lat: float | None = None
    lon: float | None = None
    address: str | None = None
    video_available: bool
    status: Status


class IncidentDetail(IncidentSummary):
    """Карточка GET /api/incidents/{id} (§3.1). Расширяет Summary."""

    ts_end: str
    unit_id: str
    unit_name: str
    driver_id: str
    driver_phone: str
    driver_region: str  # из driver_reference (§7.1)
    driver_department: str
    driver_safety_score: int
    speed_limit_kmh: int
    is_night: bool
    continuous_driving_min: int
    events_last_7d: int
    confidence: int  # «уверенность версии события %» (§2)
    event_version: str | None = None  # короткая гипотеза причины (§2)
    sensor_active_after_sec: int | None = None  # no-video: DMS работал ещё N сек после offline (§2)
    mileage_km: float
    movement_duration: str
    video_count: int
    cam_front_url: str | None = None
    cam_dms_url: str | None = None
    cam_extra: list[CamExtra] = []
    evidence_summary: str
    cameras: list[Camera] = []
    telemetry: list[TelemetryPoint] = []
