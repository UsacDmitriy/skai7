"""Роутер домена incidents (§3.2). prefix=/api/incidents.

Лента, карточка, телеметрия и видеофайл (FileResponse). БД — через Depends(get_db),
обогащение/сборка — incidents_service (b5).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from api.core.config import settings
from api.core.duckdb_conn import get_db
from api.domain.common import Severity, Source, Status
from api.domain.incidents import IncidentDetail, IncidentSummary, TelemetryPoint
from api.repositories import incidents_repo
from api.services import incidents_service

router = APIRouter(prefix="/api/incidents", tags=["incidents"])

# Каналы камер (§3.1): 1=ADAS/фронт, 2/3=доп., 5=DMS/салон.
_VALID_CHANNELS = {1, 2, 3, 5}


def _resolve_media_path(rel_path: str) -> Path:
    """Абсолютный путь к mp4 под `settings.media_dir`.

    `media_relative_path` в БД хранится относительно корня проекта и уже
    содержит префикс `datasets/media/…`, тогда как `media_dir` сам равен
    `<root>/datasets/media`. Снимаем избыточный префикс, чтобы склейка
    `media_dir / rel` не задваивала `datasets/media`. Устойчиво и к путям,
    хранящимся уже относительно media_dir (`video_events/…`).
    """
    rel = Path(rel_path)
    try:
        media_prefix = settings.media_dir.relative_to(settings.project_root).parts
    except ValueError:  # media_dir вне project_root (env-override) — без снятия
        media_prefix = ()
    if media_prefix and rel.parts[: len(media_prefix)] == media_prefix:
        rel = Path(*rel.parts[len(media_prefix):])
    return settings.media_dir / rel

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("", response_model=list[IncidentSummary])
def list_incidents(
    db: DbDep,
    severity: Severity | None = None,
    source: Source | None = None,
    status: Status | None = None,
    vehicle_plate: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[IncidentSummary]:
    """Лента инцидентов (§3.2) с фильтрами; `status` — рантайм-журнал (сервис)."""
    filters = {
        "severity": severity,
        "source": source,
        "status": status,
        "vehicle_plate": vehicle_plate,
        "limit": limit,
        "offset": offset,
    }
    return incidents_service.list_summaries(
        db, {k: v for k, v in filters.items() if v is not None}
    )


@router.get("/{incident_id}", response_model=IncidentDetail)
def get_incident(incident_id: str, db: DbDep) -> IncidentDetail:
    """Карточка инцидента со всеми enrichment-полями (§3.1). 404 если нет."""
    detail = incidents_service.get_detail(db, incident_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Инцидент не найден")
    return detail


@router.get("/{incident_id}/telemetry", response_model=list[TelemetryPoint])
def get_telemetry(incident_id: str, db: DbDep) -> list[TelemetryPoint]:
    """Телеметрия трека инцидента (§3.1). Пустой список, если точек нет."""
    return incidents_service.get_telemetry(db, incident_id)


@router.get("/{incident_id}/video/{channel}")
def get_video(incident_id: str, channel: int, db: DbDep) -> FileResponse:
    """Видеофайл mp4 канала из settings.media_dir (§3.2). 404 если нет файла."""
    if channel not in _VALID_CHANNELS:
        raise HTTPException(
            status_code=404, detail=f"Недопустимый канал: {channel}"
        )

    rel_path = incidents_repo.video_path_for(db, incident_id, channel)
    if rel_path is None:
        raise HTTPException(status_code=404, detail="Видео не найдено")

    file_path = _resolve_media_path(rel_path)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Видеофайл отсутствует на диске")

    return FileResponse(path=file_path, media_type="video/mp4", filename=file_path.name)
