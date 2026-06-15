"""Роутер кросс-сверки скоростей (§10.1) — `GET /api/incidents/{id}/speed-check`.

Отдаёт `SpeedCheck` (§10.2): скорость события аларма против ближайшей точки GPS-трека
с классификацией расхождения. Слой доверия к данным, НЕ AI-фича: без флага/сети.
Отдельный модуль с префиксом `/api/incidents` (автодискавери `api/main.py`), чтобы не
смешивать слой доверия с доменным роутером `incidents.py` — общий `__init__.py` не трогаем.

Неизвестный `id` → 404. `no_data` (нет точки в окне / нет "Speed") → 200, не 5xx (§10.5).
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from api.core.duckdb_conn import get_db
from api.domain.speed import SpeedCheck
from api.services import speed_check_service

router = APIRouter(prefix="/api/incidents", tags=["speed-check"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("/{incident_id}/speed-check", response_model=SpeedCheck)
def get_speed_check(incident_id: str, db: DbDep) -> SpeedCheck:
    """Сверка скорости событие↔GPS-трек инцидента (§10.2).

    Неизвестный `incident_id` → 404. Детерминированно из DuckDB.
    """
    result = speed_check_service.speed_check(db, incident_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Инцидент не найден")
    return result
