"""Интеграционные тесты домена reports (CONTRACT §7.4 / §7.5).

driver/fleet/vehicle/query/transcribe. NLU без `GROQ_API_KEY` детерминированно
уходит в regex-fallback (Check b10); STT мокается на graceful-fallback, чтобы
тест не зависел от наличия весов faster-whisper.
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from api.domain.reports import (
    DriverReport,
    FleetReport,
    ReportQuery,
    VehicleReport,
)


# ---------------------------------------------------------------------------
# GET /api/reports/driver/{plate} → DriverReport (§7.5 В-1)
# ---------------------------------------------------------------------------


class TestDriverReport:
    def test_driver_report_schema(self, client: TestClient, driver_plate: str):
        r = client.get(f"/api/reports/driver/{driver_plate}")
        assert r.status_code == 200, r.text
        rep = DriverReport(**r.json())  # строгий контракт §7.5
        # KPI заполнены, дисциплинарный флаг — bool, нарушения несут is_gross.
        assert rep.vehicle_plate == driver_plate
        assert isinstance(rep.disciplinary_warning, bool)
        assert rep.kpi.total == len(rep.violations)
        assert all(isinstance(v.is_gross, bool) for v in rep.violations)
        # §63: KPI-согласованность.
        assert rep.kpi.total == rep.kpi.video_da + rep.kpi.telematics
        assert rep.kpi.gross <= rep.kpi.total


# ---------------------------------------------------------------------------
# GET /api/reports/fleet?view=drivers|vehicles → FleetReport (§7.5 В-2)
# ---------------------------------------------------------------------------


class TestFleetReport:
    @pytest.mark.parametrize("view", ["drivers", "vehicles"])
    def test_fleet_both_views(self, client: TestClient, view: str):
        r = client.get("/api/reports/fleet", params={"view": view})
        assert r.status_code == 200, r.text
        rep = FleetReport(**r.json())
        # Оба разреза заполнены независимо от приоритетного view.
        assert rep.by_drivers and rep.by_vehicles
        assert rep.vehicles_count == len(rep.by_vehicles) == len(rep.by_drivers)
        # §63: суммы по водителям согласованы с агрегатной KPI.
        assert sum(d.total for d in rep.by_drivers) == rep.kpi.total
        for v in rep.by_vehicles:
            assert v.cameras_ok.endswith("/3")

    def test_fleet_default_view(self, client: TestClient):
        # Без параметра view → дефолт drivers, оба массива всё равно заполнены.
        r = client.get("/api/reports/fleet")
        assert r.status_code == 200
        rep = FleetReport(**r.json())
        assert rep.by_drivers and rep.by_vehicles


# ---------------------------------------------------------------------------
# GET /api/reports/vehicle/{plate} → VehicleReport (§7.5 В-2/ТС)
# ---------------------------------------------------------------------------


class TestVehicleReport:
    def test_vehicle_report_schema(self, client: TestClient, vehicle_plate: str):
        r = client.get(f"/api/reports/vehicle/{vehicle_plate}")
        assert r.status_code == 200, r.text
        rep = VehicleReport(**r.json())
        assert rep.plate == vehicle_plate
        assert len(rep.cameras) == 3  # ADAS/DMS/СНЗ (§7.5)
        assert len(rep.drivers) >= 1
        # Ровно один основной водитель.
        assert sum(1 for d in rep.drivers if d.role == "main") == 1


# ---------------------------------------------------------------------------
# POST /api/reports/query → {query, report} (§7.4) — regex-fallback без Groq
# ---------------------------------------------------------------------------


class TestQuery:
    def test_query_driver_branch(self, client: TestClient):
        r = client.post(
            "/api/reports/query", json={"text": "Нарушения Иванова за 3 дня"}
        )
        assert r.status_code == 200, r.text
        out = r.json()
        assert set(out) == {"query", "report"}
        query = ReportQuery(**out["query"])
        assert query.kind == "driver"
        DriverReport(**out["report"])  # driver-ветка → DriverReport

    def test_query_fleet_branch(self, client: TestClient):
        r = client.post("/api/reports/query", json={"text": "отчёт по парку"})
        assert r.status_code == 200, r.text
        out = r.json()
        assert ReportQuery(**out["query"]).kind == "fleet"
        FleetReport(**out["report"])  # fleet-ветка → FleetReport

    def test_query_period_override(self, client: TestClient):
        r = client.post(
            "/api/reports/query",
            json={"text": "отчёт по парку", "period_days": 10},
        )
        assert r.status_code == 200
        out = r.json()
        assert out["query"]["period_days"] == 10
        assert out["report"]["period"]["days"] == 10


# ---------------------------------------------------------------------------
# POST /api/reports/transcribe → {text, lang, confidence} (§7.4)
# ---------------------------------------------------------------------------


class TestTranscribe:
    @pytest.fixture
    def stub_stt(self, monkeypatch):
        """Принудительный graceful-fallback STT (модель недоступна).

        Делает тест детерминированным независимо от установки faster-whisper:
        `transcribe` вернёт `{text:"", lang: lang|"ru", confidence:0.0}`.
        """
        from api.services import stt_service

        monkeypatch.setattr(stt_service, "_get_model", lambda: None)

    def test_transcribe_contract(self, client: TestClient, stub_stt):
        wav = io.BytesIO(b"RIFF\x00\x00\x00\x00WAVEfmt ")  # минимальный псевдо-WAV
        r = client.post(
            "/api/reports/transcribe",
            files={"file": ("clip.wav", wav, "audio/wav")},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert set(body) == {"text", "lang", "confidence"}
        assert isinstance(body["text"], str)
        assert isinstance(body["lang"], str) and body["lang"]
        assert isinstance(body["confidence"], (int, float))

    def test_transcribe_lang_echoed(self, client: TestClient, stub_stt):
        wav = io.BytesIO(b"RIFF\x00\x00\x00\x00WAVEfmt ")
        r = client.post(
            "/api/reports/transcribe",
            files={"file": ("clip.wav", wav, "audio/wav")},
            data={"lang": "en"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["lang"] == "en"  # явный язык фиксируется в ответе
