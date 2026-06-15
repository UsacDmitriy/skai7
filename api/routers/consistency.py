"""Роутер консистентности данных (§10.1) — `GET /api/consistency`.

Отдаёт `ConsistencyReport` (§10.2): агрегат 7 детерминированных проверок целостности
+ сводные `evidence_rate`/`speed_agreement_rate`. Слой доверия к данным, НЕ AI-фича:
без флага/сети. Модульный `router` подхватывается автодискавери `api/main.py`
(общий `api/routers/__init__.py` не трогаем — прецедент тихого 404 scene-эндпоинта).
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends

from api.core.duckdb_conn import get_db
from api.domain.consistency import ConsistencyReport
from api.services import consistency_service

router = APIRouter(prefix="/api", tags=["consistency"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("/consistency", response_model=ConsistencyReport)
def get_consistency(db: DbDep) -> ConsistencyReport:
    """Отчёт консистентности данных (§10.2): 7 проверок + сводные доли доверия.

    Детерминированно из DuckDB; повторный вызов → идентичный ответ.
    """
    return consistency_service.report(db)
