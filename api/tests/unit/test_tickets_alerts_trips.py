"""Unit-покрытие прикладных срезов tickets/alerts/trips (b13 + W3-1) — §7.4/§7.5.

`tickets_service`: журнал заявок из `output/actions.csv` (дефолт status="active",
правило is_overdue), диспетчерский алерт (video_window_sec=15) и видеодосье
поездки (track + timeline с has_video). CSV — во временном каталоге; alert/trip —
против собранной БД (`skip` без `make db`). Без сети и без поднятого uvicorn.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from api.domain.entities import DispatchAlert, Ticket, TripDossier
from api.services import incidents_service, tickets_service


# ---------------------------------------------------------------------------
# Хелперы статуса/просрочки (детерминированные, без БД).
# ---------------------------------------------------------------------------


class TestStatusAndOverdue:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("new", "active"),
            (None, "active"),
            ("", "active"),
            ("closed", "closed"),
            ("in_progress", "in_progress"),
        ],
    )
    def test_status_default_is_active_not_new(self, raw, expected: str) -> None:
        # Дефолт §3.1 — «active», НЕ «new»; неизвестное → «active».
        assert tickets_service._status_from_csv(raw) == expected

    def test_is_overdue_rule(self) -> None:
        past = "2020-01-01T00:00:00+00:00"
        future = "2999-01-01T00:00:00+00:00"
        # deadline<now И status∉{closed} → True.
        assert tickets_service._is_overdue(past, "active") is True
        # closed никогда не просрочена, даже с прошедшим дедлайном.
        assert tickets_service._is_overdue(past, "closed") is False
        # null/будущий дедлайн → False.
        assert tickets_service._is_overdue(None, "active") is False
        assert tickets_service._is_overdue(future, "active") is False


# ---------------------------------------------------------------------------
# list_tickets — журнал поверх output/actions.csv.
# ---------------------------------------------------------------------------


class TestListTickets:
    def test_no_csv_returns_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from api.core.config import settings

        monkeypatch.setattr(settings, "output_dir", tmp_path)
        assert tickets_service.list_tickets(None) == []

    def test_parses_status_and_overdue(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from api.core.config import settings

        monkeypatch.setattr(settings, "output_dir", tmp_path)
        csv_path = tmp_path / "actions.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["created_at", "incident_id", "action", "comment", "status", "deadline"]
            )
            # Без status/deadline → дефолт active, не просрочена.
            writer.writerow(["2026-06-01T00:00:00+00:00", "INC-A", "create_task", "c", "", ""])
            # Просроченная активная (deadline в прошлом).
            writer.writerow(
                [
                    "2026-06-01T00:00:00+00:00",
                    "INC-B",
                    "create_task",
                    "c",
                    "active",
                    "2020-01-01T00:00:00+00:00",
                ]
            )
            # Закрытая с прошедшим дедлайном → не просрочена.
            writer.writerow(
                [
                    "2026-06-01T00:00:00+00:00",
                    "INC-C",
                    "mark_reviewed",
                    "c",
                    "closed",
                    "2020-01-01T00:00:00+00:00",
                ]
            )

        tickets = tickets_service.list_tickets(None)
        assert all(isinstance(t, Ticket) for t in tickets)
        by_incident = {t.incident_id: t for t in tickets}
        assert by_incident["INC-A"].status == "active"
        assert by_incident["INC-A"].is_overdue is False
        assert by_incident["INC-B"].is_overdue is True
        assert by_incident["INC-C"].is_overdue is False


# ---------------------------------------------------------------------------
# get_alert / get_trip — против собранной БД.
# ---------------------------------------------------------------------------


class TestAlertAndTrip:
    def _anchor_id(self, db) -> str:
        return incidents_service.list_summaries(db, {})[0].id

    def test_get_alert_wraps_incident_with_window(self, real_db) -> None:
        alert = tickets_service.get_alert(real_db, self._anchor_id(real_db))
        assert isinstance(alert, DispatchAlert)
        assert alert.video_window_sec == 15
        assert alert.incident.id == self._anchor_id(real_db)

    def test_get_alert_unknown_returns_none(self, real_db) -> None:
        assert tickets_service.get_alert(real_db, "no-such-id") is None

    def test_get_trip_track_and_timeline(self, real_db) -> None:
        trip = tickets_service.get_trip(real_db, self._anchor_id(real_db))
        assert isinstance(trip, TripDossier)
        assert trip.vehicle_plate
        assert isinstance(trip.track, list)
        assert isinstance(trip.timeline, list)
        # has_video в каждой точке таймлайна — булево (§7.5).
        assert all(isinstance(e.has_video, bool) for e in trip.timeline)

    def test_get_trip_unknown_returns_none(self, real_db) -> None:
        assert tickets_service.get_trip(real_db, "no-such-id") is None
