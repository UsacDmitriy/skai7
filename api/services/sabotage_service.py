"""Сервис домена sabotage (§7.2/§7.4/§7.5, идеи #9 + #16).

Читает сырые строки view `v_sabotage` (b11) и обогащает каждую `driver_name`
через `driver_reference` (§7.1, b7) по `vehicle_plate`. При отсутствии записи в
справочнике — синтетическое ФИО из `enrichment.driver_for` (фолбэк §7.1).

b23 (идея #16): «умный вердикт» — детерминированное усиление детекции кросс-проверкой
сцены. Базовая уверенность из правила `v_sabotage`; **+надбавка**, если снаружи день/ясно
(`incident_weather`/`incident_scene`, b16/b17) при тёмном DMS-кадре — камера «должна была
видеть»; **−** при ночи/тумане (тёмный кадр объясним внешними условиями). Нет кэша сцены →
прежний вердикт (базовая уверенность). Никакой сети/«живого» AI: читаем только материализованный
офлайн-кэш, один инцидент → один вердикт (детерминизм §8.0).
"""

from __future__ import annotations

import duckdb

from api.core import enrichment
from api.domain.sabotage import SabotageEvent
from api.repositories import rows_to_dicts

# Базовая уверенность: событие уже прошло правило v_sabotage (тёмный DMS / CAMERA_TAMPER
# при движении). Кросс-проверка сцены лишь усиливает/ослабляет её фиксированной надбавкой.
_BASE_CONFIDENCE = 0.5
_BONUS_DAY_CLEAR = 0.3  # день И ясно при тёмном кадре — камера «должна была видеть»
_BONUS_DAY_ONLY = 0.15  # день, но погода не ясная — частичное усиление
_PENALTY_NIGHT_FOG = 0.2  # ночь/туман — тёмный кадр объясним, ослабляем

# Категориальные значения сцены/погоды (b16/b17), при которых кадр объясним внешне.
_CLEAR = "clear"
_OBSCURED_WEATHER = {"fog", "rain", "snow"}
_OBSCURED_VISIBILITY = {"fog", "low", "poor"}

# Тексты причины — пользовательские (показывает виджет f19), держим по-русски как в §8 примерах.
_REASON_DAY_CLEAR = "день/ясно снаружи — камера должна была видеть"
_REASON_DAY_ONLY = "день снаружи — кадр должен был быть светлее"
_REASON_NIGHT_FOG = "ночь/туман — тёмный кадр объясним"
_REASON_NEUTRAL = "базовый вердикт: кросс-проверка сцены нейтральна"
_REASON_NO_CACHE = "базовый вердикт: нет кросс-проверки сцены"


def _maybe_row(
    db: duckdb.DuckDBPyConnection, table: str, incident_id: str
) -> dict | None:
    """Строка кэша сцены/погоды по `id`. Нет таблицы (старая БД) → None (обратная совместимость)."""
    try:
        rows = rows_to_dicts(
            db.execute(f'SELECT * FROM "{table}" WHERE "id" = ? LIMIT 1', [incident_id])
        )
    except duckdb.Error:
        return None
    return rows[0] if rows else None


def _verdict(
    dms_dark: bool, scene: dict | None, weather: dict | None
) -> tuple[float, str]:
    """Детерминированный вердикт: (confidence∈[0,1], reason).

    Кросс-проверка применима к тёмному DMS-кадру (`dms_dark`) — именно его «темнота»
    объяснима/подозрительна внешними условиями. Для видимого CAMERA_TAMPER аргумент
    тёмного кадра не работает → базовая уверенность.
    """
    if scene is None and weather is None:
        return _BASE_CONFIDENCE, _REASON_NO_CACHE

    is_day = bool(weather.get("is_day")) if weather else False
    api_weather = str((weather or {}).get("api_weather") or "unknown").lower()
    day_night = str((scene or {}).get("day_night") or "unknown").lower()
    scene_weather = str((scene or {}).get("weather") or "unknown").lower()
    visibility = str((scene or {}).get("visibility") or "unknown").lower()

    daylight = is_day or day_night == "day"
    clear = api_weather == _CLEAR or scene_weather == _CLEAR
    night = (weather is not None and not is_day) or day_night == "night"
    fog = (
        scene_weather in _OBSCURED_WEATHER
        or api_weather in _OBSCURED_WEATHER
        or visibility in _OBSCURED_VISIBILITY
    )

    confidence = _BASE_CONFIDENCE
    if dms_dark and daylight and clear:
        confidence += _BONUS_DAY_CLEAR
        reason = _REASON_DAY_CLEAR
    elif dms_dark and daylight:
        confidence += _BONUS_DAY_ONLY
        reason = _REASON_DAY_ONLY
    elif dms_dark and (night or fog):
        confidence -= _PENALTY_NIGHT_FOG
        reason = _REASON_NIGHT_FOG
    else:
        reason = _REASON_NEUTRAL

    confidence = round(min(1.0, max(0.0, confidence)), 2)
    return confidence, reason


def list_sabotage(db: duckdb.DuckDBPyConnection) -> list[SabotageEvent]:
    """GET /api/sabotage. Пустой `v_sabotage` → `[]` (не ошибка, не 404)."""
    rows = rows_to_dicts(db.execute('SELECT * FROM "v_sabotage"'))
    events: list[SabotageEvent] = []
    for row in rows:
        plate = row.get("vehicle_plate") or ""
        driver_name = enrichment.driver_for(db, plate)["driver"]
        incident_id = str(row.get("id") or "")
        dms_dark = bool(row.get("dms_dark"))
        scene = _maybe_row(db, "incident_scene", incident_id)
        weather = _maybe_row(db, "incident_weather", incident_id)
        confidence, reason = _verdict(dms_dark, scene, weather)
        events.append(
            SabotageEvent(
                id=row["id"],
                vehicle_plate=plate,
                ts=row.get("ts") or "",
                dms_dark=dms_dark,
                speed_kmh=float(row.get("speed_kmh") or 0.0),
                driver_name=driver_name,
                video_url=row.get("video_url"),
                verdict_confidence=confidence,
                verdict_reason=reason,
            )
        )
    return events
