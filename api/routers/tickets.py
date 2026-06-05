"""Роутер заявок (§7.4, идея #6). prefix=/api/tickets.

Журнал заявок поверх output/actions.csv (tickets_service b13). БД — Depends(get_db)
для единообразия DI, хотя срез строится по CSV.
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends

from api.core.duckdb_conn import get_db
from api.domain.entities import Ticket
from api.services import tickets_service

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("", response_model=list[Ticket])
def list_tickets(db: DbDep) -> list[Ticket]:
    """Журнал заявок (§7.5). Нет actions.csv → пустой список."""
    return tickets_service.list_tickets(db)
