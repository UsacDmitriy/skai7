"""Роутер домена sabotage (§7.4, идея #9). prefix=/api.

GET /api/sabotage → список событий саботажа камеры (тёмный DMS / CAMERA_TAMPER
при движении). БД — через Depends(get_db), сборка — sabotage_service (b11).
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends

from api.core.duckdb_conn import get_db
from api.domain.sabotage import SabotageEvent
from api.services import sabotage_service

router = APIRouter(prefix="/api", tags=["sabotage"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("/sabotage", response_model=list[SabotageEvent])
def list_sabotage(db: DbDep) -> list[SabotageEvent]:
    """Список событий саботажа (§7.4). Пустой `v_sabotage` → `[]` (HTTP 200)."""
    return sabotage_service.list_sabotage(db)
