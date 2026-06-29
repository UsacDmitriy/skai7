"""Роутер Hypercare (Гиперопека). Автообнаруживается в api/main.py."""
from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends

from api.core.duckdb_conn import get_db
from api.domain.hypercare import (
    EvidenceRequest,
    HypercareEvidence,
    HypercareRule,
    ManualRequest,
)
from api.services import hypercare_service

router = APIRouter(prefix="/api/hypercare", tags=["hypercare"])
DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("/rules", response_model=list[HypercareRule])
def get_rules() -> list[HypercareRule]:
    return hypercare_service.seed_rules()


@router.post("/evidence", response_model=list[HypercareEvidence])
def post_evidence(body: EvidenceRequest, db: DbDep) -> list[HypercareEvidence]:
    return hypercare_service.evaluate(db, body.rules, body.role)


@router.post("/request", response_model=HypercareEvidence)
def post_request(body: ManualRequest, db: DbDep) -> HypercareEvidence:
    return hypercare_service.manual_request(db, body)
