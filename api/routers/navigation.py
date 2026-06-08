"""Роутер домена navigation (§9.1, Волна 3) — список проблемных треков → вход в РЭБ.

Повышен из стаба (раньше — Not implemented): `GET /api/navigation` отдаёт
`NavProblemVehicle[]` (5 matched + 1 unmatched), `GET /api/navigation/{plate}` —
сводку ТС (deep-view = `/api/reb/{id}` через `reb_link_id`). Без коллизии префиксов
с `reb.py` (тот — `/api` + `/reb/{id}`). БД — Depends(get_db), сборка — `navigation_service`.
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from api.core.duckdb_conn import get_db
from api.domain.fleet_health import NavProblemVehicle
from api.services import navigation_service

router = APIRouter(prefix="/api/navigation", tags=["navigation"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("", response_model=list[NavProblemVehicle])
def list_navigation(db: DbDep) -> list[NavProblemVehicle]:
    """Список проблемных треков навигации (§9.1) → вход в `/api/reb/{reb_link_id}`."""
    return navigation_service.list_nav_problems(db)


@router.get("/{plate:path}", response_model=NavProblemVehicle)
def get_navigation(plate: str, db: DbDep) -> NavProblemVehicle:
    """Сводка ТС по госномеру. 404 при неизвестном (§9.5).

    `{plate:path}` — навигационные госномера содержат `/` (напр. `А 230 КУ/550 RUS`).
    """
    item = navigation_service.get_nav_problem(db, plate)
    if item is None:
        raise HTTPException(status_code=404, detail="ТС навигации не найдено")
    return item
