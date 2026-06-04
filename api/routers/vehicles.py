"""Роутер домена vehicles (§3.2). prefix=/api/vehicles."""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends

from api.core.duckdb_conn import get_db
from api.domain.vehicles import VehicleSummary
from api.services import vehicles_service

router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("", response_model=list[VehicleSummary])
def list_vehicles(db: DbDep) -> list[VehicleSummary]:
    """Список ТС парка (§3.3), обогащённый driver/model/cameras_ok."""
    return vehicles_service.list_summaries(db)
