"""Роутер домена fatigue (b20) — цепочки усталости водителя.

GET /api/fatigue          — все цепочки
GET /api/fatigue?plate=X  — только для конкретного ТС

Авто-discovery в `api/main.py:_discover_routers()` — ручная регистрация не нужна.
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends

from api.core.duckdb_conn import get_db
from api.domain.entities import FatigueChain
from api.services import fatigue_service

router = APIRouter(prefix="/api/fatigue", tags=["fatigue"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("", response_model=list[FatigueChain])
def list_fatigue(db: DbDep, plate: str | None = None) -> list[FatigueChain]:
    """Цепочки усталости (скользящее окно 90 мин). Опционально `?plate=`."""
    return fatigue_service.chains(db, plate=plate)
