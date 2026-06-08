"""Unit-покрытие восстановления при РЭБ (b12) — §7.2/§7.5, идея #8.

`reb_service.get_reb` собирает `gap_periods`/`gps_track`/`video_frames` поверх
view `v_reb` (потеря GPS = period_type=3). Тестируем детерминированно на
in-memory DuckDB с **реальным** SQL вью: разрыв трека → период с началом/концом
и соседний gps_track + кадр в окне; непрерывный трек → пусто; неизвестный id → None.
"""

from __future__ import annotations

from datetime import datetime

from api.services import reb_service


_REB_SQL = "api/sql/24_v_reb.sql"


def _build_navigation(mem_db, load_rows) -> None:
    """Сырые навигационные таблицы + применённый вью `v_reb`.

    PLATE1/uid1 — три периода: видимый(1) · разрыв GPS(2, type=3) · видимый(3).
    PLATE2/uid2 — один непрерывный период (нет type=3).
    """
    from api.core.config import settings

    load_rows(
        mem_db,
        "navigation__track_periods",
        [
            {
                "vehicle_id": "PLATE1",
                "public_unit_id": "uid1",
                "date": "2026-06-01",
                "period_index": 1,
                "period_type": 1,
                "period_duration": "00:10:00",
            },
            {
                "vehicle_id": "PLATE1",
                "public_unit_id": "uid1",
                "date": "2026-06-01",
                "period_index": 2,
                "period_type": 3,
                "period_duration": "00:05:00",
            },
            {
                "vehicle_id": "PLATE1",
                "public_unit_id": "uid1",
                "date": "2026-06-01",
                "period_index": 3,
                "period_type": 1,
                "period_duration": "00:10:00",
            },
            {
                "vehicle_id": "PLATE2",
                "public_unit_id": "uid2",
                "date": "2026-06-01",
                "period_index": 1,
                "period_type": 1,
                "period_duration": "00:30:00",
            },
        ],
    )
    load_rows(
        mem_db,
        "navigation__track_points",
        [
            {
                "public_unit_id": "uid1",
                "date": "2026-06-01",
                "period_index": 1,
                "timestamp": "2026-06-01T11:50:00+00:00",
                "latitude": 55.10,
                "longitude": 37.10,
            },
            # Разрыв (period 2): две точки задают окно [12:00, 12:03].
            {
                "public_unit_id": "uid1",
                "date": "2026-06-01",
                "period_index": 2,
                "timestamp": "2026-06-01T12:00:00+00:00",
                "latitude": 55.20,
                "longitude": 37.20,
            },
            {
                "public_unit_id": "uid1",
                "date": "2026-06-01",
                "period_index": 2,
                "timestamp": "2026-06-01T12:03:00+00:00",
                "latitude": 55.25,
                "longitude": 37.25,
            },
            {
                "public_unit_id": "uid1",
                "date": "2026-06-01",
                "period_index": 3,
                "timestamp": "2026-06-01T12:10:00+00:00",
                "latitude": 55.30,
                "longitude": 37.30,
            },
            {
                "public_unit_id": "uid2",
                "date": "2026-06-01",
                "period_index": 1,
                "timestamp": "2026-06-01T09:00:00+00:00",
                "latitude": 54.00,
                "longitude": 36.00,
            },
        ],
    )
    # Видеокадры ТС: один внутри окна разрыва (попадёт в video_frames), один вне.
    load_rows(
        mem_db,
        "video_events__video_files",
        [
            {
                "unit_state_number": "PLATE1",
                "event_begin_utc": "2026-06-01T12:02:00Z",
                "channel": 1,
                "media_relative_path": "in_window.mp4",
            },
            {
                "unit_state_number": "PLATE1",
                "event_begin_utc": "2026-06-01T15:00:00Z",
                "channel": 1,
                "media_relative_path": "out_window.mp4",
            },
        ],
    )
    sql_text = (settings.project_root / _REB_SQL).read_text(encoding="utf-8")
    mem_db.execute(sql_text)


# ---------------------------------------------------------------------------
# _parse_ts — нормализация Z и устойчивость к мусору (чистая функция).
# ---------------------------------------------------------------------------


class TestParseTs:
    def test_parses_z_suffix(self) -> None:
        dt = reb_service._parse_ts("2026-06-01T12:00:00Z")
        assert isinstance(dt, datetime) and dt.tzinfo is not None

    def test_none_and_garbage(self) -> None:
        assert reb_service._parse_ts(None) is None
        assert reb_service._parse_ts("not-a-timestamp") is None


# ---------------------------------------------------------------------------
# get_reb — детекция разрывов и сборка §7.5.
# ---------------------------------------------------------------------------


class TestGetReb:
    def test_gap_track_yields_gap_period_and_neighbors(self, mem_db, load_rows) -> None:
        _build_navigation(mem_db, load_rows)
        reb = reb_service.get_reb(mem_db, "PLATE1")
        assert reb is not None
        assert reb.vehicle_plate == "PLATE1"
        # Ровно один разрыв с непустыми границами и длительностью.
        assert len(reb.gap_periods) == 1
        gap = reb.gap_periods[0]
        assert gap.start and gap.end and gap.duration_sec == 300
        # Соседние видимые периоды дают gps_track; кадр в окне — во video_frames.
        assert len(reb.gps_track) == 2
        assert [f.url for f in reb.video_frames] == ["in_window.mp4"]

    def test_continuous_track_has_no_gaps(self, mem_db, load_rows) -> None:
        _build_navigation(mem_db, load_rows)
        reb = reb_service.get_reb(mem_db, "PLATE2")
        assert reb is not None
        assert reb.vehicle_plate == "PLATE2"
        assert reb.gap_periods == []  # непрерывный трек → пусто (не 404)

    def test_unknown_id_returns_none(self, mem_db, load_rows) -> None:
        _build_navigation(mem_db, load_rows)
        assert reb_service.get_reb(mem_db, "NO-SUCH-UNIT") is None
