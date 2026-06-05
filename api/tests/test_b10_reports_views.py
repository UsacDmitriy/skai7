"""Tests for b10 — SQL-views (v_driver_report/v_fleet/v_vehicle) + reports_service.

Контракт 00-CONTRACT.md §7.2/§7.4/§7.5. Требуют собранную DuckDB (`make db`),
skip при отсутствии. Чистые unit-проверки (is_gross/disciplinary) — без БД.
"""

from __future__ import annotations

import duckdb
import pytest

from api.core.config import settings


@pytest.fixture(scope="module")
def db() -> duckdb.DuckDBPyConnection:
    if not settings.db_path.exists():
        pytest.skip(f"DuckDB не собран ({settings.db_path}); запусти `make db`.")
    conn = duckdb.connect(str(settings.db_path), read_only=True)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# SQL-views существуют и читаются (Check: «SELECT * ... LIMIT 1 без ошибок»).
# ---------------------------------------------------------------------------


class TestViews:
    @pytest.mark.parametrize("view", ["v_driver_report", "v_fleet", "v_vehicle"])
    def test_view_selectable(self, db, view):
        db.execute(f'SELECT * FROM "{view}" LIMIT 1').fetchall()

    def test_driver_report_view_consistency(self, db):
        # сумма total по ТС == числу строк v_incidents (единый источник).
        total = db.execute('SELECT sum("total") FROM "v_driver_report"').fetchone()[0]
        n = db.execute('SELECT count(*) FROM "v_incidents"').fetchone()[0]
        assert total == n

    def test_fleet_view_has_driver_reference(self, db):
        # v_fleet несёт водителя из driver_reference (§7.1).
        rows = db.execute(
            'SELECT "driver_name" FROM "v_fleet" WHERE "driver_name" IS NOT NULL'
        ).fetchall()
        assert len(rows) > 0

    def test_vehicle_view_cameras_bounded(self, db):
        # cameras_online ∈ [0,3] — основа для "N/3".
        rows = db.execute('SELECT "cameras_online" FROM "v_vehicle"').fetchall()
        assert rows and all(0 <= r[0] <= 3 for r in rows)


# ---------------------------------------------------------------------------
# reports_service — поведение (§7.5).
# ---------------------------------------------------------------------------


class TestDriverReport:
    def test_driver_from_driver_reference(self, db):
        from api.services import reports_service as rs
        from api.domain.reports import DriverReport

        plate = db.execute(
            'SELECT "vehicle_plate" FROM "driver_reference" LIMIT 1'
        ).fetchone()[0]
        ref_name = db.execute(
            'SELECT "driver_name" FROM "driver_reference" WHERE "vehicle_plate"=?',
            [plate],
        ).fetchone()[0]
        ref_safety = db.execute(
            'SELECT "safety_score" FROM "driver_reference" WHERE "vehicle_plate"=?',
            [plate],
        ).fetchone()[0]

        rep = rs.driver_report(db, plate)
        assert isinstance(rep, DriverReport)
        assert rep.driver.driver_name == ref_name
        assert rep.driver.safety_score == ref_safety
        # KPI-согласованность (§63): total == video_da + telematics; gross <= total.
        assert rep.kpi.total == rep.kpi.video_da + rep.kpi.telematics
        assert rep.kpi.gross <= rep.kpi.total
        assert rep.kpi.total == len(rep.violations)

    def test_unknown_plate_no_raise(self, db):
        from api.services import reports_service as rs

        rep = rs.driver_report(db, "X000XX00")  # нет в данных / справочнике.
        assert rep.kpi.total == 0
        assert rep.violations == []
        assert rep.driver.driver_name  # синтетика driver_for, не пусто.


