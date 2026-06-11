"""Сервис AI-метрик и качества данных (b25, §8.7).

Закрывает «измеримость» AI-слоя: даёт два детерминированных среза —
  * `AiMetrics`     — KPI поведения AI-фич, считаются из событийной таблицы
                      `ai_metric_events` (prep `w3-16`, аддитивный лог);
  * `DataQuality`   — доверие к входным данным, считается из реальных view
                      `v_incidents` / `incident_weather` (без событий).

Плюс **эмиттер** `track_event(...)`, которым продьюсеры (рекомендации f16,
копилот b21/f17, зоны f18, погода b17) пишут события. Запись — best-effort:
основной коннект приложения read-only (`duckdb_conn.get_connection`), поэтому
эмиттер открывает собственный writable-коннект и НИКОГДА не роняет продьюсера
(любой сбой/флаг → no-op). Это сознательная деградация (§8.0): метрики не
должны блокировать продуктовые эндпоинты.

Детерминизм агрегации (Check b25): один и тот же набор событий → один и тот же
`AiMetrics`. `track_event` фиксирует момент вызова (`ts`) — это запись лога, а не
аналитическая логика view, поэтому время/идентификатор здесь допустимы (см.
комментарий DDL `33_ai_metric_events.sql`).

Схемы держим здесь (как `scene_service`/`forecast_service` свои) — общий
`entities.py` не трогаем, чтобы не плодить кросс-трек гонки.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import duckdb
from pydantic import BaseModel

from api.core.config import settings
from api.repositories import rows_to_dicts

logger = logging.getLogger(__name__)

_TABLE = "ai_metric_events"

# --- Таксономия событий (feature_name в ai_metric_events) ------------------
# Имя события кладём в колонку "feature_name" (VARCHAR без CHECK) — DDL не
# фиксирует словарь, а funnel-метрикам нужны парные события (shown/accepted).
EVENT_RECOMMENDATION_SHOWN = "recommendation_shown"
EVENT_RECOMMENDATION_ACCEPTED = "recommendation_accepted"
EVENT_RECOMMENDATION_REJECTED = "recommendation_rejected"
EVENT_COPILOT_TOOL_CALLED = "copilot_tool_called"
EVENT_COPILOT_TOOL_SUCCESS = "copilot_tool_success"
EVENT_ZONE_OPENED = "zone_opened"
EVENT_WEATHER_MISMATCH = "weather_mismatch"
EVENT_FORECAST_SHOWN = "forecast_shown"
EVENT_INCIDENT_TRIAGED = "incident_triaged"

_LIVE_SOURCES = ("live", "cache")  # «настоящий» прогноз vs fallback (§8.6)


# ---------------------------------------------------------------------------
# Схемы (§8.7)
# ---------------------------------------------------------------------------

class AiMetrics(BaseModel):
    """KPI AI-слоя (§8.7). Все доли ∈ [0,1]; `avg_time_to_triage` — мс (≥0)."""

    recommendation_acceptance: float
    copilot_tool_success: float
    weather_mismatch_rate: float
    zone_hit_rate: float
    avg_time_to_triage: float
    forecast_coverage: float
    total_events: int


class DataQuality(BaseModel):
    """Доверие к данным (§8.7). Все `*_ratio` ∈ [0,1]; считаются из реальных view."""

    camera_offline_ratio: float
    missing_gps_ratio: float
    missing_media_ratio: float
    weather_mismatch_rate: float
    incidents_with_video_ratio: float
    total_incidents: int


class MetricEvent(BaseModel):
    """Вход эмиттера `POST /api/metrics/event`. Минимум — `name`; прочее опционально."""

    name: str
    incident_id: Optional[str] = None
    plate: Optional[str] = None
    latency_ms: Optional[int] = None
    source: Optional[str] = None
    success: Optional[bool] = None
    error_detail: Optional[str] = None


class TrackResult(BaseModel):
    """Ответ эмиттера: записалось ли событие (best-effort, не падает)."""

    tracked: bool


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------

def _ratio(numerator: float, denominator: float) -> float:
    """Доля, безопасная к нулю и к выходу за [0,1] (страховка от грязных данных)."""
    if not denominator:
        return 0.0
    value = numerator / denominator
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return round(value, 4)


def _table_exists(db: duckdb.DuckDBPyConnection, name: str) -> bool:
    """Есть ли таблица/view `name` (mem_db в тестах может не содержать всего)."""
    try:
        row = db.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = ?",
            [name],
        ).fetchone()
        return bool(row and row[0])
    except Exception:  # noqa: BLE001 — отсутствие каталога → считаем, что нет
        return False


def _counts_by_event(db: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """Срез `ai_metric_events`: на каждое имя события — total и доля success."""
    if not _table_exists(db, _TABLE):
        return []
    return rows_to_dicts(
        db.execute(
            f'''
            SELECT
              "feature_name"                                        AS "name",
              count(*)                                              AS "total",
              count(*) FILTER (WHERE "success" IS TRUE)             AS "ok",
              count(*) FILTER (WHERE "source" IN ('live', 'cache')) AS "real_src",
              avg("latency_ms")                                     AS "avg_latency"
            FROM "{_TABLE}"
            GROUP BY "feature_name"
            '''
        )
    )


def _weather_mismatch_rate(db: duckdb.DuckDBPyConnection) -> float:
    """Доля инцидентов с погодным расхождением — из `incident_weather` (b17).

    Единый источник истины для обоих эндпоинтов; таблицы нет → 0.0 (mem_db/пусто).
    """
    if not _table_exists(db, "incident_weather"):
        return 0.0
    row = db.execute(
        '''
        SELECT
          count(*)                                       AS "total",
          count(*) FILTER (WHERE "discrepancy" IS TRUE)  AS "mismatch"
        FROM "incident_weather"
        '''
    ).fetchone()
    total = row[0] if row else 0
    mismatch = row[1] if row else 0
    return _ratio(mismatch, total)


# ---------------------------------------------------------------------------
# Эмиттер событий (best-effort)
# ---------------------------------------------------------------------------

def _writable_connection() -> Optional[duckdb.DuckDBPyConnection]:
    """Открыть отдельный read-write коннект к БД для записи события.

    Основной коннект приложения read-only, поэтому пишем через свой инстанс.
    Любая проблема (нет файла / занят / read-only-конфликт в процессе) → None:
    эмиттер тогда no-op, продьюсер не падает.
    """
    if not settings.db_path.exists():
        return None
    try:
        return duckdb.connect(str(settings.db_path), read_only=False)
    except Exception as exc:  # noqa: BLE001 — конфликт коннектов/блокировка → no-op
        logger.debug("metrics: writable connection unavailable: %s", exc)
        return None


def track_event(
    name: str,
    *,
    db: Optional[duckdb.DuckDBPyConnection] = None,
    incident_id: Optional[str] = None,
    plate: Optional[str] = None,
    latency_ms: Optional[int] = None,
    source: Optional[str] = None,
    success: Optional[bool] = None,
    error_detail: Optional[str] = None,
    ts: Optional[datetime] = None,
) -> bool:
    """Записать одно событие в `ai_metric_events`. Best-effort: возвращает успех.

    `db` — writable-коннект (тесты передают свой). Без `db` — открываем
    собственный writable-коннект; недоступен или флаг `SKAI_METRICS_DISABLE`
    выставлен → no-op (`False`), без исключения. Продьюсер вызывает это в
    «огне-и-забыл» режиме — метрики не должны ронять продуктовый путь.
    """
    if os.environ.get("SKAI_METRICS_DISABLE", "").strip().lower() in (
        "1",
        "true",
        "on",
        "yes",
    ):
        return False

    own_conn: Optional[duckdb.DuckDBPyConnection] = None
    conn = db
    if conn is None:
        own_conn = _writable_connection()
        conn = own_conn
    if conn is None:
        return False

    event_ts = ts or datetime.now(timezone.utc)
    try:
        conn.execute(
            f'''
            INSERT INTO "{_TABLE}"
              ("id", "ts", "feature_name", "incident_id", "plate",
               "latency_ms", "source", "success", "error_detail")
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            [
                uuid.uuid4().hex,
                event_ts,
                name,
                incident_id,
                plate,
                latency_ms,
                source,
                success,
                error_detail,
            ],
        )
        return True
    except Exception as exc:  # noqa: BLE001 — запись метрики не критична
        logger.debug("metrics: track_event(%s) skipped: %s", name, exc)
        return False
    finally:
        if own_conn is not None:
            own_conn.close()


# ---------------------------------------------------------------------------
# Агрегация AiMetrics (детерминирована на наборе событий)
# ---------------------------------------------------------------------------

def get_ai_metrics(db: duckdb.DuckDBPyConnection) -> AiMetrics:
    """Свести KPI AI-слоя из `ai_metric_events` (§8.7). Пусто → нулевые дефолты."""
    by_name: dict[str, dict[str, Any]] = {
        r["name"]: r for r in _counts_by_event(db)
    }

    def total(name: str) -> int:
        return int(by_name.get(name, {}).get("total", 0) or 0)

    def ok(name: str) -> int:
        return int(by_name.get(name, {}).get("ok", 0) or 0)

    def real_src(name: str) -> int:
        return int(by_name.get(name, {}).get("real_src", 0) or 0)

    # recommendation_acceptance = принято / показано (funnel).
    acceptance = _ratio(
        total(EVENT_RECOMMENDATION_ACCEPTED), total(EVENT_RECOMMENDATION_SHOWN)
    )
    # copilot_tool_success = успешных вызовов tool / всех вызовов.
    copilot_success = _ratio(
        total(EVENT_COPILOT_TOOL_SUCCESS), total(EVENT_COPILOT_TOOL_CALLED)
    )
    # zone_hit_rate = доля открытий зоны, оказавшихся «горячими» (success=true).
    zone_hit = _ratio(ok(EVENT_ZONE_OPENED), total(EVENT_ZONE_OPENED))
    # forecast_coverage = доля показов прогноза с реальным источником (live/cache).
    forecast_cov = _ratio(
        real_src(EVENT_FORECAST_SHOWN), total(EVENT_FORECAST_SHOWN)
    )
    # avg_time_to_triage = средняя задержка триажа (мс), 0.0 при отсутствии событий.
    triage = by_name.get(EVENT_INCIDENT_TRIAGED, {})
    avg_triage = float(triage.get("avg_latency") or 0.0)

    total_events = sum(int(r.get("total", 0) or 0) for r in by_name.values())

    return AiMetrics(
        recommendation_acceptance=acceptance,
        copilot_tool_success=copilot_success,
        weather_mismatch_rate=_weather_mismatch_rate(db),
        zone_hit_rate=zone_hit,
        avg_time_to_triage=round(avg_triage, 2),
        forecast_coverage=forecast_cov,
        total_events=total_events,
    )


# ---------------------------------------------------------------------------
# Агрегация DataQuality (из реальных view)
# ---------------------------------------------------------------------------

def get_data_quality(db: duckdb.DuckDBPyConnection) -> DataQuality:
    """Свести качество данных из `v_incidents` + `incident_weather` (§8.7).

    Нет `v_incidents` (mem_db без сборки) → нулевые дефолты, без падения.
    Все `*_ratio` ∈ [0,1].
    """
    if not _table_exists(db, "v_incidents"):
        return DataQuality(
            camera_offline_ratio=0.0,
            missing_gps_ratio=0.0,
            missing_media_ratio=0.0,
            weather_mismatch_rate=_weather_mismatch_rate(db),
            incidents_with_video_ratio=0.0,
            total_incidents=0,
        )

    row = db.execute(
        '''
        SELECT
          count(*)                                                          AS "total",
          -- камера офлайн: оба канала (DMS + фронт) без медиа-URL.
          count(*) FILTER (
            WHERE "cam_dms_url" IS NULL AND "cam_front_url" IS NULL
          )                                                                 AS "cam_offline",
          -- нет GPS: отсутствует широта или долгота.
          count(*) FILTER (WHERE "lat" IS NULL OR "lon" IS NULL)            AS "no_gps",
          -- нет медиа: видео недоступно (video_available = 0).
          count(*) FILTER (WHERE "video_available" = 0)                     AS "no_media",
          -- есть видео: video_available = 1.
          count(*) FILTER (WHERE "video_available" = 1)                     AS "with_video"
        FROM "v_incidents"
        '''
    ).fetchone()

    total = row[0] if row else 0
    cam_offline, no_gps, no_media, with_video = (
        (row[1], row[2], row[3], row[4]) if row else (0, 0, 0, 0)
    )

    return DataQuality(
        camera_offline_ratio=_ratio(cam_offline, total),
        missing_gps_ratio=_ratio(no_gps, total),
        missing_media_ratio=_ratio(no_media, total),
        weather_mismatch_rate=_weather_mismatch_rate(db),
        incidents_with_video_ratio=_ratio(with_video, total),
        total_incidents=int(total or 0),
    )
