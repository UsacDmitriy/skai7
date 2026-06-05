"""Роутер диспетчерских алертов (§7.4, идея #5). prefix=/api/alerts.

Карточка инцидента + видео-окно ±15с для немедленной реакции (tickets_service b13).
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from api.core.duckdb_conn import get_db
from api.domain.entities import DispatchAlert
from api.services import tickets_service

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("/{alert_id}", response_model=DispatchAlert)
def get_alert(alert_id: str, db: DbDep) -> DispatchAlert:
    """Диспетчерский алерт инцидента (§7.5), video_window_sec=15. 404 если нет."""
    alert = tickets_service.get_alert(db, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Инцидент не найден")
    return alert
