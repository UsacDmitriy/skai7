"""Роутер домена reports (§3.2/§7.5). prefix=/api/reports.

driver/{plate}, fleet, vehicle/{plate}, query (сырой текст → NLU), transcribe (голос → текст).
Логика — reports_service (b5/b10) + nlu_service (b9) + stt_service (b8). Роутер ничего не считает —
только разбирает HTTP-контракт и делегирует сервису.
"""

from __future__ import annotations

from typing import Annotated, Literal

import duckdb
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import BaseModel

from api.core.duckdb_conn import get_db
from api.domain.reports import (
    DriverReport,
    FleetReport,
    ReportQuery,
    VehicleReport,
)
from api.services import reports_service, stt_service

router = APIRouter(prefix="/api/reports", tags=["reports"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


class QueryRequest(BaseModel):
    """Тело `POST /query` (§7.4): сырой текст запроса + опциональный период."""

    text: str
    period_days: int | None = None


class QueryResult(BaseModel):
    """Ответ `POST /query` — обёртка `{query, report}` (§7.4)."""

    query: ReportQuery
    report: DriverReport | FleetReport


class Transcription(BaseModel):
    """Ответ `POST /transcribe` (§7.4) — результат faster-whisper / fallback."""

    text: str
    lang: str
    confidence: float


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
    view: Literal["drivers", "vehicles"] = "drivers",
) -> FleetReport:
    """Отчёт по парку (§7.5 В-2). `view` — приоритетный разрез UI; оба массива всегда заполнены."""
    return reports_service.fleet_report(db, period_days, view)


@router.get("/vehicle/{plate}", response_model=VehicleReport)
def vehicle_report(
    plate: str,
    db: DbDep,
    period_days: Annotated[int, Query(ge=1)] = 3,
) -> VehicleReport:
    """Отчёт по ТС (§7.5 В-2/ТС, идея #2/#10). `cameras` длины 3 (ADAS/DMS/СНЗ)."""
    return reports_service.vehicle_report(db, plate, period_days)


@router.post("/query", response_model=QueryResult)
def query_report(body: QueryRequest, db: DbDep) -> dict:
    """Сырой текст → NLU (b9) → отчёт (§7.4). `query.kind=driver|fleet`.

    Без `GROQ_API_KEY` nlu_service детерминированно уходит в regex-fallback.
    """
    return reports_service.query(db, body.text, body.period_days)


@router.post("/transcribe", response_model=Transcription)
async def transcribe(
    file: Annotated[UploadFile, File()],
    lang: Annotated[str | None, Form()] = None,
) -> dict:
    """Голос (wav multipart) → текст (§7.4) через faster-whisper / fallback."""
    wav_bytes = await file.read()
    return stt_service.transcribe(wav_bytes, lang)
