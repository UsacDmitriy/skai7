"""Unit/integration-тесты прогноза риска (b18, §8.4).

Покрывают чистые функции (`_aggregate_days`/`_dense_series`/`_trend_*`/
`_detect_anomaly`/`_recommendations`) без БД, поведение `forecast()` на in-memory
DuckDB и HTTP-контракт `GET /api/reports/forecast/{plate}` против собранной базы.
"""

from __future__ import annotations

from datetime import date

import pytest

from api.services import forecast_service as fc
from api.services.forecast_service import (
    RiskForecast,
    _aggregate_days,
    _DayStat,
    _dense_series,
    _detect_anomaly,
    _recommendations,
    _trend_arima,
    _trend_baseline,
)


def _row(code: str, ts: str, speed: float = 50.0) -> dict:
    return {"alarm_code": code, "ts": ts, "speed_kmh": speed}


# ---------------------------------------------------------------------------
# Агрегация дневного ряда.
# ---------------------------------------------------------------------------


def test_aggregate_days_counts_night_and_harsh():
    rows = [
        _row("HARSH_BRAKING", "2026-05-14 23:30:00+00:00", 80.0),  # ночь (UTC) + harsh
        _row("ADAS_HMW", "2026-05-14 12:00:00+00:00", 44.0),       # день
        _row("DMS_YAWNING", "2026-05-16 02:00:00+00:00", 60.0),    # ночь (UTC)
    ]
    days = _aggregate_days(rows)
    d14 = days[date(2026, 5, 14)]
    assert d14.count == 2
    assert d14.max_speed == 80.0
    assert d14.night == 1
    assert d14.harsh == 1
    assert d14.night_share == 0.5
    assert d14.harsh_share == 0.5
    assert days[date(2026, 5, 16)].count == 1


def test_dense_series_zero_fills_gaps():
    rows = [_row("ADAS_HMW", "2026-05-10 12:00:00+00:00")]
    days = _aggregate_days(rows)
    out_days, out_stats = _dense_series(days, anchor=date(2026, 5, 14))
    assert len(out_days) == 5  # 10..14 включительно
    assert [s.count for s in out_stats] == [1, 0, 0, 0, 0]


# ---------------------------------------------------------------------------
# Тренд: базлайн и ARIMA. Инвариант ci_low ≤ predicted ≤ ci_high, длина 7.
# ---------------------------------------------------------------------------


def _assert_valid_trend(trend):
    assert len(trend) == fc._HORIZON == 7
    for p in trend:
        assert p.ci_low <= p.predicted_events <= p.ci_high
        assert p.ci_low >= 0.0


def test_trend_baseline_invariant_and_length():
    _assert_valid_trend(_trend_baseline([1, 0, 2, 3, 1], anchor=date(2026, 5, 18)))


def test_trend_baseline_empty_history_is_zero():
    trend = _trend_baseline([], anchor=date(2026, 5, 18))
    _assert_valid_trend(trend)
    assert all(p.predicted_events == 0.0 for p in trend)
    assert trend[0].date == "2026-05-19"  # anchor + 1 день


def test_trend_arima_none_when_too_few_points():
    assert _trend_arima([1, 2, 3], anchor=date(2026, 5, 18)) is None


@pytest.mark.filterwarnings("ignore")
def test_trend_arima_produces_valid_seven_points():
    counts = [1, 2, 1, 3, 2, 4, 3, 5, 4, 6]  # ≥ _MIN_ARIMA_DAYS, выраженный тренд
    trend = _trend_arima(counts, anchor=date(2026, 5, 18))
    if trend is None:  # statsmodels отсутствует/не сошёлся → фолбэк, тест неприменим
        pytest.skip("ARIMA недоступна в окружении")
    _assert_valid_trend(trend)


# ---------------------------------------------------------------------------
# Аномалия.
# ---------------------------------------------------------------------------


def test_anomaly_insufficient_history_is_false():
    stats = [_DayStat() for _ in range(3)]
    anomaly, reason = _detect_anomaly(stats)
    assert anomaly is False
    assert reason == "недостаточно истории"


def test_anomaly_detects_spike():
    stats = []
    for _ in range(9):  # ровный фон
        s = _DayStat()
        s.count = 1
        s.max_speed = 50.0
        stats.append(s)
    spike = _DayStat()  # резкий всплеск числа событий
    spike.count = 40
    spike.max_speed = 140.0
    stats.append(spike)

    anomaly, reason = _detect_anomaly(stats)
    if reason == "недостаточно истории":
        pytest.skip("sklearn недоступен в окружении")
    assert anomaly is True
    assert reason and "аномалия по фиче" in reason


