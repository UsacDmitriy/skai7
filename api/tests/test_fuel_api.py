"""W3-14 · API-тесты домена fuel (CONTRACT §9.1/§9.2/§9.5 — топливная сверка ЗИС vs карты).

Happy + негатив против контракта. Клиент и `skip` при несобранной БД — общий
`conftest` (`client`/`real_db`), тот же приём, что в прочих API-тестах. Контракт
ответа валидируется прогоном JSON обратно через Pydantic-схемы (§9.2), не только
по кодам ответа. Топливо — изолированный остров (§9.0): ключ ТС — собственный
`fuel__fuel_vehicles.vehicle_id`, к инцидентам/РЭБ не линкуется.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.domain.fleet_health import FuelVehicleCard, FuelVehicleSummary

# Реальный госномер топливного домена — пример из §9.1 (для /api/fuel/{plate}).
REAL_PLATE = "А144ЕВ193"
RECON_STATUSES = {"matched", "review", "missing_sensor_event"}


@pytest.fixture
def fuel_list(client: TestClient) -> list[dict]:
    """Топливный ростер; `skip` уже сделан фикстурой `client` при несобранной БД."""
    r = client.get("/api/fuel")
    assert r.status_code == 200
    return r.json()


class TestFuelList:
    def test_list_len_10_and_schema(self, fuel_list: list[dict]) -> None:
        # §9.1: ровно 10 ТС; каждый элемент валиден по FuelVehicleSummary (§9.2).
        assert len(fuel_list) == 10
        for item in fuel_list:
            model = FuelVehicleSummary(**item)
            assert isinstance(model.volume_delta_zis_minus_card_l, float)  # headline KPI
            assert model.recon_status in RECON_STATUSES

    def test_headline_kpi_key_present(self, fuel_list: list[dict]) -> None:
        # Анти-регресс: ключ headline KPI присутствует в сыром JSON каждой строки.
        assert all("volume_delta_zis_minus_card_l" in row for row in fuel_list)


class TestFuelCard:
    def test_card_real_plate_ok(self, client: TestClient) -> None:
        # §9.1: реальный госномер → 200, FuelVehicleCard с непустыми reconciliation/events.
        r = client.get(f"/api/fuel/{REAL_PLATE}")
        assert r.status_code == 200
        card = FuelVehicleCard(**r.json())
        assert card.vehicle_id
        assert len(card.reconciliation) > 0
        assert len(card.events) > 0

    @pytest.mark.parametrize(
        "variant",
        [REAL_PLATE.lower(), f" {REAL_PLATE.lower()} ", f"{REAL_PLATE} "],
    )
    def test_card_plate_normalization(self, client: TestClient, variant: str) -> None:
        # §9.1/§9.5: нормализация (пробелы/регистр) резолвит то же ТС.
        r = client.get(f"/api/fuel/{variant}")
        assert r.status_code == 200
        assert r.json()["vehicle_id"] == REAL_PLATE

    def test_card_unknown_404(self, client: TestClient) -> None:
        # §9.5: неизвестный госномер → 404.
        assert client.get("/api/fuel/UNKNOWN999").status_code == 404
