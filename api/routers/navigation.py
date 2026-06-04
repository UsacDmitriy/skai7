"""Роутер-стаб домена navigation (§3.4). Все пути → 501 Not implemented.

Реальная навигация (GPS-разрывы РЭБ) реализуется b12 как /api/reb.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/navigation", tags=["navigation"])


@router.get("")
def list_navigation() -> None:
    # TODO: проблемные треки навигации (реализуется b12 → /api/reb).
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{plate}")
def get_navigation(plate: str) -> None:
    # TODO: навигационная карточка ТС.
    raise HTTPException(status_code=501, detail="Not implemented")