# ---------------------------------------------------------------------------
# Рекомендации.
# ---------------------------------------------------------------------------


def test_recommendations_empty_history_is_empty():
    assert _recommendations([]) == []


def test_recommendations_night_history_is_relevant():
    rows = [
        _row("DMS_DROWSY", "2026-05-14 23:00:00+00:00"),
        _row("DMS_YAWNING", "2026-05-14 23:30:00+00:00"),
        _row("ADAS_HMW", "2026-05-14 12:00:00+00:00"),
    ]
    recs = _recommendations(rows)
    assert recs  # непуст
    assert any("ночь" in r for r in recs)
    assert any("усталост" in r for r in recs)


def test_recommendations_no_factors_has_default():
    recs = _recommendations([_row("ADAS_HMW", "2026-05-14 12:00:00+00:00")])
    assert len(recs) == 1
    assert "стандартный мониторинг" in recs[0]


# ---------------------------------------------------------------------------
# forecast() на in-memory DuckDB: пустая история и детерминизм.
# ---------------------------------------------------------------------------


def _seed_incidents(db, load_rows, rows: list[dict]) -> None:
    load_rows(
        db,
        "v_incidents",
        rows,
        columns=["vehicle_plate", "alarm_code", "ts", "speed_kmh"],
    )
    load_rows(db, "video_events__vehicles", [], columns=["unit_state_number"])


def test_forecast_empty_history_is_valid(mem_db, load_rows):
    """Известный ТС без алярмов → валидный нулевой прогноз, без исключения."""
    _seed_incidents(
        mem_db,
        load_rows,
        [{"vehicle_plate": "OTHER", "alarm_code": "ADAS_HMW",
          "ts": "2026-05-18 10:00:00+00:00", "speed_kmh": 40.0}],
    )
    result = fc.forecast(mem_db, "EMPTY")
    assert isinstance(result, RiskForecast)
    assert len(result.trend) == 7
    assert all(p.predicted_events == 0.0 for p in result.trend)
    assert result.anomaly is False
    assert result.anomaly_reason == "недостаточно истории"
    # anchor = глобальный максимум ts (2026-05-18) + 1.
    assert result.trend[0].date == "2026-05-19"


def test_forecast_is_deterministic(mem_db, load_rows):
    rows = [
        {"vehicle_plate": "А001АА01", "alarm_code": "DMS_DROWSY",
         "ts": "2026-05-14 23:00:00+00:00", "speed_kmh": 60.0},
        {"vehicle_plate": "А001АА01", "alarm_code": "HARSH_BRAKING",
         "ts": "2026-05-15 23:30:00+00:00", "speed_kmh": 90.0},
    ]
    _seed_incidents(mem_db, load_rows, rows)
    first = fc.forecast(mem_db, "А001АА01")
    second = fc.forecast(mem_db, "А001АА01")
    assert first.model_dump() == second.model_dump()
    _assert_valid_trend(first.trend)
    assert first.recommendations  # ночные/усталость/резкие → непусто


def test_plate_exists(mem_db, load_rows):
    _seed_incidents(
        mem_db,
        load_rows,
        [{"vehicle_plate": "KNOWN", "alarm_code": "ADAS_HMW",
          "ts": "2026-05-18 10:00:00+00:00", "speed_kmh": 40.0}],
    )
    assert fc.plate_exists(mem_db, "KNOWN") is True
    assert fc.plate_exists(mem_db, "NOPE") is False


# ---------------------------------------------------------------------------
# HTTP-контракт против собранной базы (skip при отсутствии).
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    from api.core.config import settings

    if not settings.db_path.exists():
        pytest.skip(f"DuckDB не собран ({settings.db_path}); запусти `make db`.")
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as c:
        yield c


def _any_plate() -> str:
    from api.core.config import settings
    import duckdb

    conn = duckdb.connect(str(settings.db_path), read_only=True)
    try:
        row = conn.execute(
            'SELECT "vehicle_plate" FROM "v_incidents" '
            'GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 1'
        ).fetchone()
    finally:
        conn.close()
    return row[0]


def test_endpoint_returns_valid_forecast(client):
    plate = _any_plate()
    resp = client.get(f"/api/reports/forecast/{plate}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["plate"] == plate
    assert len(body["trend"]) == 7
    for p in body["trend"]:
        assert p["ci_low"] <= p["predicted_events"] <= p["ci_high"]
    assert isinstance(body["recommendations"], list)
    assert isinstance(body["anomaly"], bool)


def test_endpoint_unknown_plate_404(client):
    resp = client.get("/api/reports/forecast/UNKNOWN-PLATE-XYZ")
    assert resp.status_code == 404
