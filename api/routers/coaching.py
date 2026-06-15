"""Роутер цикла обучения (§12.2) — `GET /api/coaching`, `GET /api/coaching/{plate}`.

Слой данных (синтетический демо-датасет b31), НЕ AI-фича — без флага/сети.
Модульный `router` подхватывается автодискавери `api/main.py:_discover_routers`
(общий `api/routers/__init__.py` не трогаем — прецедент scene-эндпоинта).
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from api.core.duckdb_conn import get_db
from api.domain.coaching import CoachingCard, CoachingSummary
from api.services import coaching_service

router = APIRouter(prefix="/api", tags=["coaching"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("/coaching", response_model=list[CoachingSummary])
def get_coaching_summary(db: DbDep) -> list[CoachingSummary]:
    """Сводка по водителям (§12.2), сортировка по `repeat_violation_rate` desc."""
    return coaching_service.summary(db)


@router.get("/coaching/{plate}", response_model=CoachingCard)
def get_coaching_card(plate: str, db: DbDep) -> CoachingCard:
    """Карточка водителя (§12.2). `plate` не из `driver_reference` → 404."""
    card = coaching_service.card(db, plate)
    if card is None:
        raise HTTPException(status_code=404, detail="Водитель не найден")
    return card
