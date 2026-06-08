"""Unit-покрытие детектора саботажа (b11) — §7.2/§7.5, идея #9.

Правило `v_sabotage` (b11): событие = (тёмный DMS **ИЛИ** CAMERA_TAMPER) И движение
(speed>0). Проверяем граничные значения, применяя **реальный** SQL вью к
синтетическим сырым таблицам в in-memory DuckDB (без `make db`). Отдельно —
маппинг сервиса в `SabotageEvent` против собранной БД (`skip` без неё).
"""

from __future__ import annotations

from api.domain.sabotage import SabotageEvent
from api.services import sabotage_service


_SABOTAGE_SQL = "api/sql/23_v_sabotage.sql"


def _build_v_sabotage(mem_db, load_rows) -> None:
    """Создать сырые таблицы и применить реальный SQL вью `v_sabotage`."""
    from api.core.config import settings

    # 5 граничных аларм: dark/visible/tamper × move/stop.
    load_rows(
        mem_db,
        "video_events__selected_video_alarms",
        [
            {
                "AlarmId": "DARK_MOVE",
                "UnitStateNumber": "PLATE1",
                "Begin": "2026-06-01T12:00:00",
                "Type": "DROWSY_RAW",
                "Speed": 0.0,
            },
            {
                "AlarmId": "DARK_STOP",
                "UnitStateNumber": "PLATE1",
                "Begin": "2026-06-01T12:10:00",
                "Type": "DROWSY_RAW",
                "Speed": 0.0,
            },
            {
                "AlarmId": "VISIBLE_MOVE",
                "UnitStateNumber": "PLATE2",
                "Begin": "2026-06-01T12:20:00",
                "Type": "PHONE_RAW",
                "Speed": 0.0,
            },
            {
                "AlarmId": "TAMPER_MOVE",
                "UnitStateNumber": "PLATE3",
                "Begin": "2026-06-01T12:30:00",
                "Type": "TAMPER_RAW",
                "Speed": 0.0,
            },
            {
                "AlarmId": "TAMPER_STOP",
                "UnitStateNumber": "PLATE3",
                "Begin": "2026-06-01T12:40:00",
                "Type": "TAMPER_RAW",
                "Speed": 0.0,
            },
        ],
    )
    load_rows(
        mem_db,
        "alarm_type_catalog",
        [
            {"raw": "DROWSY_RAW", "code": "DMS_DROWSY"},
            {"raw": "PHONE_RAW", "code": "DMS_PHONE"},
            {"raw": "TAMPER_RAW", "code": "CAMERA_TAMPER"},
        ],
    )
    # Движение задаём через track_points (max speed_kmh): только у *_MOVE.
    load_rows(
        mem_db,
        "video_events__track_points",
        [
            {"alarm_id": "DARK_MOVE", "speed_kmh": 40.0},
            {"alarm_id": "VISIBLE_MOVE", "speed_kmh": 50.0},
            {"alarm_id": "TAMPER_MOVE", "speed_kmh": 30.0},
        ],
    )
    # DMS-кадр (channel=5, downloaded) есть только у visible/tamper → у них DMS не тёмный.
    load_rows(
        mem_db,
        "video_events__video_files",
        [
            {
                "alarm_id": "VISIBLE_MOVE",
                "channel": 5,
                "download_status": "downloaded",
                "media_relative_path": "v.mp4",
            },
            {
                "alarm_id": "TAMPER_MOVE",
                "channel": 5,
                "download_status": "downloaded",
                "media_relative_path": "t.mp4",
            },
            {
                "alarm_id": "TAMPER_STOP",
                "channel": 5,
                "download_status": "downloaded",
                "media_relative_path": "ts.mp4",
            },
        ],
    )
    sql_text = (settings.project_root / _SABOTAGE_SQL).read_text(encoding="utf-8")
    mem_db.execute(sql_text)


class TestSabotageRule:
    def test_only_dark_or_tamper_while_moving(self, mem_db, load_rows) -> None:
        _build_v_sabotage(mem_db, load_rows)
        rows = mem_db.execute('SELECT "id", "dms_dark", "speed_kmh" FROM "v_sabotage"').fetchall()
        ids = {r[0] for r in rows}
        # Событие: тёмный DMS+движение (DARK_MOVE) и CAMERA_TAMPER+движение (TAMPER_MOVE).
        # НЕ событие: стоянка (DARK_STOP/TAMPER_STOP) и видимый-без-tamper (VISIBLE_MOVE).
        assert ids == {"DARK_MOVE", "TAMPER_MOVE"}

    def test_boundary_flags_and_speed(self, mem_db, load_rows) -> None:
        _build_v_sabotage(mem_db, load_rows)
        by_id = {
            r[0]: {"dms_dark": r[1], "speed_kmh": r[2]}
            for r in mem_db.execute(
                'SELECT "id", "dms_dark", "speed_kmh" FROM "v_sabotage"'
            ).fetchall()
        }
        assert by_id["DARK_MOVE"]["dms_dark"] is True
        assert by_id["TAMPER_MOVE"]["dms_dark"] is False  # видим, но CAMERA_TAMPER
        assert all(v["speed_kmh"] > 0 for v in by_id.values())


# ---------------------------------------------------------------------------
# Сервисный маппинг против собранной БД (форма §7.5).
# ---------------------------------------------------------------------------


class TestSabotageService:
    def test_list_sabotage_against_real_db(self, real_db) -> None:
        events = sabotage_service.list_sabotage(real_db)
        assert isinstance(events, list)
        for ev in events:
            assert isinstance(ev, SabotageEvent)
            assert ev.speed_kmh > 0  # инвариант правила: движение
            assert ev.driver_name  # обогащено из driver_reference/фолбэк §7.1
