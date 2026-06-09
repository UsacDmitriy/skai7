"""Роутер зон риска (b19) — кластеры алармов + РЭБ-зоны.

GET /api/zones           — все зоны (incident + reb)
GET /api/zones?kind=reb  — только РЭБ-зоны
GET /api/zones?hour=22   — зоны с peak_hour=22

Авто-discovery в api/main.py:_discover_routers() — ручная регистрация не нужна.
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, Query

from api.core.duckdb_conn import get_db
from api.domain.entities import RiskZone
from api.services import zones_service

router = APIRouter(prefix="/api/zones", tags=["zones"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("", response_model=list[RiskZone])
def list_zones(
    db: DbDep,
    kind: str | None = Query(default=None, pattern="^(incident|reb)$"),
    hour: int | None = Query(default=None, ge=0, le=23),
) -> list[RiskZone]:
    """Зоны риска. Фильтры: `?kind=incident|reb`, `?hour=0..23`."""
    return zones_service.compute_zones(db, kind=kind, hour=hour)
