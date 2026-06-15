"""Unit-покрытие Data Trust — кросс-сверка скоростей (b29) — §10.2/§10.5.

`speed_check_service.speed_check` сравнивает скорость события аларма ("Speed") и
ближайшей точки GPS-трека (окно ±10 с) по view `v_speed_check`. `delta_kmh` и
`agreement` (пороги ok/minor/major/no_data) считает СЕРВИС. ASSUMPTION (§10.2):
истина — GPS-трек → `truth_source` всегда `'gps_track'`.

Покрытие (Check tu-consistency), без сети:
  * пороги agreement — табличный тест сервисной функции;
  * окно ±10 с — синтетические строки прогоняются через реальный `35_v_speed_check.sql`
    в in-memory DuckDB (точка в 9 с берётся, в 11 с — игнорируется → `no_data`);
  * негативы `no_data` / неизвестный id — на синтетическом `v_speed_check`;
  * 200 / 404 / `truth_source` — эндпоинт на реальной базе (skip без сборки).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterator

import pytest

from api.services import speed_check_service as ss

# Колонки v_speed_check, которые читает сервис.
_VSC_DDL = (
    'CREATE TABLE "v_speed_check" ('
    '"id" VARCHAR, "event_speed_kmh" DOUBLE, '
    '"track_speed_kmh" DOUBLE, "max_track_speed_kmh" DOUBLE)'
)


def _synth_vsc(db, rows: list[tuple]) -> None:
    db.execute(_VSC_DDL)
    if rows:
        db.executemany(
            'INSERT INTO "v_speed_check" '
            '("id","event_speed_kmh","track_speed_kmh","max_track_speed_kmh") '
            "VALUES (?,?,?,?)",
            rows,
        )


def _build_speed_view(db) -> None:
    """Поднять `v_speed_check` из реального `35_*.sql` на синтетических источниках."""
    from api.core.config import settings

    sql = settings.project_root / "api" / "sql" / "35_v_speed_check.sql"
    if not sql.exists():
        pytest.skip("35_v_speed_check.sql ещё не влит (b29).")
    db.execute(sql.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Пороги agreement — табличный тест сервисной функции (§10.2).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "delta,expected",
    [
        (0.0, "ok"),
        (5.0, "ok"),       # граница ok ≤ 5
        (5.1, "minor"),
        (15.0, "minor"),   # граница minor ≤ 15
        (15.1, "major"),
        (None, "no_data"),  # любой источник NULL → нет дельты
    ],
)
def test_agreement_threshold_table(delta, expected) -> None:
    """`ok` ≤ 5 · `minor` ≤ 15 · `major` > 15 · `no_data` если delta None (§10.2)."""
    assert ss._agreement(delta) == expected


# ---------------------------------------------------------------------------
# Окно ±10 с — на синтетике через реальный SQL view (§10.2).
# ---------------------------------------------------------------------------


def _seed_window_sources(db) -> None:
    """Два аларма: NEAR — точка в 9 с (берётся), FAR — в 11 с (вне окна)."""
    db.execute(
        'CREATE TABLE video_events__selected_video_alarms '
        '("AlarmId" VARCHAR, "Speed" VARCHAR)'
    )
    db.execute(
        "CREATE TABLE video_events__track_points ("
        "alarm_id VARCHAR, speed_kmh DOUBLE, "
        "timestamp_utc TIMESTAMP, event_begin_utc TIMESTAMP)"
    )
    db.execute(
        "CREATE TABLE video_events__max_speed_points "
        "(alarm_id VARCHAR, speed_kmh DOUBLE)"
    )
    db.executemany(
        'INSERT INTO video_events__selected_video_alarms ("AlarmId","Speed") '
        "VALUES (?,?)",
        [("NEAR", "50"), ("FAR", "50")],
    )
    db.execute(
        """
        INSERT INTO video_events__track_points
          (alarm_id, speed_kmh, timestamp_utc, event_begin_utc)
        VALUES
          ('NEAR', 48.0, TIMESTAMP '2026-06-01 12:00:09', TIMESTAMP '2026-06-01 12:00:00'),
          ('FAR',  48.0, TIMESTAMP '2026-06-01 12:00:11', TIMESTAMP '2026-06-01 12:00:00')
        """
    )


def test_window_point_within_10s_is_taken(mem_db) -> None:
    """Точка в 9 с от `event_begin_utc` попадает в окно → `track_speed` определён."""
    _seed_window_sources(mem_db)
    _build_speed_view(mem_db)

    sc = ss.speed_check(mem_db, "NEAR")

    assert sc is not None
    assert sc.track_speed_kmh == pytest.approx(48.0)
    assert sc.delta_kmh == pytest.approx(2.0)
    assert sc.agreement == "ok"


def test_window_point_beyond_10s_is_ignored(mem_db) -> None:
    """Точка в 11 с — вне окна ±10 с → `no_data`, `delta_kmh is None` (§10.5)."""
    _seed_window_sources(mem_db)
    _build_speed_view(mem_db)

    sc = ss.speed_check(mem_db, "FAR")

    assert sc is not None
    assert sc.track_speed_kmh is None
    assert sc.delta_kmh is None
    assert sc.agreement == "no_data"


# ---------------------------------------------------------------------------
# Негативы no_data и неизвестный id — на синтетическом v_speed_check.
# ---------------------------------------------------------------------------


def test_no_data_when_event_speed_none(mem_db) -> None:
    """`event_speed_kmh is None` → `agreement='no_data'`, `delta_kmh=None`, ответ есть."""
    _synth_vsc(mem_db, [("A1", None, 50.0, 60.0)])

    sc = ss.speed_check(mem_db, "A1")

    assert sc is not None  # сервис возвращает объект (роутер отдаёт 200, не 5xx)
    assert sc.agreement == "no_data"
    assert sc.delta_kmh is None
    assert sc.truth_source == "gps_track"


def test_no_data_when_no_track_point(mem_db) -> None:
    """Нет точки трека в окне (`track_speed_kmh is None`) → `no_data`, delta None."""
    _synth_vsc(mem_db, [("A2", 50.0, None, None)])

    sc = ss.speed_check(mem_db, "A2")

    assert sc.agreement == "no_data"
    assert sc.delta_kmh is None


def test_known_alarm_classified(mem_db) -> None:
    """Оба источника есть → считается delta и agreement (мажорное расхождение)."""
    _synth_vsc(mem_db, [("A3", 90.0, 50.0, 95.0)])

    sc = ss.speed_check(mem_db, "A3")

    assert sc.delta_kmh == pytest.approx(40.0)
    assert sc.agreement == "major"
    assert sc.truth_source == "gps_track"


def test_unknown_id_returns_none(mem_db) -> None:
    """Неизвестный `id` → None (роутер поднимает 404 в t2)."""
    _synth_vsc(mem_db, [("A1", 50.0, 50.0, 60.0)])

    assert ss.speed_check(mem_db, "__missing__") is None


def test_speed_check_deterministic(mem_db) -> None:
    """Два вызова на одном источнике → идентичный `SpeedCheck` (§10.5)."""
    _synth_vsc(mem_db, [("A1", 70.0, 58.0, 80.0)])

    assert ss.speed_check(mem_db, "A1") == ss.speed_check(mem_db, "A1")


# ---------------------------------------------------------------------------
# Эндпоинт на реальной базе (skip без сборки / без SQL view).
# ---------------------------------------------------------------------------


def _sql_view_files() -> tuple[Path, Path]:
    from api.core.config import settings

    sql_dir = settings.project_root / "api" / "sql"
    return sql_dir / "34_v_consistency.sql", sql_dir / "35_v_speed_check.sql"


@pytest.fixture(scope="module")
def trust_db(tmp_path_factory) -> Iterator[object]:
    """RW-коннект к КОПИИ собранной БД с поднятым `v_speed_check` (§10)."""
    import duckdb

    from api.core.config import settings

    if not settings.db_path.exists():
        pytest.skip(f"DuckDB не собран ({settings.db_path}); запусти `make db`.")

    consistency_sql, speed_sql = _sql_view_files()
    if not consistency_sql.exists() or not speed_sql.exists():
        pytest.skip("SQL view §10 (34_/35_) ещё не влиты (b28/b29).")

    dst = tmp_path_factory.mktemp("trust_speed") / "skai.duckdb"
    shutil.copy(settings.db_path, dst)
    conn = duckdb.connect(str(dst), read_only=False)
    try:
        conn.execute(consistency_sql.read_text(encoding="utf-8"))
        conn.execute(speed_sql.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — нет исходных таблиц → не наша зона
        conn.close()
        pytest.skip(f"view §10 не строятся на этой базе: {exc}")
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def trust_client(trust_db) -> Iterator[object]:
    from fastapi.testclient import TestClient

    from api.core.duckdb_conn import get_db
    from api.main import app

    app.dependency_overrides[get_db] = lambda: trust_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


def _any_alarm_id(trust_db) -> str:
    row = trust_db.execute('SELECT "id" FROM v_speed_check LIMIT 1').fetchone()
    if not row or row[0] is None:
        pytest.skip("в v_speed_check нет алармов на этой базе")
    return str(row[0])


def test_endpoint_known_alarm_200(trust_db, trust_client) -> None:
    """Известный аларм → 200; `truth_source == 'gps_track'` (§10.1/§10.2)."""
    alarm_id = _any_alarm_id(trust_db)

    resp = trust_client.get(f"/api/incidents/{alarm_id}/speed-check")

    assert resp.status_code == 200
    assert resp.json()["truth_source"] == "gps_track"


def test_endpoint_unknown_id_404(trust_client) -> None:
    """Неизвестный `id` → 404 (§10.1)."""
    resp = trust_client.get("/api/incidents/__missing__/speed-check")

    assert resp.status_code == 404
