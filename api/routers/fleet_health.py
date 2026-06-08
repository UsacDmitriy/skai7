"""Роутер домена fleet-health (§9.1/§9.6, Волна 3) — хаб «Здоровье парка».

`GET /api/fleet-health` → `FleetHealthResponse` {coverage, rows}: баннер покрытия
(§9.0) + ростер 17 ТС объединения disjoint-популяций (fuel ∪ sensors ∪ navigation).
Без коллизии префиксов с fuel/sensors/navigation-роутерами. БД — Depends(get_db),
сборка — `fleet_health_service`. Авто-discovery в `api/main.py` (ручная регистрация не нужна).
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends

from api.core.duckdb_conn import get_db
from api.domain.fleet_health import FleetHealthResponse
from api.services import fleet_health_service

router = APIRouter(prefix="/api/fleet-health", tags=["fleet-health"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("", response_model=FleetHealthResponse)
def get_fleet_health(db: DbDep) -> FleetHealthResponse:
    """Хаб «Здоровье парка» (§9.6): покрытие по доменам + ростер 17 ТС объединения."""
    return fleet_health_service.get_fleet_health(db)
