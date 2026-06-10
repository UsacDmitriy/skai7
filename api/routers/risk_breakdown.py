"""Роутер explainability риска (§8.8) — `GET /api/incidents/{id}/risk-breakdown`.

Отдаёт плоский `RiskBreakdown` (вклады слагаемых формулы §2) для waterfall-фронта
(`f20`). Отдельный модуль с префиксом `/api/incidents` (авто-discovery `api/main.py`),
чтобы не смешивать explainability-слой с доменным роутером `incidents.py` (b6).

Неизвестный инцидент → 404. Детерминированно из enrichment, без флага: декомпозиция
лишь раскладывает уже посчитанный risk_score, скрывать нечего.
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from api.core.duckdb_conn import get_db
from api.services import risk_breakdown_service
from api.services.risk_breakdown_service import RiskBreakdown

router = APIRouter(prefix="/api/incidents", tags=["risk-breakdown"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("/{incident_id}/risk-breakdown", response_model=RiskBreakdown)
def get_risk_breakdown(incident_id: str, db: DbDep) -> RiskBreakdown:
    """Декомпозиция `risk_score` инцидента (§8.8). Сумма вкладов == risk_score.

    Неизвестный `incident_id` → 404.
    """
    result = risk_breakdown_service.breakdown(db, incident_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Инцидент не найден")
    return result
