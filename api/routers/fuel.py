"""Роутер-стаб домена fuel (§3.4). Все пути → 501 Not implemented."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/fuel", tags=["fuel"])


@router.get("")
def list_fuel() -> None:
    # TODO: расхождение топлива ЗИС vs карты (`fuel__fuel_vehicles`).
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{plate}")
def get_fuel(plate: str) -> None:
    # TODO: топливная карточка ТС.
    raise HTTPException(status_code=501, detail="Not implemented")
