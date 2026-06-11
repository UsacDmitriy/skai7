"""Unit-покрытие метрик/data-quality (b25) — §8.7, идея #18.

`metrics_service` даёт два детерминированных среза AI-слоя:
  * `get_ai_metrics`   — KPI из событийной таблицы `ai_metric_events` (funnel-доли);
  * `get_data_quality` — доверие к данным из view `v_incidents` + `incident_weather`.
Плюс эмиттер `track_event` (best-effort запись события).

Проверяем (Check tu-metrics): детерминизм агрегации (повтор → идентично),
пустой набор → нулевые дефолты (без падения / без деления на ноль),
все `*_ratio ∈ [0,1]`. Без сети: in-memory DuckDB на сэмпле.
"""

from __future__ import annotations

from typing import Any

import pytest

from api.services import metrics_service as ms

# Каноничная схема `ai_metric_events` (33_ai_metric_events.sql, w3-16) — событие = строка.
_EVENTS_DDL = '''
CREATE TABLE "ai_metric_events" (
  "id"            VARCHAR,
  "ts"            TIMESTAMP,
  "feature_name"  VARCHAR,
  "incident_id"   VARCHAR,
  "plate"         VARCHAR,
  "latency_ms"    INTEGER,
  "source"        VARCHAR,
  "success"       BOOLEAN,
  "error_detail"  VARCHAR
)
'''

# Колонки `v_incidents`, которые читает get_data_quality (остальные не нужны).
_VINC_DDL = '''
CREATE TABLE "v_incidents" (
  "cam_dms_url"     VARCHAR,
  "cam_front_url"   VARCHAR,
  "lat"             DOUBLE,
  "lon"             DOUBLE,
  "video_available" INTEGER
)
'''

_WEATHER_DDL = '''
CREATE TABLE "incident_weather" ("discrepancy" BOOLEAN)
'''


def _make_events_table(db) -> None:
    db.execute(_EVENTS_DDL)


def _insert_events(db, names_with_meta: list[dict[str, Any]]) -> None:
    """Вставить события явным INSERT (None → настоящий NULL, без pandas-NaN)."""
    rows = [
        (
            f"id{i}",
            "2026-06-01T12:00:00",
            m["name"],
            None,
            None,
            m.get("latency_ms"),
            m.get("source"),
            m.get("success"),
            None,
        )
        for i, m in enumerate(names_with_meta)
    ]
    db.executemany(
        'INSERT INTO "ai_metric_events" '
        '("id","ts","feature_name","incident_id","plate","latency_ms",'
        '"source","success","error_detail") VALUES (?,?,?,?,?,?,?,?,?)',
        rows,
    )


def _sample_events() -> list[dict[str, Any]]:
    """Детерминированный набор парных funnel-событий с известными долями."""
    ev: list[dict[str, Any]] = []
    # recommendation: показано 4, принято 3 → acceptance = 0.75
    ev += [{"name": ms.EVENT_RECOMMENDATION_SHOWN}] * 4
    ev += [{"name": ms.EVENT_RECOMMENDATION_ACCEPTED}] * 3
    # copilot tool: вызвано 5, успешно 4 → 0.8
    ev += [{"name": ms.EVENT_COPILOT_TOOL_CALLED}] * 5
    ev += [{"name": ms.EVENT_COPILOT_TOOL_SUCCESS}] * 4
    # zone_opened 4, из них success=True 1 → zone_hit = 0.25
    ev += [{"name": ms.EVENT_ZONE_OPENED, "success": True}]
    ev += [{"name": ms.EVENT_ZONE_OPENED, "success": False}] * 3
    # forecast_shown 4: live 2 + cache 1 (реальные) + fallback 1 → coverage 0.75
    ev += [{"name": ms.EVENT_FORECAST_SHOWN, "source": "live"}] * 2
    ev += [{"name": ms.EVENT_FORECAST_SHOWN, "source": "cache"}]
    ev += [{"name": ms.EVENT_FORECAST_SHOWN, "source": "fallback"}]
    # incident_triaged 2 с latency 100 и 300 → avg_time_to_triage = 200.0
    ev += [{"name": ms.EVENT_INCIDENT_TRIAGED, "latency_ms": 100}]
    ev += [{"name": ms.EVENT_INCIDENT_TRIAGED, "latency_ms": 300}]
    return ev


