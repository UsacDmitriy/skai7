"""Тесты детекции РЭБ-аномалий (reb_anomaly_service).

Юнит-тесты _score_zone: не требуют DuckDB.
Интеграционный тест detect_anomalies: требует data/skai.duckdb (пропускается без файла).
"""

from __future__ import annotations

import pytest

from api.domain.entities import AnomalyType
from api.services.reb_anomaly_service import _score_zone


def _gap_pt(plate: str, ts: str, duration: int = 400, odometer: float = 5.0) -> dict:
    return {
        "vehicle_plate": plate,
        "lat": 50.0,
        "lon": 35.0,
        "ts": ts,
        "anomaly_type": AnomalyType.gap,
        "speed_kmh": None,
        "duration_sec": duration,
        "odometer_km": odometer,
        "date": ts[:10],
        "unit_id": "test-unit",
        "period_index": 5,
    }


def _spike_pt(plate: str, ts: str, speed: float = 250.0) -> dict:
    return {
        "vehicle_plate": plate,
        "lat": 50.0,
        "lon": 35.0,
        "ts": ts,
        "anomaly_type": AnomalyType.speed_spike,
        "speed_kmh": speed,
        "duration_sec": 0,
        "odometer_km": 0.0,
        "date": ts[:10],
        "unit_id": None,
        "period_index": None,
    }


def _jump_pt(plate: str, ts: str, speed: float = 450.0) -> dict:
    return {
        "vehicle_plate": plate,
        "lat": 50.0,
        "lon": 35.0,
        "ts": ts,
        "anomaly_type": AnomalyType.coord_jump,
        "speed_kmh": speed,
        "duration_sec": 0,
        "odometer_km": 0.0,
        "date": ts[:10],
        "unit_id": None,
        "period_index": None,
    }


class TestScoreZone:
    def test_multi_vehicle_gap_gets_high_score(self) -> None:
        pts = [
            _gap_pt("А001АА", "2026-05-07T10:00:00+00:00"),
            _gap_pt("Б002ББ", "2026-05-07T10:05:00+00:00"),
        ]
        score = _score_zone(pts)
        assert score >= 40, f"Ожидали score>=40 для 2 ТС с gap, получили {score}"

    def test_single_vehicle_speed_spike_only_gets_low_score(self) -> None:
        pts = [_spike_pt("А001АА", "2026-05-07T10:00:00+00:00")]
        score = _score_zone(pts)
        assert score < 20, f"Одиночный spike без gap не должен быть РЭБ-зоной, score={score}"

    def test_coord_jump_adds_score(self) -> None:
        pts = [
            _gap_pt("А001АА", "2026-05-07T10:00:00+00:00"),
            _jump_pt("А001АА", "2026-05-07T10:01:00+00:00"),
        ]
        score_with_jump = _score_zone(pts)
        score_without = _score_zone([_gap_pt("А001АА", "2026-05-07T10:00:00+00:00")])
        assert score_with_jump > score_without

    def test_short_gap_penalized(self) -> None:
        pts = [_gap_pt("А001АА", "2026-05-07T10:00:00+00:00", duration=20, odometer=0.0)]
        score = _score_zone(pts)
        # Штраф -15 за короткий gap (<30с) + -25 за одно ТС без gap типа?
        # Нет: тип gap есть, но штраф за короткий gap применяется.
        score_long = _score_zone([_gap_pt("А001АА", "2026-05-07T10:00:00+00:00", duration=400)])
        assert score < score_long

    def test_odometer_positive_adds_score(self) -> None:
        pts_with_odo = [_gap_pt("А001АА", "2026-05-07T10:00:00+00:00", odometer=5.0)]
        pts_no_odo = [_gap_pt("А001АА", "2026-05-07T10:00:00+00:00", odometer=0.0)]
        assert _score_zone(pts_with_odo) > _score_zone(pts_no_odo)

    def test_multi_date_adds_score(self) -> None:
        pts = [
            _gap_pt("А001АА", "2026-05-06T10:00:00+00:00"),
            _gap_pt("А001АА", "2026-05-07T10:00:00+00:00"),
        ]
        score = _score_zone(pts)
        single_date = _score_zone([_gap_pt("А001АА", "2026-05-06T10:00:00+00:00")])
        assert score > single_date


@pytest.fixture
def real_db():
    """Реальная DuckDB — пропускается если файл не собран."""
    import os
    import duckdb

    db_path = "data/skai.duckdb"
    if not os.path.exists(db_path):
        pytest.skip("data/skai.duckdb не найдена — запустите make db")
    conn = duckdb.connect(db_path, read_only=True)
    yield conn
    conn.close()


class TestDetectAnomalies:
    def test_returns_list(self, real_db) -> None:
        from api.services.reb_anomaly_service import detect_anomalies
        zones = detect_anomalies(real_db)
        assert isinstance(zones, list)

    def test_zones_have_valid_schema(self, real_db) -> None:
        from api.services.reb_anomaly_service import detect_anomalies
        from api.domain.entities import RebAnomalyZone
        zones = detect_anomalies(real_db)
        for z in zones:
            assert isinstance(z, RebAnomalyZone)
            assert z.confidence >= 20
            assert z.confidence_label in ("reb", "suspicious")
            assert len(z.centroid) == 2
            assert z.radius_m > 0
            assert len(z.vehicles) >= 1

    def test_all_zones_above_noise_threshold(self, real_db) -> None:
        from api.services.reb_anomaly_service import detect_anomalies
        zones = detect_anomalies(real_db)
        for z in zones:
            assert z.confidence >= 20, f"Зона {z.zone_id} прошла с score {z.confidence} < 20"
