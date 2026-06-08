"""Unit-покрытие Pydantic-схем §7.5 (b5) — валидация и отклонение нарушающих enum.

Дополняет t1/`test_b5_schemas_services` (там — форма из мока): здесь фокус на
P1/P2-сущностях §7.5 (Ticket/DispatchAlert/SabotageEvent/ReportQuery/Camera) и на
строгом отклонении значений вне Status/Source/Severity/CameraStatus. Чисто
in-process, без БД и без сети.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.domain.entities import Ticket
from api.domain.reports import ReportQuery, ViolationRow
from api.domain.incidents import Camera, IncidentSummary
from api.domain.sabotage import SabotageEvent


# ---------------------------------------------------------------------------
# Корректные объекты валидируются (happy path §7.5).
# ---------------------------------------------------------------------------


class TestValidObjects:
    def test_ticket_accepts_null_deadline_and_bool_overdue(self) -> None:
        # §7.5 / синхронно с W3-1: deadline:null допустим, is_overdue:bool.
        t = Ticket(
            id="TK-1",
            created_at="2026-06-01T00:00:00+00:00",
            incident_id="INC-1",
            action="create_task",
            comment="",
            status="active",
            deadline=None,
        )
        assert t.deadline is None
        assert t.is_overdue is False  # дефолт

        t2 = Ticket(
            id="TK-2",
            created_at="2026-06-01T00:00:00+00:00",
            incident_id="INC-2",
            action="mark_reviewed",
            comment="c",
            status="closed",
            deadline="2020-01-01T00:00:00+00:00",
            is_overdue=True,
        )
        assert t2.deadline == "2020-01-01T00:00:00+00:00"
        assert t2.is_overdue is True

    def test_sabotage_event_valid(self) -> None:
        ev = SabotageEvent(
            id="A1",
            vehicle_plate="А123ВС77",
            ts="2026-06-01T12:00:00+00:00",
            dms_dark=True,
            speed_kmh=42.0,
            driver_name="Иванов И.И.",
        )
        assert ev.video_url is None  # nullable по умолчанию

    def test_report_query_valid_enums(self) -> None:
        assert ReportQuery(kind="driver", plate="А123ВС77").period_days == 3
        assert ReportQuery(kind="fleet", view="vehicles").view == "vehicles"


# ---------------------------------------------------------------------------
# Нарушающие enum значения отвергаются → ValidationError.
# ---------------------------------------------------------------------------


class TestEnumRejection:
    def test_ticket_rejects_unknown_status(self) -> None:
        # «new» НЕ входит в §3.1 enum Status (active/in_progress/validated/closed).
        with pytest.raises(ValidationError):
            Ticket(
                id="x",
                created_at="t",
                incident_id="i",
                action="create_task",
                comment="",
                status="new",
            )

    def test_violation_row_rejects_bad_source(self) -> None:
        with pytest.raises(ValidationError):
            ViolationRow(
                id="x",
                ts="t",
                alarm_code="OVERSPEED",
                alarm_label_ru="Превышение",
                source="SATELLITE",  # вне Source
                severity="high",
                is_gross=True,
            )

    def test_violation_row_rejects_bad_severity(self) -> None:
        with pytest.raises(ValidationError):
            ViolationRow(
                id="x",
                ts="t",
                alarm_code="OVERSPEED",
                alarm_label_ru="Превышение",
                source="ADAS",
                severity="extreme",  # вне Severity
                is_gross=True,
            )

    def test_camera_rejects_bad_status(self) -> None:
        with pytest.raises(ValidationError):
            Camera(id="cam-1", label="ADAS", status="blinking", hasVideo=True)

    def test_report_query_rejects_bad_kind(self) -> None:
        with pytest.raises(ValidationError):
            ReportQuery(kind="vehicle")  # только driver|fleet

    def test_incident_summary_forbids_extra_fields(self) -> None:
        # IncidentSummary: extra="forbid" — лишнее поле ловится (анти-дрейф контракта).
        with pytest.raises(ValidationError):
            IncidentSummary(
                id="x",
                alarm_type="t",
                alarm_code="t",
                alarm_label_ru="t",
                source="DMS",
                severity="high",
                risk_level="high",
                risk_score=10,
                ts="t",
                vehicle_plate="p",
                driver="d",
                vehicle_model="m",
                speed_kmh=1.0,
                video_available=True,
                status="active",
                unexpected_field="boom",
            )