# ---------------------------------------------------------------------------
# AiMetrics — детерминированная агрегация funnel-долей.
# ---------------------------------------------------------------------------


def test_ai_metrics_known_aggregation(mem_db) -> None:
    """Доли считаются по контракту §8.7 на известном наборе событий."""
    _make_events_table(mem_db)
    _insert_events(mem_db, _sample_events())

    m = ms.get_ai_metrics(mem_db)

    assert m.recommendation_acceptance == pytest.approx(0.75)
    assert m.copilot_tool_success == pytest.approx(0.8)
    assert m.zone_hit_rate == pytest.approx(0.25)
    assert m.forecast_coverage == pytest.approx(0.75)
    assert m.avg_time_to_triage == pytest.approx(200.0)
    assert m.total_events == 26


def test_ai_metrics_deterministic(mem_db) -> None:
    """Повторная агрегация того же набора → идентичный результат (Check)."""
    _make_events_table(mem_db)
    _insert_events(mem_db, _sample_events())

    first = ms.get_ai_metrics(mem_db)
    second = ms.get_ai_metrics(mem_db)

    assert first == second


def test_ai_metrics_ratios_in_range(mem_db) -> None:
    """Все KPI-доли остаются в [0,1] (страховка `_ratio`)."""
    _make_events_table(mem_db)
    _insert_events(mem_db, _sample_events())

    m = ms.get_ai_metrics(mem_db)
    for value in (
        m.recommendation_acceptance,
        m.copilot_tool_success,
        m.zone_hit_rate,
        m.forecast_coverage,
    ):
        assert 0.0 <= value <= 1.0


def test_ai_metrics_empty_table_defaults(mem_db) -> None:
    """Пустая таблица событий → нулевые дефолты, без деления на ноль."""
    _make_events_table(mem_db)

    m = ms.get_ai_metrics(mem_db)

    assert m.recommendation_acceptance == 0.0
    assert m.copilot_tool_success == 0.0
    assert m.zone_hit_rate == 0.0
    assert m.forecast_coverage == 0.0
    assert m.avg_time_to_triage == 0.0
    assert m.weather_mismatch_rate == 0.0
    assert m.total_events == 0


def test_ai_metrics_no_table_does_not_crash(mem_db) -> None:
    """Нет таблицы `ai_metric_events` (mem_db без каркаса) → нули, не падает."""
    m = ms.get_ai_metrics(mem_db)

    assert m.total_events == 0
    assert m.recommendation_acceptance == 0.0


def test_ai_metrics_weather_mismatch_from_table(mem_db) -> None:
    """`weather_mismatch_rate` считается из `incident_weather` (2 из 5 → 0.4)."""
    _make_events_table(mem_db)
    mem_db.execute(_WEATHER_DDL)
    mem_db.executemany(
        'INSERT INTO "incident_weather" ("discrepancy") VALUES (?)',
        [(True,), (True,), (False,), (False,), (False,)],
    )

    m = ms.get_ai_metrics(mem_db)

    assert m.weather_mismatch_rate == pytest.approx(0.4)
    assert 0.0 <= m.weather_mismatch_rate <= 1.0


# ---------------------------------------------------------------------------
# DataQuality — доли из реальных view, все в [0,1].
# ---------------------------------------------------------------------------


def _make_v_incidents(db) -> None:
    db.execute(_VINC_DDL)
    rows = [
        # cam offline (оба url NULL), нет gps (lat NULL), нет медиа (video=0)
        (None, None, None, None, 0),
        # норм: dms есть, gps есть, видео есть
        ("dms://1", None, 55.0, 37.0, 1),
        # нет gps (lon NULL), видео есть
        (None, "front://3", 55.0, None, 1),
        # нет медиа (video=0), gps есть, камеры есть
        ("dms://a", "front://b", 55.0, 37.0, 0),
    ]
    db.executemany(
        'INSERT INTO "v_incidents" '
        '("cam_dms_url","cam_front_url","lat","lon","video_available") '
        "VALUES (?,?,?,?,?)",
        rows,
    )


