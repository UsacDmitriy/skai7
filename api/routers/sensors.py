"""Роутер-стаб домена sensors (§3.4). Все пути → 501 Not implemented."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


@router.get("")
def list_sensors() -> None:
    # TODO: сенсорная диагностика (`sensors__*`).
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{plate}")
def get_sensors(plate: str) -> None:
    # TODO: сенсорная карточка ТС.
    raise HTTPException(status_code=501, detail="Not implemented")
