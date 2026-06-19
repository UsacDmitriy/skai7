"""Роутер домена reb (§7.4, идея #8 — РЭБ/GPS-разрывы).

Реализует навигацию из §3.4 как `/api/reb` (заменяет стаб `navigation`):
восстановление трека при подавлении GPS. БД — через Depends(get_db),
сборка `RebRecovery` (§7.5) — reb_service (b12).
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from api.core.duckdb_conn import get_db
from api.domain.entities import RebAnomalyZone, RebRecovery
from api.services import reb_anomaly_service, reb_service

router = APIRouter(prefix="/api", tags=["reb"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("/reb/anomalies", response_model=list[RebAnomalyZone])
def get_reb_anomalies(db: DbDep) -> list[RebAnomalyZone]:
    """Детектированные РЭБ-зоны с confidence score и per-vehicle аномалиями."""
    return reb_anomaly_service.detect_anomalies(db)


@router.get("/reb/{id:path}", response_model=RebRecovery)
def get_reb(id: str, db: DbDep) -> RebRecovery:
    """Восстановление трека по `id` ТС (госномер или unit_id). 404 если нет данных.

    `{id:path}` — госномера навигации содержат `/` (напр. `А 230 КУ/550 RUS`).
    """
    recovery = reb_service.get_reb(db, id)
    if recovery is None:
        raise HTTPException(status_code=404, detail="Данные навигации не найдены")
    return recovery
