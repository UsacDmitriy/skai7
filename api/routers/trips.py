"""Роутер видеодосье поездки (§7.4, идея #7). prefix=/api/trips.

Трек поездки + таймлайн событий ТС (tickets_service b13).
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from api.core.duckdb_conn import get_db
from api.domain.entities import TripDossier
from api.services import tickets_service

router = APIRouter(prefix="/api/trips", tags=["trips"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("/{trip_id}", response_model=TripDossier)
def get_trip(trip_id: str, db: DbDep) -> TripDossier:
    """Видеодосье поездки (§7.5): трек + таймлайн. 404 если данных по id нет."""
    trip = tickets_service.get_trip(db, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Поездка не найдена")
    return trip
