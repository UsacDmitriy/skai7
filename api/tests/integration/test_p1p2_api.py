"""Интеграционные тесты P1/P2-ручек + стабов + OpenAPI (CONTRACT §7.4 / §7.5 / §3.4).

tickets / alerts / trips / reb / sabotage → 200 + схемы §7.5;
fuel/sensors/navigation → рабочие домены (§9, w3-6/7/8); в `/openapi.json` присутствуют теги всех роутеров.
"""

from __future__ import annotations

import csv

from fastapi.testclient import TestClient

from api.core.config import settings
from api.domain.entities import DispatchAlert, RebRecovery, Ticket, TripDossier
from api.domain.sabotage import SabotageEvent
from api.main import app


# ---------------------------------------------------------------------------
# GET /api/tickets → Ticket[] (§7.5, идея #6) — журнал поверх output/actions.csv
# ---------------------------------------------------------------------------


class TestTickets:
    def test_tickets_empty_without_csv(self, client: TestClient, tmp_path, monkeypatch):
        # Нет actions.csv → 200 + пустой список (не ошибка).
        monkeypatch.setattr(settings, "output_dir", tmp_path)
        r = client.get("/api/tickets")
        assert r.status_code == 200
        assert r.json() == []

    def test_tickets_parse_and_overdue(
        self, client: TestClient, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(settings, "output_dir", tmp_path)
        csv_path = tmp_path / "actions.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                ["created_at", "incident_id", "action", "comment", "status", "deadline"]
            )
            # Просроченная активная заявка (deadline в прошлом, status != closed).
            w.writerow(
                ["2026-01-01T00:00:00+00:00", "INC-1", "create_task", "c",
                 "active", "2020-01-01T00:00:00+00:00"]
            )
            # Закрытая с прошедшим дедлайном → is_overdue False.
            w.writerow(
                ["2026-01-02T00:00:00+00:00", "INC-2", "mark_reviewed", "c",
                 "closed", "2020-01-01T00:00:00+00:00"]
            )

        r = client.get("/api/tickets")
        assert r.status_code == 200, r.text
        tickets = [Ticket(**t) for t in r.json()]  # строгий контракт §7.5
        assert len(tickets) == 2
        by_incident = {t.incident_id: t for t in tickets}
        assert by_incident["INC-1"].is_overdue is True
        assert by_incident["INC-2"].is_overdue is False  # closed не просрочена

    def test_tickets_default_status_active(
        self, client: TestClient, tmp_path, monkeypatch
    ):
        # CSV без колонок status/deadline → дефолт «active» (НЕ «new»), is_overdue False.
        monkeypatch.setattr(settings, "output_dir", tmp_path)
        csv_path = tmp_path / "actions.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["created_at", "incident_id", "action", "comment"])
            w.writerow(["2026-01-01T00:00:00+00:00", "INC-3", "create_task", "c"])

        r = client.get("/api/tickets")
        assert r.status_code == 200, r.text
        tickets = [Ticket(**t) for t in r.json()]  # строгий контракт §7.5
        assert len(tickets) == 1
        assert tickets[0].status == "active"
        assert tickets[0].deadline is None
        assert tickets[0].is_overdue is False


# ---------------------------------------------------------------------------
# GET /api/alerts/{id} → DispatchAlert (§7.5, идея #5)
# ---------------------------------------------------------------------------


class TestAlerts:
    def test_alert_ok(self, client: TestClient, first_incident_id: str):
        r = client.get(f"/api/alerts/{first_incident_id}")
        assert r.status_code == 200, r.text
        alert = DispatchAlert(**r.json())
        assert alert.video_window_sec == 15
        assert alert.incident.id == first_incident_id

    def test_alert_404(self, client: TestClient):
        assert client.get("/api/alerts/no-such-id").status_code == 404


# ---------------------------------------------------------------------------
# GET /api/trips/{id} → TripDossier (§7.5, идея #7)
# ---------------------------------------------------------------------------


class TestTrips:
    def test_trip_ok(self, client: TestClient, first_incident_id: str):
        r = client.get(f"/api/trips/{first_incident_id}")
        assert r.status_code == 200, r.text
        trip = TripDossier(**r.json())
        assert trip.vehicle_plate
        assert isinstance(trip.track, list)
        assert isinstance(trip.timeline, list)

    def test_trip_404(self, client: TestClient):
        assert client.get("/api/trips/no-such-id").status_code == 404


# ---------------------------------------------------------------------------
# GET /api/reb/{id} → RebRecovery (§7.5, идея #8)
# ---------------------------------------------------------------------------


class TestReb:
    def test_reb_ok(self, client: TestClient, reb_id: str):
        r = client.get(f"/api/reb/{reb_id}")
        assert r.status_code == 200, r.text
        reb = RebRecovery(**r.json())
        assert reb.vehicle_plate
        assert isinstance(reb.gap_periods, list)
        assert isinstance(reb.gps_track, list)

    def test_reb_404(self, client: TestClient):
        assert client.get("/api/reb/no-such-vehicle").status_code == 404


# ---------------------------------------------------------------------------
# GET /api/sabotage → SabotageEvent[] (§7.5, идея #9)
# ---------------------------------------------------------------------------


class TestSabotage:
    def test_sabotage_list(self, client: TestClient):
        r = client.get("/api/sabotage")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        for item in data:
            SabotageEvent(**item)  # строгий контракт §7.5


# ---------------------------------------------------------------------------
# Домен fuel (§9.2) — повышен из стаба (w3-6): list → 200, неизвестный ТС → 404
# ---------------------------------------------------------------------------


class TestFuelDomain:
    def test_fuel_list_ok(self, client: TestClient):
        r = client.get("/api/fuel")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list) and data, "v_fuel — 10 ТС, список не пуст"
        # Заголовочный KPI домена + статус сверки (§9.2).
        assert "volume_delta_zis_minus_card_l" in data[0]
        assert "recon_status" in data[0]

    def test_fuel_unknown_plate_404(self, client: TestClient):
        # Неизвестный госномер → 404 (детерминированно), не 501/5xx.
        assert client.get("/api/fuel/A123BC77").status_code == 404


# ---------------------------------------------------------------------------
# OpenAPI (/docs) — присутствуют теги всех роутеров (Check)
# ---------------------------------------------------------------------------


def test_openapi_has_all_router_tags():
    """В `/openapi.json` есть теги всех роутеров (incidents/reports/vehicles/
    actions/tickets/alerts/trips/sabotage/reb). Не зависит от данных — отдельный
    клиент без skip по БД.
    """
    expected = {
        "incidents", "reports", "vehicles", "actions",
        "tickets", "alerts", "trips", "sabotage", "reb",
    }
    with TestClient(app) as c:
        spec = c.get("/openapi.json").json()
    tags = {
        tag
        for path in spec["paths"].values()
        for op in path.values()
        for tag in op.get("tags", [])
    }
    assert expected <= tags, f"отсутствуют теги: {expected - tags}"
