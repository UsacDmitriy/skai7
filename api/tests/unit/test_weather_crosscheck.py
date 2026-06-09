"""Unit-тесты weather-crosscheck (идея #11, модуль b17) — §8.1/§8.2.

Правило расхождения «сцена↔погода» (discrepancy/discrepancy_kind) и надбавка
weather_risk_bonus. Без сети — на кэше data/ai/weather_cache.json (54 строки).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

_WEATHER_CACHE = Path(__file__).resolve().parents[3] / "data" / "ai" / "weather_cache.json"

_API_WEATHER_VALID = {"clear", "rain", "snow", "fog", "unknown"}
_DISCREPANCY_KIND_VALID = {"weather", "daynight", "none"}


# ── Чистая логика расхождения §8.1 ─────────────────────────────────────────────


def _compute_discrepancy(
    scene_weather: str,
    api_weather: str,
    scene_day_night: str,
    api_is_day: bool,
) -> tuple[bool, str]:
    """Правило расхождения §8.1: (discrepancy, kind ∈ {weather,daynight,none}).

    Weather: scene_weather ≠ api_weather, оба известны → kind='weather'.
    Daynight: scene='night' и is_day=True (или 'day' и is_day=False) → kind='daynight'.
    'unknown' не порождает расхождений (§8.2 фолбэк).
    """
    if scene_weather != "unknown" and api_weather != "unknown" and scene_weather != api_weather:
        return True, "weather"
    if scene_day_night == "night" and api_is_day:
        return True, "daynight"
    if scene_day_night == "day" and not api_is_day:
        return True, "daynight"
    return False, "none"


# ── Фикстура кэша ───────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def weather_cache() -> list[dict]:
    """54 записи weather_cache.json (data/ai/)."""
    if not _WEATHER_CACHE.exists():
        pytest.skip(f"weather_cache.json не найден ({_WEATHER_CACHE})")
    raw = json.loads(_WEATHER_CACHE.read_text(encoding="utf-8"))
    return raw.get("records", raw) if isinstance(raw, dict) else raw


# ── Структура кэша ─────────────────────────────────────────────────────────────


def test_weather_cache_count(weather_cache: list[dict]) -> None:
    """incident_weather = 54 строки (§8.1)."""
    assert len(weather_cache) == 54


def test_weather_cache_is_day_bool(weather_cache: list[dict]) -> None:
    """is_day ∈ {true,false} — тип bool для каждой записи (§8.1)."""
    for r in weather_cache:
        assert isinstance(r["is_day"], bool), f"id={r['id']}: is_day={r['is_day']!r} не bool"


def test_incident_weather_discrepancy_kind_enum(real_db) -> None:
    """discrepancy_kind ∈ {weather,daynight,none} (§8.1).

    `discrepancy`/`discrepancy_kind` — производные поля: считаются в SQL
    (`31_incident_weather.sql` JOIN с `incident_scene`), а не в сыром кэше
    Open-Meteo. Поэтому проверяем таблицу `incident_weather`, а не cache JSON.
    """
    kinds = {row[0] for row in real_db.execute(
        'SELECT DISTINCT "discrepancy_kind" FROM "incident_weather"'
    ).fetchall()}
    assert kinds, "incident_weather пуст — выполни make db"
    assert kinds <= _DISCREPANCY_KIND_VALID, f"недопустимые kind: {kinds - _DISCREPANCY_KIND_VALID}"


def test_weather_cache_api_weather_enum(weather_cache: list[dict]) -> None:
    """api_weather ∈ {clear,rain,snow,fog,unknown} (§8.1)."""
    for r in weather_cache:
        assert r["api_weather"] in _API_WEATHER_VALID, (
            f"id={r['id']}: api_weather={r['api_weather']!r}"
        )


def test_weather_cache_required_fields(weather_cache: list[dict]) -> None:
    """Каждая запись кэша содержит сырые поля Open-Meteo (§8.1).

    `discrepancy`/`discrepancy_kind` — производные (SQL JOIN со сценой), их в
    сыром кэше нет; они проверяются на таблице (см. test_incident_weather_*)."""
    required = {"id", "ts", "lat", "lon", "api_weather", "is_day"}
    for r in weather_cache:
        missing = required - set(r)
        assert not missing, f"id={r.get('id')}: missing {missing}"


def test_incident_weather_table_has_discrepancy_fields(real_db) -> None:
    """Таблица `incident_weather` несёт производные `discrepancy`/`discrepancy_kind` (§8.1)."""
    cols = {row[1] for row in real_db.execute('PRAGMA table_info("incident_weather")').fetchall()}
    assert {"discrepancy", "discrepancy_kind"} <= cols, f"нет полей расхождения: {cols}"


# ── Логика расхождения ─────────────────────────────────────────────────────────


def test_discrepancy_weather_rain_vs_clear() -> None:
    """Сцена rain, API clear → discrepancy=True, kind='weather' (§8.1)."""
    disc, kind = _compute_discrepancy("rain", "clear", "day", True)
    assert disc is True
    assert kind == "weather"


def test_discrepancy_weather_night_scene_vs_api_day() -> None:
    """Сцена night, is_day=True → discrepancy=True, kind='daynight' (§8.1)."""
    disc, kind = _compute_discrepancy("clear", "clear", "night", True)
    assert disc is True
    assert kind == "daynight"


def test_discrepancy_day_scene_vs_api_night() -> None:
    """Сцена day, is_day=False → discrepancy=True, kind='daynight' (§8.1)."""
    disc, kind = _compute_discrepancy("clear", "clear", "day", False)
    assert disc is True
    assert kind == "daynight"


def test_discrepancy_none_weather_match() -> None:
    """Совпадение weather и day_night → discrepancy=False, kind='none'."""
    disc, kind = _compute_discrepancy("rain", "rain", "night", False)
    assert disc is False
    assert kind == "none"


def test_discrepancy_none_clear_day() -> None:
    """Полное совпадение clear+day → discrepancy=False, kind='none'."""
    disc, kind = _compute_discrepancy("clear", "clear", "day", True)
    assert disc is False
    assert kind == "none"


def test_discrepancy_unknown_scene_no_weather_conflict() -> None:
    """Сцена unknown не порождает weather-расхождение (фолбэк §8.2)."""
    disc, kind = _compute_discrepancy("unknown", "clear", "day", True)
    assert disc is False
    assert kind == "none"


def test_discrepancy_unknown_api_no_conflict() -> None:
    """API unknown не порождает weather-расхождение (§8.2)."""
    disc, kind = _compute_discrepancy("rain", "unknown", "night", False)
    assert disc is False
    assert kind == "none"


# ── weather_risk_bonus ─────────────────────────────────────────────────────────


def test_weather_risk_bonus_wet_road() -> None:
    """wet road_surface → надбавка > 0 (§8.2)."""
    from api.core.enrichment import weather_risk_bonus

    bonus = weather_risk_bonus({"road_surface": "wet", "visibility": "good"}, {})
    assert bonus > 0


def test_weather_risk_bonus_ice_road() -> None:
    """ice road_surface → надбавка > 0 (§8.2)."""
    from api.core.enrichment import weather_risk_bonus

    bonus = weather_risk_bonus({"road_surface": "ice", "visibility": "good"}, {})
    assert bonus > 0


def test_weather_risk_bonus_poor_visibility() -> None:
    """visibility=poor → надбавка > 0 (§8.2)."""
    from api.core.enrichment import weather_risk_bonus

    bonus = weather_risk_bonus({"road_surface": "dry", "visibility": "poor"}, {})
    assert bonus > 0


def test_weather_risk_bonus_monotone() -> None:
    """wet+poor > wet alone — монотонность надбавки (§8.2)."""
    from api.core.enrichment import weather_risk_bonus

    bonus_both = weather_risk_bonus({"road_surface": "wet", "visibility": "poor"}, {})
    bonus_wet = weather_risk_bonus({"road_surface": "wet", "visibility": "good"}, {})
    assert bonus_both > bonus_wet


def test_weather_risk_bonus_dry_good_zero() -> None:
    """dry + good visibility → надбавка = 0 (§8.2)."""
    from api.core.enrichment import weather_risk_bonus

    bonus = weather_risk_bonus({"road_surface": "dry", "visibility": "good"}, {})
    assert bonus == 0.0


def test_weather_risk_bonus_no_cache_backward_compat() -> None:
    """Без кэша (scene=None) → 0.0, обратная совместимость §8.2."""
    from api.core.enrichment import weather_risk_bonus

    assert weather_risk_bonus(None, None) == 0.0
    assert weather_risk_bonus(None, {}) == 0.0


# ── Регресс risk_score без weather (§2/§8.2) ───────────────────────────────────


def test_risk_score_deterministic_without_weather() -> None:
    """risk_score без weather_risk_bonus детерминирован и ∈ [0,100] (регресс §2)."""
    from api.core.enrichment import risk_score

    score = risk_score(
        severity="high",
        speed_kmh=80.0,
        speed_limit_kmh=90,
        is_night=False,
        events_last_7d=3,
    )
    score2 = risk_score(
        severity="high",
        speed_kmh=80.0,
        speed_limit_kmh=90,
        is_night=False,
        events_last_7d=3,
    )
    assert score == score2
    assert 0 <= score <= 100
