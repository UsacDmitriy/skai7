"""W3-14 · API-тесты хаба fleet-health (CONTRACT §9.0/§9.6 — объединение популяций).

`/api/fleet-health` = баннер покрытия (§9.0) + ростер 17 ТС объединения
(fuel ∪ sensors ∪ navigation по нормализованному госномеру). У ТС без домена
соответствующий KPI = None (фронт рендерит «—», §9.5 — не ошибка).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.domain.fleet_health import FleetHealthResponse

# §9.0: размеры ИСТОЧНИКОВ (не строк ростера) — баннер «Топливо:10 · Сенсоры:7 · …».
EXPECTED_COVERAGE = {"fuel": 10, "sensors": 7, "navigation": 5, "in_video_fleet": 2}


@pytest.fixture
def fleet_health(client: TestClient) -> dict:
    """Ответ хаба «Здоровье парка»: {coverage, rows}."""
    r = client.get("/api/fleet-health")
    assert r.status_code == 200
    return r.json()


class TestFleetHealth:
    def test_response_schema(self, fleet_health: dict) -> None:
        # §9.6: валиден по FleetHealthResponse (coverage + rows).
        FleetHealthResponse(**fleet_health)

    def test_coverage_banner(self, fleet_health: dict) -> None:
        # §9.0: точный баннер покрытия по доменам + пересечение с видеопарком.
        assert fleet_health["coverage"] == EXPECTED_COVERAGE

    def test_roster_len_17(self, fleet_health: dict) -> None:
        # §9.0: объединение disjoint-популяций = 17 ТС.
        assert len(fleet_health["rows"]) == 17

    def test_missing_domain_kpi_is_none(self, fleet_health: dict) -> None:
        # §9.5/§9.6: у ТС без домена соответствующий KPI = None («—» на фронте).
        rows = fleet_health["rows"]
        for row in rows:
            if not row["has_fuel"]:
                assert row["fuel_delta_l"] is None
            if not row["has_sensors"]:
                assert row["sensors_gap_can_gps_km"] is None
                assert row["sensors_online_status"] is None
            if not row["has_nav"]:
                assert row["nav_gap_count"] is None
                assert row["reb_link_id"] is None
        # disjoint-популяции: каждый домен реально отсутствует хотя бы у одного ТС.
        assert any(not r["has_fuel"] for r in rows)
        assert any(not r["has_sensors"] for r in rows)
        assert any(not r["has_nav"] for r in rows)

    def test_two_in_video_fleet(self, fleet_health: dict) -> None:
        # §9.0: только 2 ТС объединения пересекаются с видеопарком.
        assert sum(1 for r in fleet_health["rows"] if r["in_video_fleet"]) == 2
