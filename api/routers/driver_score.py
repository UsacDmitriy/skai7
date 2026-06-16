"""Роутер единого рейтинга водителя (§13.2) — лидерборд и карточка по plate.

`GET /api/driver-score` — лидерборд всех ТС; `GET /api/driver-score/{plate}` — один ТС.
Детерминированный слой данных (бленд риска §2 и позитива §13.1), НЕ AI-фича — без
флага/сети. Модульный `router` подхватывается автодискавери `api/main.py:_discover_routers`
(общий `api/routers/__init__.py` не трогаем — прецедент positive-score/coaching-эндпоинтов).
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from api.core.duckdb_conn import get_db
from api.domain.driver_score import DriverScore
from api.services import driver_score_service

router = APIRouter(prefix="/api", tags=["driver-score"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("/driver-score", response_model=list[DriverScore])
def get_driver_leaderboard(db: DbDep) -> list[DriverScore]:
    """Лидерборд всех ТС (§13.2): `unified_score` desc, тай-брейк `vehicle_plate` asc."""
    return driver_score_service.leaderboard(db)


@router.get("/driver-score/{plate}", response_model=DriverScore)
def get_driver_score(plate: str, db: DbDep) -> DriverScore:
    """Единый рейтинг ТС (§13.2). `plate` не из `driver_reference` → 404."""
    result = driver_score_service.score(db, plate)
    if result is None:
        raise HTTPException(status_code=404, detail="ТС не найдено")
    return result
