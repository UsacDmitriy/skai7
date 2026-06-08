"""Роутер домена sensors (§9.1 — сенсорная диагностика, CAN−GPS разрыв).

Снимает стаб Not-implemented: `GET /api/sensors` → сводка по ТС,
`GET /api/sensors/{plate}` → карточка (404 при неизвестном ТС). БД — через
Depends(get_db), сборка доменных моделей — sensors_service (w3-7).
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from api.core.duckdb_conn import get_db
from api.domain.fleet_health import SensorVehicleCard, SensorVehicleSummary
from api.services import sensors_service

router = APIRouter(prefix="/api/sensors", tags=["sensors"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("", response_model=list[SensorVehicleSummary])
def list_sensors(db: DbDep) -> list[SensorVehicleSummary]:
    """Сводка сенсорной диагностики по всем ТС (§9.2) — 7 строк."""
    return sensors_service.list_sensors(db)


@router.get("/{plate:path}", response_model=SensorVehicleCard)
def get_sensors(plate: str, db: DbDep) -> SensorVehicleCard:
    """Карточка сенсоров по госномеру/UUID. 404 при неизвестном ТС.

    `{plate:path}` — госномера могут содержать `/` (напр. `А 230 КУ/550 RUS`).
    """
    card = sensors_service.get_sensors(db, plate)
    if card is None:
        raise HTTPException(status_code=404, detail="ТС не найдено")
    return card
