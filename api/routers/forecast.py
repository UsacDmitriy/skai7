"""Роутер прогноза риска (b18, §8.3) — `GET /api/reports/forecast/{plate}`.

Авто-discovery в `api/main.py:_discover_routers()` подключает модуль по объекту
`router` — общий `api/routers/__init__.py` НЕ правим (иначе гонка с b19/b20).
Роутер ничего не считает: проверяет существование ТС (иначе 404) и делегирует
`forecast_service`.
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from api.core.duckdb_conn import get_db
from api.services import forecast_service
from api.services.forecast_service import RiskForecast

router = APIRouter(prefix="/api/reports", tags=["forecast"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("/forecast/{plate}", response_model=RiskForecast)
def risk_forecast(plate: str, db: DbDep) -> RiskForecast:
    """Прогноз нарушений на 7 дней + аномалия + рекомендации (§8.4).

    Неизвестный `plate` → 404. Известный ТС с пустой историей → валидный нулевой
    прогноз (не падать).
    """
    if not forecast_service.plate_exists(db, plate):
        raise HTTPException(status_code=404, detail=f"ТС не найдено: {plate}")
    return forecast_service.forecast(db, plate)
