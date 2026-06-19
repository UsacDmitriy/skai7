"""API-тест GET /api/reb/anomalies."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.domain.entities import RebAnomalyZone


class TestRebAnomaliesEndpoint:
    def test_returns_200_with_list(self, client: TestClient) -> None:
        r = client.get("/api/reb/anomalies")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_schema_valid_when_zones_present(self, client: TestClient) -> None:
        r = client.get("/api/reb/anomalies")
        assert r.status_code == 200
        for item in r.json():
            zone = RebAnomalyZone(**item)
            assert zone.confidence >= 20
            assert zone.confidence_label in ("reb", "suspicious")
            assert len(zone.centroid) == 2
            assert zone.radius_m > 0
            assert len(zone.vehicles) >= 1
            for v in zone.vehicles:
                assert v.vehicle_plate
                assert v.anomaly_type in ("gap", "speed_spike", "coord_jump")
                assert isinstance(v.possible_route, list)

    def test_endpoint_before_reb_id(self, client: TestClient) -> None:
        # Убедиться что /anomalies не перехватывается роутом /{id:path}.
        r = client.get("/api/reb/anomalies")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
