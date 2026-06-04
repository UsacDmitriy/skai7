"""Сервис домена vehicles (§3.3) — сборка VehicleSummary из сырых строк.

Маппит `video_events__vehicles` (vehicles_repo) в контрактный VehicleSummary +
детерминированное обогащение driver/model (enrichment). cameras_ok — доля
онлайн-камер «N/3» по downloaded_video_count (точный статус — §7.2, b10).
"""

from __future__ import annotations

from typing import Any

import duckdb

from api.core import enrichment
from api.domain.vehicles import VehicleSummary
from api.repositories import vehicles_repo


def _cameras_ok(row: dict[str, Any]) -> str:
    """Доля онлайн-камер «N/3». Без точного источника — по downloaded_video_count.

    # TODO: реальный статус камер из v_vehicle (§7.2, b10).
    """
    online = 3 if (row.get("downloaded_video_count") or 0) > 0 else 1
    return f"{min(online, 3)}/3"


def _to_summary(row: dict[str, Any]) -> VehicleSummary:
    plate = row.get("unit_state_number") or ""
    return VehicleSummary(
        unit_id=row.get("unit_id") or "",
        plate=plate,
        vehicle_model=enrichment.vehicle_model_for(plate),
        driver=enrichment.driver_for(plate),
        alarm_count=int(row.get("alarm_count") or 0),
        alarm_types=row.get("alarm_types"),
        downloaded_video_count=int(row.get("downloaded_video_count") or 0),
        total_track_mileage_km=float(row.get("total_track_mileage_km") or 0.0),
        cameras_ok=_cameras_ok(row),
    )


def list_summaries(db: duckdb.DuckDBPyConnection) -> list[VehicleSummary]:
    """GET /api/vehicles — все ТС, обогащённые driver/model/cameras_ok."""
    return [_to_summary(r) for r in vehicles_repo.list_vehicles(db)]
