"""Роутер позитивного скоринга (§13.1) — `GET /api/positive-score/{plate}`.

Детерминированный слой данных (агрегация алармов b33), НЕ AI-фича — без флага/сети.
Модульный `router` подхватывается автодискавери `api/main.py:_discover_routers`
(общий `api/routers/__init__.py` не трогаем — прецедент scene/coaching-эндпоинтов).
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from api.core.duckdb_conn import get_db
from api.domain.positive import PositiveScore
from api.services import positive_score_service

router = APIRouter(prefix="/api", tags=["positive-score"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("/positive-score/{plate}", response_model=PositiveScore)
def get_positive_score(plate: str, db: DbDep) -> PositiveScore:
    """Позитивный скоринг ТС (§13.1). `plate` не из `driver_reference` → 404."""
    result = positive_score_service.score(db, plate)
    if result is None:
        raise HTTPException(status_code=404, detail="ТС не найдено")
    return result
