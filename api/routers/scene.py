"""Роутер сцен-контекста инцидента (§8.3) — `GET /api/incidents/{id}/scene`.

Отдаёт `SceneContext` + `WeatherCrossCheck` + governance-мету (§8.6). Отдельный
модуль с тем же префиксом `/api/incidents`, чтобы не смешивать AI-слой с доменным
роутером `incidents.py` (б5) — авто-discovery подключает оба по объекту `router`.

Governance (§8.6): флаг `scene` выключен → 200 «feature disabled» (не 5xx),
UI скрывает блок. Неизвестный инцидент → 404.
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from api.core.ai_flags import FeatureDisabledResponse, flags
from api.core.duckdb_conn import get_db
from api.services import scene_service
from api.services.scene_service import SceneResponse

router = APIRouter(prefix="/api/incidents", tags=["scene"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("/{incident_id}/scene", response_model=None)
def get_scene(
    incident_id: str, db: DbDep
) -> SceneResponse | FeatureDisabledResponse:
    """Сцена + погодная сверка инцидента (§8.3/§8.4).

    Флаг `scene` выкл → `FeatureDisabledResponse` (200, §8.6). Неизвестный
    инцидент → 404. Известный без предрасчёта → детерминированный фолбэк.
    """
    if not flags.is_enabled("scene"):
        return FeatureDisabledResponse(detail="scene feature disabled")
    if not scene_service.incident_exists(db, incident_id):
        raise HTTPException(status_code=404, detail="Инцидент не найден")
    return scene_service.get_scene(db, incident_id)
