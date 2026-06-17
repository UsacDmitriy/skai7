"""Сервис домена incidents — сборка контрактных ответов (§3.1 / §2).

Берёт сырую строку `v_incidents` (репозиторий) и достраивает enrichment-поля
детерминированным модулем `api/core/enrichment.py`. driver_region/department/
safety_score берутся DB-first из `driver_reference` (§7.1) — единый источник с
отчётом водителя (§7). Поля без источника (confidence, event_version,
sensor_active_after_sec) и fallback при plate вне справочника вычисляются здесь
детерминированно.
"""

from __future__ import annotations

import zlib
from typing import Any

import duckdb

from api.core import enrichment
from api.domain.incidents import (
    CamExtra,
    Camera,
    IncidentDetail,
    IncidentSummary,
    TelemetryPoint,
)
from api.repositories import incidents_repo as repo
from api.services import actions_service

# ---------------------------------------------------------------------------
# Детерминированные пулы — fallback для plate вне driver_reference (§7.1)
# ---------------------------------------------------------------------------

_REGIONS = [
    "Москва",
    "Московская обл.",
    "Санкт-Петербург",
    "Приморский край",
    "Татарстан",
    "Свердловская обл.",
]
_DEPARTMENTS = [
    "Логистика · Север",
    "Логистика · Центр",
    "Логистика · Юг",
    "Доставка · Запад",
    "Доставка · Восток",
]

# Короткая гипотеза причины по alarm_code (event_version, §2). Нет кода → None.
_EVENT_VERSION: dict[str, str] = {
    "DMS_DROWSY": "Засыпание за рулём (микросон)",
    "DMS_YAWNING": "Признаки усталости (зевание)",
    "DMS_PHONE": "Отвлечение на телефон",
    "DMS_SMOKING": "Курение за рулём",
    "DMS_SEATBELT": "Движение без ремня",
    "DRIVER_SUBSTITUTION": "Подмена/отсутствие водителя",
    "CAMERA_TAMPER": "Саботаж DMS-камеры",
    "ADAS_FCW": "Угроза столкновения (FCW)",
    "ADAS_HMW": "Опасная дистанция",
    "ADAS_PCW": "Опасное сближение с пешеходом",
    "OVERSPEED": "Превышение скорости",
    "HARSH_BRAKING": "Резкое торможение",
    "HARSH_ACCEL": "Резкое ускорение",
    "HARSH_CORNERING": "Резкий манёвр в повороте",
}


def _seed(value: str) -> int:
    return zlib.crc32(value.encode()) & 0xFFFFFFFF


