"""Unit-покрытие прогноза риска b18 (forecast_service) — §8.3/§8.4, идея #12.

Без сети и без поднятого uvicorn. Тестирует:
  * trend длиной 7 + инвариант ci_low ≤ predicted_events ≤ ci_high (§8.4)
  * детерминизм: один вход → один выход (random_state=42)
  * аномалия: всплеск в истории → anomaly=True / reason непуст; ровный ряд → False
  * рекомендации: ночные события → коучинг по ночной бдительности
  * пустая история → нулевой прогноз без исключения; неизвестный plate → не падает
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from api.services.forecast_service import (
    RiskForecast,
    _DayStat,
    _aggregate_days,
    _detect_anomaly,
    _recommendations,
    _trend_baseline,
    forecast,
)

# ---------------------------------------------------------------------------
# Константы для тестов
# ---------------------------------------------------------------------------

_ANCHOR = date(2026, 6, 1)
_NIGHT_TS = "2026-06-01T23:00:00Z"   # UTC hour=23 → is_night
_DAY_TS   = "2026-06-01T12:00:00Z"   # UTC hour=12 → not night


# ---------------------------------------------------------------------------
# Вспомогательные построители
# ---------------------------------------------------------------------------


def _flat_stats(n: int, count: int = 2) -> list[_DayStat]:
    """n одинаковых _DayStat с count алярмами и нулевой скоростью."""
    stats: list[_DayStat] = []
    for _ in range(n):
        s = _DayStat()
        s.count = count
        stats.append(s)
    return stats


def _spike_stats(n: int, spike_count: int = 200) -> list[_DayStat]:
    """n-1 тихих дней (count=1) + 1 день с огромным всплеском."""
    stats = _flat_stats(n - 1, count=1)
    spike = _DayStat()
    spike.count = spike_count
    spike.max_speed = 180.0
    stats.append(spike)
    return stats


def _setup_v_incidents(mem_db, load_rows, rows=None) -> None:
    """Создать таблицу v_incidents в mem_db (пустую или с данными)."""
    columns = ["vehicle_plate", "alarm_code", "ts", "speed_kmh"]
    load_rows(mem_db, "v_incidents", rows or [], columns=columns)


# ---------------------------------------------------------------------------
# 1. Тренд: длина 7 + инвариант ci_low ≤ predicted ≤ ci_high
# ---------------------------------------------------------------------------


class TestTrendBaseline:
    def test_trend_length_is_7(self) -> None:
        trend = _trend_baseline([2, 3, 1], _ANCHOR)
        assert len(trend) == 7

    def test_ci_invariant_on_variable_history(self) -> None:
        trend = _trend_baseline([1, 2, 3, 4, 5], _ANCHOR)
        for pt in trend:
            assert pt.ci_low <= pt.predicted_events <= pt.ci_high, (
                f"{pt.date}: ci_low={pt.ci_low} pred={pt.predicted_events} ci_high={pt.ci_high}"
            )

    def test_ci_invariant_on_uniform_history(self) -> None:
        trend = _trend_baseline([3, 3, 3, 3, 3, 3, 3], _ANCHOR)
        for pt in trend:
            assert pt.ci_low <= pt.predicted_events <= pt.ci_high

    def test_empty_history_zero_forecast(self) -> None:
        trend = _trend_baseline([], _ANCHOR)
        assert len(trend) == 7
        for pt in trend:
            assert pt.predicted_events == 0.0
            assert pt.ci_low == 0.0
            assert pt.ci_high == 0.0

    def test_dates_are_consecutive_after_anchor(self) -> None:
        trend = _trend_baseline([1, 2], _ANCHOR)
        assert len(trend) == 7
        for i, pt in enumerate(trend):
            expected = (_ANCHOR + timedelta(days=i + 1)).isoformat()
            assert pt.date == expected


# ---------------------------------------------------------------------------
# 2. Детерминизм: один вход → один выход
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_baseline_same_input_same_output(self) -> None:
        counts = [2, 5, 1, 3, 4]
        out1 = _trend_baseline(counts, _ANCHOR)
        out2 = _trend_baseline(counts, _ANCHOR)
        assert [pt.predicted_events for pt in out1] == [pt.predicted_events for pt in out2]
        assert [pt.ci_low for pt in out1] == [pt.ci_low for pt in out2]
        assert [pt.ci_high for pt in out1] == [pt.ci_high for pt in out2]

    def test_aggregate_days_deterministic(self) -> None:
        rows = [
            {"ts": "2026-06-01T10:00:00Z", "alarm_code": "DMS_DROWSY", "speed_kmh": 60.0},
            {"ts": "2026-06-01T14:00:00Z", "alarm_code": "OVERSPEED",  "speed_kmh": 90.0},
            {"ts": "2026-06-02T09:00:00Z", "alarm_code": "HARSH_BRAKING", "speed_kmh": 70.0},
        ]
        out1 = _aggregate_days(rows)
        out2 = _aggregate_days(rows)
        assert set(out1.keys()) == set(out2.keys())
        for d in out1:
            assert out1[d].count == out2[d].count
            assert out1[d].max_speed == out2[d].max_speed
            assert out1[d].night == out2[d].night


# ---------------------------------------------------------------------------
# 3. Аномалия: fallback при нехватке данных; всплеск → True; ровный → False
# ---------------------------------------------------------------------------


class TestAnomalyDetection:
    def test_insufficient_history_returns_false_with_reason(self) -> None:
        stats = _flat_stats(3)   # < 8 дней → детерминированный fallback
        anomaly, reason = _detect_anomaly(stats)
        assert anomaly is False
        assert reason == "недостаточно истории"

    def test_empty_stats_returns_false_with_reason(self) -> None:
        anomaly, reason = _detect_anomaly([])
        assert anomaly is False
        assert reason == "недостаточно истории"

    def test_flat_series_no_anomaly(self) -> None:
        pytest.importorskip("sklearn", reason="sklearn недоступен — пропуск ML-теста")
        stats = _flat_stats(12, count=2)   # ровный ряд, 12 дней
        anomaly, _ = _detect_anomaly(stats)
        assert anomaly is False

    def test_spike_triggers_anomaly_with_nonempty_reason(self) -> None:
        pytest.importorskip("sklearn", reason="sklearn недоступен — пропуск ML-теста")
        stats = _spike_stats(15)   # 14 тихих + 1 всплеск count=200
        anomaly, reason = _detect_anomaly(stats)
        assert anomaly is True
        assert reason is not None and len(reason) > 0


# ---------------------------------------------------------------------------
# 4. Рекомендации: ночные события → коучинг по ночной бдительности
# ---------------------------------------------------------------------------


class TestRecommendations:
    def test_night_majority_triggers_coaching(self) -> None:
        rows = [
            {"ts": _NIGHT_TS, "alarm_code": "DMS_DROWSY", "speed_kmh": 60.0},
            {"ts": _NIGHT_TS, "alarm_code": "OVERSPEED",   "speed_kmh": 95.0},
            {"ts": _DAY_TS,   "alarm_code": "OVERSPEED",   "speed_kmh": 90.0},
        ]
        recs = _recommendations(rows)
        joined = " ".join(recs).lower()
        assert "бдительност" in joined, f"Ожидался коучинг по бдительности, получено: {recs}"

    def test_all_day_events_no_night_coaching(self) -> None:
        rows = [
            {"ts": _DAY_TS, "alarm_code": "HARSH_BRAKING", "speed_kmh": 70.0},
            {"ts": _DAY_TS, "alarm_code": "HARSH_BRAKING", "speed_kmh": 65.0},
            {"ts": _DAY_TS, "alarm_code": "HARSH_BRAKING", "speed_kmh": 60.0},
        ]
        recs = _recommendations(rows)
        joined = " ".join(recs).lower()
        assert "ночн" not in joined, f"Не должно быть ночного коучинга: {recs}"

    def test_empty_rows_returns_empty_list(self) -> None:
        assert _recommendations([]) == []

    def test_fatigue_events_trigger_shift_review(self) -> None:
        rows = [
            {"ts": _DAY_TS, "alarm_code": "DMS_DROWSY",  "speed_kmh": 60.0},
            {"ts": _DAY_TS, "alarm_code": "DMS_YAWNING", "speed_kmh": 55.0},
        ]
        recs = _recommendations(rows)
        joined = " ".join(recs).lower()
        assert "усталост" in joined or "смен" in joined or "перерыв" in joined, (
            f"Ожидались рекомендации по усталости: {recs}"
        )

    def test_single_event_no_crash(self) -> None:
        rows = [{"ts": _DAY_TS, "alarm_code": "DMS_DROWSY", "speed_kmh": 60.0}]
        recs = _recommendations(rows)
        assert isinstance(recs, list)


# ---------------------------------------------------------------------------
# 5. forecast() с mem_db — пустая история и данные
# ---------------------------------------------------------------------------


class TestForecastWithMemDb:
    def test_empty_history_returns_valid_zero_forecast(self, mem_db, load_rows) -> None:
        _setup_v_incidents(mem_db, load_rows)
        result = forecast(mem_db, "EMPTY001")
        assert isinstance(result, RiskForecast)
        assert result.plate == "EMPTY001"
        assert len(result.trend) == 7
        for pt in result.trend:
            assert pt.predicted_events == 0.0
            assert pt.ci_low == 0.0
            assert pt.ci_high == 0.0

    def test_unknown_plate_does_not_crash(self, mem_db, load_rows) -> None:
        _setup_v_incidents(mem_db, load_rows)
        result = forecast(mem_db, "UNKNOWN_XYZ")
        assert isinstance(result, RiskForecast)
        assert result.plate == "UNKNOWN_XYZ"

    def test_ci_invariant_with_real_data(self, mem_db, load_rows) -> None:
        rows = [
            {"vehicle_plate": "P001", "alarm_code": "DMS_DROWSY",
             "ts": "2026-05-20T10:00:00Z", "speed_kmh": 60.0},
            {"vehicle_plate": "P001", "alarm_code": "OVERSPEED",
             "ts": "2026-05-21T14:00:00Z", "speed_kmh": 95.0},
            {"vehicle_plate": "P001", "alarm_code": "DMS_DROWSY",
             "ts": "2026-05-22T09:00:00Z", "speed_kmh": 55.0},
        ]
        _setup_v_incidents(mem_db, load_rows, rows)
        result = forecast(mem_db, "P001")
        assert len(result.trend) == 7
        for pt in result.trend:
            assert pt.ci_low <= pt.predicted_events <= pt.ci_high, (
                f"{pt.date}: ci_low={pt.ci_low} pred={pt.predicted_events} ci_high={pt.ci_high}"
            )

    def test_forecast_anomaly_and_reason_present_on_fallback(self, mem_db, load_rows) -> None:
        _setup_v_incidents(mem_db, load_rows)
        result = forecast(mem_db, "EMPTY001")
        # Пустая история < 8 дней → fallback: anomaly=False, reason="недостаточно истории"
        assert result.anomaly is False
        assert result.anomaly_reason == "недостаточно истории"

    def test_forecast_recommendations_list_type(self, mem_db, load_rows) -> None:
        _setup_v_incidents(mem_db, load_rows)
        result = forecast(mem_db, "EMPTY001")
        assert isinstance(result.recommendations, list)