def test_data_quality_known_ratios(mem_db) -> None:
    """Доли качества данных считаются по §8.7 на детерминированном наборе."""
    _make_v_incidents(mem_db)

    dq = ms.get_data_quality(mem_db)

    assert dq.total_incidents == 4
    assert dq.camera_offline_ratio == pytest.approx(0.25)   # 1/4
    assert dq.missing_gps_ratio == pytest.approx(0.5)        # 2/4
    assert dq.missing_media_ratio == pytest.approx(0.5)      # 2/4
    assert dq.incidents_with_video_ratio == pytest.approx(0.5)  # 2/4


def test_data_quality_ratios_in_range(mem_db) -> None:
    """Все `*_ratio ∈ [0,1]` (Check tu-metrics)."""
    _make_v_incidents(mem_db)

    dq = ms.get_data_quality(mem_db)
    for value in (
        dq.camera_offline_ratio,
        dq.missing_gps_ratio,
        dq.missing_media_ratio,
        dq.weather_mismatch_rate,
        dq.incidents_with_video_ratio,
    ):
        assert 0.0 <= value <= 1.0


def test_data_quality_no_view_defaults(mem_db) -> None:
    """Нет `v_incidents` (mem_db без сборки) → нулевые дефолты, без падения."""
    dq = ms.get_data_quality(mem_db)

    assert dq.total_incidents == 0
    assert dq.camera_offline_ratio == 0.0
    assert dq.missing_gps_ratio == 0.0
    assert dq.missing_media_ratio == 0.0
    assert dq.incidents_with_video_ratio == 0.0
    assert dq.weather_mismatch_rate == 0.0


def test_data_quality_deterministic(mem_db) -> None:
    """Повтор агрегации data-quality → идентично."""
    _make_v_incidents(mem_db)

    assert ms.get_data_quality(mem_db) == ms.get_data_quality(mem_db)


# ---------------------------------------------------------------------------
# Эмиттер track_event — best-effort запись в переданный коннект.
# ---------------------------------------------------------------------------


def test_track_event_writes_row(mem_db) -> None:
    """`track_event` с явным db пишет строку события и возвращает True."""
    _make_events_table(mem_db)

    ok = ms.track_event(
        ms.EVENT_COPILOT_TOOL_SUCCESS,
        db=mem_db,
        latency_ms=42,
        source="live",
        success=True,
    )

    assert ok is True
    row = mem_db.execute(
        'SELECT "feature_name","latency_ms","source","success" '
        'FROM "ai_metric_events"'
    ).fetchone()
    assert row == (ms.EVENT_COPILOT_TOOL_SUCCESS, 42, "live", True)


def test_track_event_disabled_flag_is_noop(mem_db, monkeypatch) -> None:
    """`SKAI_METRICS_DISABLE` → no-op (False), событие не пишется, без падения."""
    _make_events_table(mem_db)
    monkeypatch.setenv("SKAI_METRICS_DISABLE", "true")

    ok = ms.track_event(ms.EVENT_ZONE_OPENED, db=mem_db, success=True)

    assert ok is False
    count = mem_db.execute('SELECT count(*) FROM "ai_metric_events"').fetchone()[0]
    assert count == 0


def test_track_event_feeds_aggregation(mem_db) -> None:
    """Записанные эмиттером события попадают в агрегацию (сквозной инвариант)."""
    _make_events_table(mem_db)

    ms.track_event(ms.EVENT_RECOMMENDATION_SHOWN, db=mem_db)
    ms.track_event(ms.EVENT_RECOMMENDATION_SHOWN, db=mem_db)
    ms.track_event(ms.EVENT_RECOMMENDATION_ACCEPTED, db=mem_db)

    m = ms.get_ai_metrics(mem_db)
    assert m.recommendation_acceptance == pytest.approx(0.5)  # 1 принято / 2 показано
    assert m.total_events == 3
