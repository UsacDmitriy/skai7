"""Роутер AI-метрик и качества данных (b25, §8.7).

Три эндпоинта измеримости AI-слоя:
  * `GET  /api/metrics/ai`           → `AiMetrics`   — KPI из `ai_metric_events`;
  * `GET  /api/metrics/data-quality` → `DataQuality` — доверие к данным из view;
  * `POST /api/metrics/event`        → `TrackResult` — эмиттер событий (продьюсеры).

Подключается автодискавери `api.main:_discover_routers` по модульному объекту
`router` — НЕ редактируем общий `api/routers/__init__.py` (прецедент scene-
эндпоинта Волны 4.1: иное имя атрибута → тихий 404).
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends

from api.core.duckdb_conn import get_db
from api.services import metrics_service
from api.services.metrics_service import (
    AiMetrics,
    DataQuality,
    MetricEvent,
    TrackResult,
)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("/ai", response_model=AiMetrics)
def get_ai_metrics(db: DbDep) -> AiMetrics:
    """KPI AI-слоя (§8.7): acceptance / copilot / zones / weather / triage / forecast.

    Детерминированы на наборе событий `ai_metric_events`; пусто → нулевые дефолты.
    """
    return metrics_service.get_ai_metrics(db)


@router.get("/data-quality", response_model=DataQuality)
def get_data_quality(db: DbDep) -> DataQuality:
    """Качество данных (§8.7): доли офлайн-камер / без GPS / без медиа / с видео.

    Считается из реальных `v_incidents` / `incident_weather`; все `*_ratio ∈ [0,1]`.
    """
    return metrics_service.get_data_quality(db)


@router.post("/event", response_model=TrackResult)
def track_event(event: MetricEvent) -> TrackResult:
    """Эмиттер событий AI-слоя (§8.7). Best-effort: запись не блокирует продьюсера.

    Коннект приложения read-only, поэтому `track_event` пишет через свой
    writable-коннект; недоступен → `tracked=false` (не ошибка).
    """
    tracked = metrics_service.track_event(
        event.name,
        incident_id=event.incident_id,
        plate=event.plate,
        latency_ms=event.latency_ms,
        source=event.source,
        success=event.success,
        error_detail=event.error_detail,
    )
    return TrackResult(tracked=tracked)
