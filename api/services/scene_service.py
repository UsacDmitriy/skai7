"""Сервис сцен-контекста инцидента (§8.3/§8.4) — `GET /api/incidents/{id}/scene`.

Отдаёт `SceneContext` + `WeatherCrossCheck` по предрасчитанным таблицам
`incident_scene` (b16) и `incident_weather` (b17). Эндпоинт ничего не считает «вживую»:
данные уже материализованы из офлайн-кэша `data/ai/*.json` на этапе `make db`.

Governance (§8.6): ответ несёт мету `AiFeatureState` (поле `state`); неизвестный
инцидент → 404 (в роутере); известный инцидент без предрасчёта → детерминированный
фолбэк (`source="fallback"`, значения `unknown`), без 5xx.

Схемы держим здесь (как `forecast_service` свои) — общий `entities.py` не трогаем,
чтобы не плодить кросс-трек гонки.
"""

from __future__ import annotations

import math

import duckdb
from pydantic import BaseModel

from api.core.ai_flags import AiFeatureState
from api.repositories import rows_to_dicts

# Категориальные поля держим как `str` (а не Literal): предрасчёт b16/b17 может
# отдавать детерминированный фолбэк `"unknown"`, которого нет в TS-литералах §8.4 —
# валидация по Literal дала бы 500 на штатных данных. Деградация важнее строгости (§8.0).


class SceneContext(BaseModel):
    """Сценовый контекст инцидента (§8.4). `source` — происхождение разметки."""

    id: str
    weather: str
    day_night: str
    road_surface: str
    area: str
    visibility: str
    scene_confidence: float


class WeatherCrossCheck(BaseModel):
    """Сверка факта со внешним погодным API (§8.4)."""

    id: str
    api_weather: str
    is_day: bool
    solar_elevation_deg: float
    discrepancy: bool
    discrepancy_kind: str


class SceneResponse(BaseModel):
    """Объединённый ответ `GET /api/incidents/{id}/scene` (§8.3) + governance-мета (§8.6)."""

    scene: SceneContext
    weather: WeatherCrossCheck
    state: AiFeatureState


# Нормализация `incident_scene.source` → AiFeatureState.source ∈ {live,cache,fallback}.
_LIVE_SOURCES = {"vlm", "live"}
_FALLBACK_SOURCES = {"fallback", "placeholder", "", None}


def _f(value: object, default: float = 0.0) -> float:
    """Безопасный float: NaN/None/мусор → default (страховка от NaN в JSON)."""
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return default if math.isnan(result) else result


def incident_exists(db: duckdb.DuckDBPyConnection, incident_id: str) -> bool:
    """Инцидент известен, если присутствует в `v_incidents`."""
    row = db.execute(
        'SELECT 1 FROM "v_incidents" WHERE "id" = ? LIMIT 1', [incident_id]
    ).fetchone()
    return row is not None


def _scene_row(db: duckdb.DuckDBPyConnection, incident_id: str) -> dict | None:
    rows = rows_to_dicts(
        db.execute('SELECT * FROM "incident_scene" WHERE "id" = ? LIMIT 1', [incident_id])
    )
    return rows[0] if rows else None


def _weather_row(db: duckdb.DuckDBPyConnection, incident_id: str) -> dict | None:
    rows = rows_to_dicts(
        db.execute('SELECT * FROM "incident_weather" WHERE "id" = ? LIMIT 1', [incident_id])
    )
    return rows[0] if rows else None


def _scene_from_row(incident_id: str, row: dict | None) -> tuple[SceneContext, str]:
    """SceneContext + нормализованный source. `None` → детерминированный фолбэк (§8.0)."""
    if row is None:
        return (
            SceneContext(
                id=incident_id,
                weather="unknown",
                day_night="night",
                road_surface="unknown",
                area="unknown",
                visibility="unknown",
                scene_confidence=0.0,
            ),
            "fallback",
        )
    raw_source = (row.get("source") or "").strip().lower()
    if raw_source in _LIVE_SOURCES:
        source = "live"
    elif raw_source in _FALLBACK_SOURCES:
        source = "fallback"
    else:
        source = "cache"
    return (
        SceneContext(
            id=incident_id,
            weather=str(row.get("weather") or "unknown"),
            day_night=str(row.get("day_night") or "unknown"),
            road_surface=str(row.get("road_surface") or "unknown"),
            area=str(row.get("area") or "unknown"),
            visibility=str(row.get("visibility") or "unknown"),
            scene_confidence=_f(row.get("scene_confidence")),
        ),
        source,
    )


def _weather_from_row(incident_id: str, row: dict | None) -> WeatherCrossCheck:
    """WeatherCrossCheck из строки `incident_weather`. `None` → нейтральный фолбэк."""
    if row is None:
        return WeatherCrossCheck(
            id=incident_id,
            api_weather="unknown",
            is_day=False,
            solar_elevation_deg=0.0,
            discrepancy=False,
            discrepancy_kind="none",
        )
    return WeatherCrossCheck(
        id=incident_id,
        api_weather=str(row.get("api_weather") or "unknown"),
        is_day=bool(row.get("is_day")),
        solar_elevation_deg=_f(row.get("solar_elevation_deg")),
        discrepancy=bool(row.get("discrepancy")),
        discrepancy_kind=str(row.get("discrepancy_kind") or "none"),
    )


def get_scene(db: duckdb.DuckDBPyConnection, incident_id: str) -> SceneResponse:
    """Собрать ответ сцены для известного инцидента (валидность — в роутере, 404 там).

    Детерминированно: один инцидент → один ответ (Check §8.0). Без сети — читает
    только БД (материализованный офлайн-кэш). `state.source` отражает происхождение
    разметки. `latency_ms=0.0` фиксировано: «живого» AI-вызова на запросе нет —
    разметка предрасчитана офлайн (b16/b17), измерять нечего, иначе ответ недетерминирован.
    """
    scene, source = _scene_from_row(incident_id, _scene_row(db, incident_id))
    weather = _weather_from_row(incident_id, _weather_row(db, incident_id))
    return SceneResponse(
        scene=scene,
        weather=weather,
        state=AiFeatureState(
            name="scene", enabled=True, source=source, latency_ms=0.0
        ),
    )
