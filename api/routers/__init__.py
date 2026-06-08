"""HTTP-слой (§3.2). b6 владеет `api/routers/*`.

Один файл = один APIRouter с prefix. `ALL_ROUTERS` — для include в app (x2/b6).
incidents/reports/vehicles/actions + fuel/sensors/navigation (§9, w3-6/7/8) — рабочие.
"""

from __future__ import annotations

from fastapi import APIRouter

from api.routers import (
    actions,
    fuel,
    incidents,
    navigation,
    reports,
    sensors,
    vehicles,
)

# Порядок = порядок групп тегов в /docs.
ALL_ROUTERS: list[APIRouter] = [
    incidents.router,
    reports.router,
    vehicles.router,
    actions.router,
    fuel.router,
    sensors.router,
    navigation.router,
]