class TestFleetReport:
    def test_fleet_consistency(self, db):
        from api.services import reports_service as rs

        rep = rs.fleet_report(db)
        assert rep.vehicles_count == len(rep.by_vehicles) == len(rep.by_drivers)
        # §63: суммы по by_drivers согласованы с агрегатной kpi (один источник).
        assert sum(d.total for d in rep.by_drivers) == rep.kpi.total
        assert sum(d.gross for d in rep.by_drivers) == rep.kpi.gross
        # cameras_ok формата "N/3".
        for v in rep.by_vehicles:
            assert v.cameras_ok.endswith("/3")

    def test_view_param_both_arms_filled(self, db):
        from api.services import reports_service as rs

        for view in ("drivers", "vehicles"):
            rep = rs.fleet_report(db, view=view)
            assert rep.by_drivers and rep.by_vehicles


class TestVehicleReport:
    def test_vehicle_drivers_and_cameras(self, db):
        from api.services import reports_service as rs
        from api.domain.reports import VehicleReport

        plate = db.execute(
            'SELECT "vehicle_plate" FROM "driver_trips" LIMIT 1'
        ).fetchone()[0]
        rep = rs.vehicle_report(db, plate)
        assert isinstance(rep, VehicleReport)
        assert len(rep.cameras) == 3
        assert len(rep.drivers) >= 1
        assert sum(1 for d in rep.drivers if d.role == "main") == 1

    def test_vehicle_unknown_plate_synthetic_driver(self, db):
        from api.services import reports_service as rs

        rep = rs.vehicle_report(db, "X000XX00")
        assert len(rep.cameras) == 3
        assert len(rep.drivers) == 1
        assert rep.drivers[0].role == "main"


class TestQuery:
    def test_query_driver_name_wrapper(self, db):
        # Check: query без ключа Groq → {"query": ReportQuery, "report": DriverReport}.
        from api.services import reports_service as rs
        from api.domain.reports import DriverReport, ReportQuery

        out = rs.query(db, "Нарушения Иванова за 3 дня")
        assert set(out) == {"query", "report"}
        assert isinstance(out["query"], ReportQuery)
        assert out["query"].kind == "driver"
        assert isinstance(out["report"], DriverReport)

    def test_query_fleet(self, db):
        from api.services import reports_service as rs
        from api.domain.reports import FleetReport

        out = rs.query(db, "отчёт по парку")
        assert out["query"].kind == "fleet"
        assert isinstance(out["report"], FleetReport)

    def test_query_deterministic(self, db):
        from api.services import reports_service as rs

        a = rs.query(db, "отчёт по парку за неделю по ТС")
        b = rs.query(db, "отчёт по парку за неделю по ТС")
        assert a["report"].model_dump() == b["report"].model_dump()

    def test_query_period_override(self, db):
        from api.services import reports_service as rs

        out = rs.query(db, "отчёт по парку", period_days=10)
        assert out["query"].period_days == 10
        assert out["report"].period.days == 10


# ---------------------------------------------------------------------------
# Чистые проверки правил (§7.5) — без БД.
# ---------------------------------------------------------------------------


class TestRules:
    def _summary(self, severity="low", alarm_code="DMS_DROWSY"):
        from api.domain.incidents import IncidentSummary

        return IncidentSummary(
            id="a", alarm_type="t", alarm_code=alarm_code, alarm_label_ru="l",
            source="DMS", severity=severity, risk_level=severity, risk_score=10,
            ts="2026-05-19 03:00:00+04", vehicle_plate="p", driver="d",
            vehicle_model="m", speed_kmh=0.0, video_available=True, status="active",
        )

    def test_is_gross_rule(self):
        from api.services import reports_service as rs

        assert rs.is_gross(self._summary(severity="critical"))
        assert rs.is_gross(self._summary(alarm_code="OVERSPEED"))
        assert rs.is_gross(self._summary(alarm_code="DMS_SMOKING"))
        assert not rs.is_gross(self._summary(severity="high", alarm_code="DMS_DROWSY"))

    def test_empty_driver_report_safe(self):
        # Нерезолвенное ФИО → пустой driver-отчёт, не падать (§62).
        from api.services import reports_service as rs

        rep = rs._empty_driver_report("Несуществующий", 3)
        assert rep.kpi.total == 0
        assert rep.disciplinary_warning is False  # safety=100.
        assert rep.driver.driver_name == "Несуществующий"
