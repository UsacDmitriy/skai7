"""Схема домена vehicles (контракт §3.3).

GET /api/vehicles — список ТС из `video_events__vehicles` + обогащение driver/model.
"""

from __future__ import annotations

from pydantic import BaseModel

from api.domain.common import CameraStatus


class VehicleCamera(BaseModel):
    """Камера в карточке ТС (упрощённая, без offline-окон)."""

    id: str
    label: str
    status: CameraStatus


class VehicleSummary(BaseModel):
    """Строка списка ТС (§3.3). Сырые метрики `video_events__vehicles` + driver/model."""

    unit_id: str
    plate: str
    vehicle_model: str
    driver: str
    alarm_count: int
    alarm_types: str | None = None
    downloaded_video_count: int
    total_track_mileage_km: float
    cameras_ok: str  # «2/3»
