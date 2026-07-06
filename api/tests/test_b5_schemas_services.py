"""Tests for b5 — domain schemas, repositories, services (CONTRACT §2/§3.1/§7.5).

Pure schema tests run always. Service/repository tests need the built DuckDB
(`make db`) and skip cleanly if it is absent.
"""

from __future__ import annotations

import duckdb
import pytest

from api.core.config import settings

# ---------------------------------------------------------------------------
# DB fixture (session-scoped, read-only)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db() -> duckdb.DuckDBPyConnection:
    if not settings.db_path.exists():
        pytest.skip(f"DuckDB не собран ({settings.db_path}); запусти `make db`.")
    conn = duckdb.connect(str(settings.db_path), read_only=True)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Schema validation against the mock shape (Check §2: «форма совпадает»)
# ---------------------------------------------------------------------------

# Legacy → canon name mapping (§3.1): score→risk_score, event_source→source,
# alarm_type_label→alarm_label_ru.
_LEGACY_TO_CANON = {
    "score": "risk_score",
    "event_source": "source",
    "alarm_type_label": "alarm_label_ru",
}


def _mock_to_canon(m: dict) -> dict:
    out = dict(m)
    for legacy, canon in _LEGACY_TO_CANON.items():
        if legacy in out:
            out[canon] = out.pop(legacy)
    out.setdefault("alarm_code", out.get("alarm_type", ""))
    out.setdefault("severity", out.get("risk_level", "low"))
    return out


class TestSchemaShapeMatchesMock:
    def test_incident_summary_from_mock(self):
        from data.mock.incidents import INCIDENTS
        from api.domain.incidents import IncidentSummary

        for raw in INCIDENTS:
            c = _mock_to_canon(raw)
            summary = IncidentSummary(
                id=c["id"],
                alarm_type=c["alarm_type"],
                alarm_code=c["alarm_code"],
                alarm_label_ru=c["alarm_label_ru"],
                source=c["source"],
                severity=c["severity"],
                risk_level=c["risk_level"],
                risk_score=c["risk_score"],
                ts=c["ts"],
                vehicle_plate=c["vehicle_plate"],
                driver=c["driver"],
                vehicle_model=c["vehicle_model"],
                speed_kmh=c["speed_kmh"],
                lat=c["lat"],
                lon=c["lon"],
                address=c["address"],
                video_available=c["video_available"],
                status=c["status"],
            )
            assert summary.id == raw["id"]
            assert summary.risk_score == raw["score"]
            assert summary.source == raw["event_source"]

    def test_camera_and_telemetry_from_mock(self):
        from data.mock.incidents import INCIDENTS
        from api.domain.incidents import Camera, TelemetryPoint

        for raw in INCIDENTS:
            for cam in raw["cameras"]:
                c = Camera(**cam)
                assert c.hasVideo == cam["hasVideo"]
            for tp in raw["telemetry"]:
                t = TelemetryPoint(**tp)
                assert t.ts_offset == tp["ts_offset"]


class TestDomainEnums:
    def test_invalid_severity_rejected(self):
        from pydantic import ValidationError
        from api.domain.incidents import IncidentSummary

        with pytest.raises(ValidationError):
            IncidentSummary(
                id="x", alarm_type="t", alarm_code="t", alarm_label_ru="t",
                source="DMS", severity="extreme", risk_level="low", risk_score=1,
                ts="t", vehicle_plate="p", driver="d", vehicle_model="m",
                speed_kmh=1.0, video_available=True, status="active",
            )

    def test_report_period_alias_from(self):
        from api.domain.reports import ReportPeriod

        p = ReportPeriod(**{"from": "a", "to": "b", "days": 3})
        assert p.model_dump(by_alias=True)["from"] == "a"


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------


class TestRepositories:
    def test_list_and_get_incident(self, db):
        from api.repositories import incidents_repo as repo

        rows = repo.list_incidents(db, limit=5)
        assert len(rows) == 5
        first = repo.get_incident(db, rows[0]["id"])
        assert first is not None and first["id"] == rows[0]["id"]
        assert repo.get_incident(db, "no-such-id") is None

    def test_filters(self, db):
        from api.repositories import incidents_repo as repo

        crit = repo.list_incidents(db, severity="critical")
        assert all(r["severity"] == "critical" for r in crit)
        dms = repo.list_incidents(db, source="DMS")
        assert all(r["source"] == "DMS" for r in dms)

    def test_window_and_video_path(self, db):
        from api.repositories import incidents_repo as repo

        row = repo.list_incidents(db, limit=1)[0]
        n = repo.count_alarms_in_window(db, row["vehicle_plate"], row["ts"])
        assert isinstance(n, int) and n >= 0
        # video_path returns str|None and is consistent with channel filter
        path = repo.video_path_for(db, row["id"], 5)
        assert path is None or isinstance(path, str)

    def test_list_vehicles(self, db):
        from api.repositories import vehicles_repo as repo

        vehicles = repo.list_vehicles(db)
        assert len(vehicles) > 0
        assert "unit_state_number" in vehicles[0]


# ---------------------------------------------------------------------------
# incidents_service — contract assembly (Check §3)
# ---------------------------------------------------------------------------