def _driver_profile(
    db: duckdb.DuckDBPyConnection, plate: str, risk_score: int
) -> dict[str, Any]:
    """`region`/`department`/`safety_score` из `driver_reference` (§7.1); единый источник.

    DB-first — те же значения, что и в отчёте водителя (§7), иначе одно ТС показывало бы
    разные регион/отдел/safety_score на карточке инцидента и в отчёте (рассинхрон данных).
    Plate вне справочника → детерминированный fallback (пулы / `100 − risk_score`).
    """
    if db is not None:
        try:
            row = db.execute(
                'SELECT "region","department","safety_score" '
                'FROM "driver_reference" WHERE "vehicle_plate"=?',
                [plate],
            ).fetchone()
            if row and row[0] and row[1] and row[2] is not None:
                return {
                    "region": row[0],
                    "department": row[1],
                    "safety_score": max(0, min(100, int(row[2]))),
                }
        except Exception:
            pass
    return {
        "region": _REGIONS[_seed(plate) % len(_REGIONS)],
        "department": _DEPARTMENTS[(_seed(plate) // 7) % len(_DEPARTMENTS)],
        "safety_score": max(0, min(100, 100 - risk_score)),
    }


def _confidence(incident_id: str, video_available: bool) -> int:
    """§2: 70 + seed(id)%30; нет видео → −10. Clamp [0,100]."""
    base = 70 + _seed(incident_id) % 30
    if not video_available:
        base -= 10
    return max(0, min(100, base))


def _sensor_active_after_sec(incident_id: str, video_available: bool) -> int | None:
    """§2: только для no-video — сколько секунд DMS работал после offline.

    Источника точного окна нет → детерминированно seed(id)%10 + 1 (1..10).
    Для алярмов с видео — поле неприменимо (None).
    """
    if video_available:
        return None
    return _seed(incident_id) % 10 + 1


def _cam_extra(video_files: list[dict[str, Any]]) -> list[CamExtra]:
    """Доп. каналы ch2/ch3 для блока «Другие камеры» (§3.1 cam_extra[])."""
    seen: dict[int, str] = {}
    for row in video_files:
        try:
            ch = int(row.get("channel"))
        except (TypeError, ValueError):
            continue
        if ch in (2, 3) and ch not in seen:
            path = row.get("media_relative_path")
            if path:
                seen[ch] = str(path)
    return [CamExtra(channel=ch, url=seen[ch]) for ch in sorted(seen)]


def _enrich(db: duckdb.DuckDBPyConnection, row: dict[str, Any]) -> dict[str, Any]:
    """Считает все производные поля для одной строки v_incidents (общая часть)."""
    plate = row.get("vehicle_plate") or ""
    alarm_code = row.get("alarm_code") or row.get("alarm_type") or ""
    severity = row.get("severity") or "low"
    speed_kmh = float(row.get("speed_kmh") or 0.0)
    ts = row.get("ts") or ""
    video_available = bool(row.get("video_available"))

    speed_limit = enrichment.speed_limit_for(alarm_code)
    night = enrichment.is_night(ts) if ts else False
    cont_min = enrichment.continuous_driving_min(row.get("movement_duration"))
    events_7d = repo.count_alarms_in_window(db, plate, ts) if (plate and ts) else 0
    score = enrichment.risk_score(severity, speed_kmh, speed_limit, night, events_7d)

    drv = enrichment.driver_for(db, plate)
    return {
        "driver": drv["driver"],
        "driver_id": drv["driver_id"],
        "driver_phone": drv["driver_phone"],
        "vehicle_model": enrichment.vehicle_model_for(plate),
        "speed_limit_kmh": speed_limit,
        "is_night": night,
        "continuous_driving_min": cont_min,
        "events_last_7d": events_7d,
        "risk_score": score,
        "evidence_summary": enrichment.evidence_summary(alarm_code, speed_kmh, severity),
        "status": actions_service.status_for(row.get("id") or ""),
    }


def _to_summary(db: duckdb.DuckDBPyConnection, row: dict[str, Any]) -> IncidentSummary:
    e = _enrich(db, row)
    return IncidentSummary(
        id=row["id"],
        alarm_type=row.get("alarm_type") or "",
        alarm_code=row.get("alarm_code") or row.get("alarm_type") or "",
        alarm_label_ru=row.get("alarm_label_ru") or "",
        source=row.get("source") or "TELEMATICS",
        severity=row.get("severity") or "low",
        risk_level=row.get("risk_level") or row.get("severity") or "low",
        risk_score=e["risk_score"],
        ts=row.get("ts") or "",
        vehicle_plate=row.get("vehicle_plate") or "",
        driver=e["driver"],
        vehicle_model=e["vehicle_model"],
        speed_kmh=float(row.get("speed_kmh") or 0.0),
        lat=row.get("lat"),
        lon=row.get("lon"),
        address=row.get("address"),
        video_available=bool(row.get("video_available")),
        status=e["status"],
    )


def list_summaries(
    db: duckdb.DuckDBPyConnection, filters: dict[str, Any] | None = None
) -> list[IncidentSummary]:
    """Лента GET /api/incidents. `status` фильтруется после обогащения (рантайм)."""
    filters = dict(filters or {})
    status_filter = filters.pop("status", None)
    rows = repo.list_incidents(db, **filters)
    summaries = [_to_summary(db, r) for r in rows]
    if status_filter is not None:
        summaries = [s for s in summaries if s.status == status_filter]
    return summaries


def get_detail(
    db: duckdb.DuckDBPyConnection, incident_id: str
) -> IncidentDetail | None:
    """Карточка GET /api/incidents/{id} со всеми enrichment-полями (§3.1) или None."""
    row = repo.get_incident(db, incident_id)
    if row is None:
        return None

    e = _enrich(db, row)
    plate = row.get("vehicle_plate") or ""
    ts = row.get("ts") or ""
    video_available = bool(row.get("video_available"))
    alarm_code = row.get("alarm_code") or row.get("alarm_type") or ""
    _profile = _driver_profile(db, plate, e["risk_score"])

    video_files = repo.video_files_for(db, incident_id)
    cameras = [Camera(**c) for c in enrichment.cameras_from_videofiles(video_files)]
    track_points = repo.track_points_for(db, incident_id)
    telemetry = [
        TelemetryPoint(**t)
        for t in enrichment.telemetry_from_trackpoints(track_points, ts)
    ]

    return IncidentDetail(
        id=row["id"],
        alarm_type=row.get("alarm_type") or "",
        alarm_code=alarm_code,
        alarm_label_ru=row.get("alarm_label_ru") or "",
        source=row.get("source") or "TELEMATICS",
        severity=row.get("severity") or "low",
        risk_level=row.get("risk_level") or row.get("severity") or "low",
        risk_score=e["risk_score"],
        ts=ts,
        vehicle_plate=plate,
        driver=e["driver"],
        vehicle_model=e["vehicle_model"],
        speed_kmh=float(row.get("speed_kmh") or 0.0),
        lat=row.get("lat"),
        lon=row.get("lon"),
        address=row.get("address"),
        video_available=video_available,
        status=e["status"],
        # --- detail-only ---
        ts_end=row.get("ts_end") or "",
        unit_id=row.get("unit_id") or "",
        unit_name=row.get("unit_name") or "",
        driver_id=e["driver_id"],
        driver_phone=e["driver_phone"],
        driver_region=_profile["region"],
        driver_department=_profile["department"],
        driver_safety_score=_profile["safety_score"],
        speed_limit_kmh=e["speed_limit_kmh"],
        is_night=e["is_night"],
        continuous_driving_min=e["continuous_driving_min"],
        events_last_7d=e["events_last_7d"],
        confidence=_confidence(incident_id, video_available),
        event_version=_EVENT_VERSION.get(alarm_code),
        sensor_active_after_sec=_sensor_active_after_sec(incident_id, video_available),
        mileage_km=float(row.get("mileage_km") or 0.0),
        movement_duration=row.get("movement_duration") or "",
        video_count=int(row.get("video_count") or 0),
        cam_front_url=row.get("cam_front_url"),
        cam_dms_url=row.get("cam_dms_url"),
        cam_extra=_cam_extra(video_files),
        evidence_summary=e["evidence_summary"],
        cameras=cameras,
        telemetry=telemetry,
    )


def get_telemetry(
    db: duckdb.DuckDBPyConnection, incident_id: str
) -> list[TelemetryPoint]:
    """GET /api/incidents/{id}/telemetry. Пустой список если алярма/точек нет."""
    row = repo.get_incident(db, incident_id)
    if row is None:
        return []
    track_points = repo.track_points_for(db, incident_id)
    return [
        TelemetryPoint(**t)
        for t in enrichment.telemetry_from_trackpoints(track_points, row.get("ts") or "")
    ]
