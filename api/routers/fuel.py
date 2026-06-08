"""Роутер домена fuel (§9.1, аддендум волны 3 — снят стаб Not implemented).

Топливная сверка ЗИС vs карты. БД — через `Depends(get_db)`, сборка схем (§9.2) —
`fuel_service` (w3-6). Авто-discovery в `api/main.py`: ручная регистрация не нужна.
Госномера простые (без `/`), потому путь `{plate}` без `:path`.
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from api.core.duckdb_conn import get_db
from api.domain.fleet_health import FuelVehicleCard, FuelVehicleSummary
from api.services import fuel_service

router = APIRouter(prefix="/api/fuel", tags=["fuel"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("", response_model=list[FuelVehicleSummary])
def list_fuel(db: DbDep) -> list[FuelVehicleSummary]:
    """Топливный ростер (10 ТС). Headline KPI — `volume_delta_zis_minus_card_l`."""
    return fuel_service.list_fuel(db)


@router.get("/{plate}", response_model=FuelVehicleCard)
def get_fuel(plate: str, db: DbDep) -> FuelVehicleCard:
    """Карточка топлива ТС. 404 при неизвестном госномере (§9.5, детерминированно)."""
    card = fuel_service.get_fuel(db, plate)
    if card is None:
        raise HTTPException(status_code=404, detail="ТС не найдено в топливном домене")
    return card
