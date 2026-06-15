"""Роутер очереди верификации (§11.1) — `GET /api/review-queue`, `POST .../{id}`.

Статусная модель ревью инцидента (b30): журнал решений вместо разовой кнопки.
Слой данных, НЕ AI-фича — без флага/сети. Модульный `router` подхватывается
автодискавери `api/main.py:_discover_routers` (общий `api/routers/__init__.py`
не трогаем — прецедент тихого 404 scene-эндпоинта).
"""

from __future__ import annotations

from typing import Annotated, Optional

import duckdb
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.core.duckdb_conn import get_db
from api.domain.review import ReviewDecision, ReviewItem, ReviewQueue, ReviewStatus
from api.services import review_service

router = APIRouter(prefix="/api", tags=["review"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


class DecisionRequest(BaseModel):
    """Тело POST /api/review-queue/{incident_id} (§11.1).

    `decision` — Literal: неизвестное значение → 422 (Pydantic). Пустая `note`
    валидна (§11.4).
    """

    decision: ReviewDecision
    note: Optional[str] = None


@router.get("/review-queue", response_model=ReviewQueue)
def get_review_queue(
    db: DbDep, status: Optional[ReviewStatus] = None
) -> ReviewQueue:
    """Очередь верификации (§11.1). Без `status` — все инциденты; `counts` — по всем.

    Неизвестный `status` в query → 422 (Literal). Детерминированно из DuckDB + журнала.
    """
    return review_service.queue(db, status)


@router.post("/review-queue/{incident_id}", response_model=ReviewItem)
def decide_review(
    incident_id: str, body: DecisionRequest, db: DbDep
) -> ReviewItem:
    """Записать решение по инциденту (§11.1). Неизвестный id → 404; решение перезаписываемо."""
    item = review_service.decide(db, incident_id, body.decision, body.note)
    if item is None:
        raise HTTPException(status_code=404, detail="Инцидент не найден")
    return item
