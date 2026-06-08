"""W3-14 · API-тесты домена sensors (CONTRACT §9.1/§9.2/§9.3/§9.5 — диагностика CAN−GPS).

Ключевой анти-регресс (§9.3): ответ НЕ содержит 959k `graph_points`/`graph_status`
ни на одном уровне — динамика отдаётся 7-точечным `daily_mileage` (спарклайн), а не
графовыми таблицами. Контракт валидируется прогоном JSON через Pydantic-схемы (§9.2).
"""
from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.domain.fleet_health import SensorVehicleCard, SensorVehicleSummary

# Тяжёлые графовые ключи, которые НЕ должны утекать наружу (§9.3).
FORBIDDEN_KEYS = ("graph_points", "graph_status")


def _has_key_deep(obj: Any, key: str) -> bool:
    """Рекурсивный поиск ключа `key` на любом уровне dict/list (для анти-регресса)."""
    if isinstance(obj, dict):
        return key in obj or any(_has_key_deep(v, key) for v in obj.values())
    if isinstance(obj, list):
        return any(_has_key_deep(v, key) for v in obj)
    return False


@pytest.fixture
def sensors_list(client: TestClient) -> list[dict]:
    """Сводка сенсорной диагностики (7 ТС)."""
    r = client.get("/api/sensors")
    assert r.status_code == 200
    return r.json()


class TestSensorsList:
    def test_list_len_7_and_schema(self, sensors_list: list[dict]) -> None:
        # §9.1: ровно 7 ТС; каждый элемент валиден по SensorVehicleSummary (§9.2).
        assert len(sensors_list) == 7
        for item in sensors_list:
            SensorVehicleSummary(**item)

    def test_exactly_two_stale(self, sensors_list: list[dict]) -> None:
        # §9.5: 2 из 7 ТС с last_valid_navigation_timestamp=NULL → online_status="stale".
        stale = [s for s in sensors_list if s["online_status"] == "stale"]
        assert len(stale) == 2

    def test_no_can_gps_gap_is_none(self, sensors_list: list[dict]) -> None:
        # §9.5: у ТС без CAN−GPS разрыва distance_gap…=None («нет данных», не 0).
        assert all("distance_gap_odometer_minus_gps_km" in s for s in sensors_list)
        none_gap = [
            s for s in sensors_list if s["distance_gap_odometer_minus_gps_km"] is None
        ]
        assert len(none_gap) >= 1

    def test_list_has_no_graph_keys(self, sensors_list: list[dict]) -> None:
        # §9.3 анти-регресс: ни graph_points, ни graph_status ни на одном уровне.
        for key in FORBIDDEN_KEYS:
            assert not _has_key_deep(sensors_list, key), f"{key} утёк в /api/sensors"


class TestSensorsCard:
    def test_card_by_unit_id_ok(self, client: TestClient, sensors_list: list[dict]) -> None:
        # §9.2: карточка по public_unit_id → 200, daily_mileage ровно 7 точек.
        uid = sensors_list[0]["public_unit_id"]
        r = client.get(f"/api/sensors/{uid}")
        assert r.status_code == 200
        card = SensorVehicleCard(**r.json())
        assert len(card.daily_mileage) == 7

    def test_card_by_plate_ok(self, client: TestClient, sensors_list: list[dict]) -> None:
        # §9.1: карточка резолвится и по госномеру (нормализация в сервисе).
        with_plate = [s for s in sensors_list if s["plate"]]
        assert with_plate, "ожидаем хотя бы одно ТС с резолвнутым plate"
        r = client.get(f"/api/sensors/{with_plate[0]['plate']}")
        assert r.status_code == 200

    def test_card_has_no_graph_keys(self, client: TestClient, sensors_list: list[dict]) -> None:
        # §9.3 анти-регресс на уровне карточки ТС.
        uid = sensors_list[0]["public_unit_id"]
        card = client.get(f"/api/sensors/{uid}").json()
        for key in FORBIDDEN_KEYS:
            assert not _has_key_deep(card, key), f"{key} утёк в карточку sensors"

    def test_card_unknown_404(self, client: TestClient) -> None:
        # §9.5: неизвестный ТС → 404.
        assert client.get("/api/sensors/UNKNOWN999").status_code == 404