class TestIncidentsService:
    def test_list_summaries(self, db):
        from api.services.incidents_service import list_summaries
        from api.domain.incidents import IncidentSummary

        summaries = list_summaries(db, {})
        assert len(summaries) == 55  # w3-5: 54 видео-алярма + 1 seeded no-video
        assert all(isinstance(s, IncidentSummary) for s in summaries)

    def test_get_detail_has_all_enrichment_fields(self, db):
        from api.services.incidents_service import get_detail, list_summaries
        from api.domain.incidents import IncidentDetail

        iid = list_summaries(db, {})[0].id
        detail = get_detail(db, iid)
        assert isinstance(detail, IncidentDetail)
        # contract enrichment fields (§3.1 / b5 Check)
        assert detail.driver and detail.driver_id and detail.driver_phone
        assert detail.vehicle_model
        assert isinstance(detail.speed_limit_kmh, int)
        assert isinstance(detail.is_night, bool)
        assert isinstance(detail.continuous_driving_min, int)
        assert isinstance(detail.events_last_7d, int)
        assert 0 <= detail.risk_score <= 100
        assert 0 <= detail.confidence <= 100
        assert detail.status in ("active", "in_progress", "validated", "closed")
        assert detail.evidence_summary
        assert len(detail.cameras) == 3
        assert detail.driver_region and detail.driver_department
        assert 0 <= detail.driver_safety_score <= 100

    def test_get_detail_driver_fields_match_reference(self, db):
        """region/department/safety_score — из driver_reference (§7.1), не фабрикуются.

        Единый источник с отчётом водителя (§7): одно ТС не должно показывать разные
        регион/отдел/safety_score на карточке инцидента и в отчёте.
        """
        from api.services.incidents_service import get_detail, list_summaries

        detail = get_detail(db, list_summaries(db, {})[0].id)
        ref = db.execute(
            'SELECT "region", "department", "safety_score" '
            'FROM "driver_reference" WHERE "vehicle_plate"=?',
            [detail.vehicle_plate],
        ).fetchone()
        assert ref is not None, "ТС инцидента должно быть в driver_reference"
        assert detail.driver_region == ref[0]
        assert detail.driver_department == ref[1]
        assert detail.driver_safety_score == max(0, min(100, int(ref[2])))

    def test_get_detail_unknown_returns_none(self, db):
        from api.services.incidents_service import get_detail

        assert get_detail(db, "no-such-id") is None

    def test_get_detail_is_deterministic(self, db):
        from api.services.incidents_service import get_detail, list_summaries

        iid = list_summaries(db, {})[0].id
        assert get_detail(db, iid).model_dump() == get_detail(db, iid).model_dump()

    def test_get_telemetry(self, db):
        from api.services.incidents_service import get_telemetry, list_summaries

        iid = list_summaries(db, {})[0].id
        tel = get_telemetry(db, iid)
        assert isinstance(tel, list)
        if tel:
            assert tel[0].ts_offset is not None


# ---------------------------------------------------------------------------
# actions_service — runtime status journal (§3.4)
# ---------------------------------------------------------------------------


class TestActionsService:
    def test_record_updates_status(self, db, tmp_path, monkeypatch):
        from api.core.config import settings as cfg
        from api.services import actions_service
        from api.services.incidents_service import get_detail, list_summaries
        from api.domain.entities import Action

        monkeypatch.setattr(cfg, "output_dir", tmp_path)
        actions_service.reset_overrides()

        iid = list_summaries(db, {})[0].id
        assert actions_service.status_for(iid) == "active"

        actions_service.record(Action(incident_id=iid, action="validate", comment="ok"))
        assert actions_service.status_for(iid) == "validated"
        assert get_detail(db, iid).status == "validated"

        # CSV written with header + row
        csv_path = tmp_path / "actions.csv"
        assert csv_path.exists()
        lines = csv_path.read_text(encoding="utf-8").strip().splitlines()
        assert lines[0] == "created_at,incident_id,action,comment,status"
        assert iid in lines[1]
        assert lines[1].endswith(",validated")  # status персистится в журнал
        actions_service.reset_overrides()


# ---------------------------------------------------------------------------
# reports_service — working reports (§7.5)
# ---------------------------------------------------------------------------


class TestReportsService:
    def test_driver_report(self, db):
        from api.services import reports_service
        from api.services.incidents_service import list_summaries
        from api.domain.reports import DriverReport

        plate = list_summaries(db, {})[0].vehicle_plate
        rep = reports_service.driver_report(db, plate)
        assert isinstance(rep, DriverReport)
        assert rep.vehicle_plate == plate
        assert rep.kpi.total == len(rep.violations)
        assert isinstance(rep.disciplinary_warning, bool)

    def test_fleet_report(self, db):
        from api.services import reports_service
        from api.domain.reports import FleetReport

        rep = reports_service.fleet_report(db)
        assert isinstance(rep, FleetReport)
        assert rep.vehicles_count == len(rep.by_vehicles) == len(rep.by_drivers)
        assert rep.kpi.total == 55  # w3-5: 54 видео-алярма + 1 seeded no-video

    def test_query_routes_fleet_and_driver(self, db):
        # §7.4: query теперь возвращает обёртку {"query": ReportQuery, "report": ...}.
        from api.services import reports_service
        from api.services.incidents_service import list_summaries
        from api.domain.reports import DriverReport, FleetReport, ReportQuery

        fleet = reports_service.query(db, "Сводка по парку")
        assert isinstance(fleet["query"], ReportQuery)
        assert isinstance(fleet["report"], FleetReport)

        plate = list_summaries(db, {})[0].vehicle_plate
        out = reports_service.query(db, f"Нарушения {plate} за 5 дней")
        assert isinstance(out["query"], ReportQuery)
        assert isinstance(out["report"], DriverReport)
        assert out["report"].vehicle_plate == plate
        assert out["report"].period.days == 5


# ---------------------------------------------------------------------------
# (бывший TestStubServices удалён) — домены fuel/sensors/navigation повышены из
# 501-стабов в Волне 3 (§9.1), `NotImplementedError` больше не бросают.
# ---------------------------------------------------------------------------
