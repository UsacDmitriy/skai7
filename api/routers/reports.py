"""Роутер домена reports (§3.2/§7.5). prefix=/api/reports.

driver/{plate}, fleet, query (тело — уже разобранный ReportQuery). Логика —
reports_service (b5); реальный NLU-парс сырого текста придёт в b9.
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, Query

from api.core.duckdb_conn import get_db
from api.domain.reports import DriverReport, FleetReport, ReportQuery
from api.services import reports_service

router = APIRouter(prefix="/api/reports", tags=["reports"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("/driver/{plate}", response_model=DriverReport)
def driver_report(
    plate: str,
    db: DbDep,
    period_days: Annotated[int, Query(ge=1)] = 3,
) -> DriverReport:
    """Отчёт по водителю/ТС (§7.5 В-1)."""
    return reports_service.driver_report(db, plate, period_days)


@router.get("/fleet", response_model=FleetReport)
def fleet_report(
    db: DbDep,
    period_days: Annotated[int, Query(ge=1)] = 3,
) -> FleetReport:
    """Отчёт по парку (§7.5 В-2)."""
    return reports_service.fleet_report(db, period_days)


@router.post("/query", response_model=DriverReport | FleetReport)
def query_report(
    query: ReportQuery, db: DbDep
) -> DriverReport | FleetReport:
    """Отчёт по разобранному NLU-запросу (§7.5). kind=driver|fleet."""
    return reports_service.report_for_query(db, query)
