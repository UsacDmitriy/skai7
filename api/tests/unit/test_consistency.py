"""Unit-покрытие Data Trust — консистентность данных (b28) — §10.0–§10.3/§10.5.

`consistency_service.report` собирает `ConsistencyReport` (7 детерминированных
кросс-датасетных проверок) из view `v_consistency_checks`. Статусы/ratio считает
СЕРВИС (не SQL). Это НЕ AI-фича: без сети/ML, повторный вызов → идентичный ответ.

Два слоя покрытия (Check tu-consistency), оба без сети:
  * **детерминированная логика** — пороги статусов, диапазоны, инварианты сводных
    долей — на синтетическом `v_consistency_checks` в in-memory DuckDB;
  * **датасет-факты** — 7 проверок, `coordinate_sanity > 0`, эндпоинт 200 — на
    реальной `data/skai.duckdb` (view строятся из `34_*.sql`/`35_*.sql` на КОПИИ
    базы; `skip`, если артефакт не собран). При барьере x9 пайплайн строит view сам.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterator

import pytest

from api.services import consistency_service as cs

# Канонические 7 проверок (§10.3) — множество, не порядок.
CANON_CHECK_IDS = {
    "video_fleet_no_track",
    "incident_no_video",
    "terminal_duplication",
    "plate_match_coverage",
    "timestamp_monotonicity",
    "coordinate_sanity",
    "speed_disagreement",
}

_VCC_DDL = (
    'CREATE TABLE "v_consistency_checks" '
    '("check_id" VARCHAR, "affected_count" INTEGER, "total" INTEGER)'
)


def _synth_checks(db, rows: list[tuple[str, int, int]]) -> None:
    """Создать синтетический `v_consistency_checks` с заданными (check_id, aff, total)."""
    db.execute(_VCC_DDL)
    if rows:
        db.executemany(
            'INSERT INTO "v_consistency_checks" '
            '("check_id","affected_count","total") VALUES (?,?,?)',
            rows,
        )


@pytest.fixture
def no_samples(monkeypatch) -> None:
    """Отключить sample-запросы: на синтетике нет исходных таблиц (→ sample_ids=[])."""
    monkeypatch.setattr(cs, "_SAMPLE_SQL", {})


# ---------------------------------------------------------------------------
# Реальная база: строим view из SQL на КОПИИ skai.duckdb (skip без сборки).
# ---------------------------------------------------------------------------


def _sql_dir() -> Path:
    from api.core.config import settings

    return settings.project_root / "api" / "sql"


@pytest.fixture(scope="module")
def trust_db(tmp_path_factory) -> Iterator[object]:
    """RW-коннект к КОПИИ собранной БД с поднятыми view §10 (`34_*`/`35_*`)."""
    import duckdb

    from api.core.config import settings

    if not settings.db_path.exists():
        pytest.skip(f"DuckDB не собран ({settings.db_path}); запусти `make db`.")

    sql_dir = _sql_dir()
    consistency_sql = sql_dir / "34_v_consistency.sql"
    speed_sql = sql_dir / "35_v_speed_check.sql"
    if not consistency_sql.exists() or not speed_sql.exists():
        pytest.skip("SQL view §10 (34_/35_) ещё не влиты (b28/b29).")

    dst = tmp_path_factory.mktemp("trust") / "skai.duckdb"
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
    """`TestClient` с `get_db`, подменённым на `trust_db` (view §10 подняты)."""
    from fastapi.testclient import TestClient

    from api.core.duckdb_conn import get_db
    from api.main import app

    app.dependency_overrides[get_db] = lambda: trust_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Пороги статусов — табличный тест сервисной функции (§10.2).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "affected,total,expected",
    [
        (0, 10, "ok"),    # ratio 0.0
        (1, 10, "warn"),  # ratio 0.1
        (2, 10, "warn"),  # ratio 0.2 — граница: НЕ fail (fail только при > 0.2)
        (3, 10, "fail"),  # ratio 0.3
        (0, 0, "ok"),     # total=0 → ratio 0 → ok (деградация без 5xx)
    ],
)
def test_status_threshold_table(affected, total, expected) -> None:
    """`fail` при ratio > 0.2, `warn` при ratio > 0, иначе `ok` (§10.2)."""
    assert cs._status(cs._ratio(affected, total)) == expected


def test_ratio_zero_total_is_zero() -> None:
    """total=0 → ratio=0.0 без деления на ноль (§10.2)."""
    assert cs._ratio(5, 0) == 0.0


# ---------------------------------------------------------------------------
# Структура отчёта и диапазоны — на синтетике (без сети).
# ---------------------------------------------------------------------------


def test_report_seven_canonical_checks(mem_db, no_samples) -> None:
    """Отчёт всегда содержит ровно 7 канонических проверок (множество §10.3)."""
    _synth_checks(mem_db, [])  # пустой источник → все проверки дефолтятся в (0,0)

    rep = cs.report(mem_db)

    assert len(rep.checks) == 7
    assert {c.check_id for c in rep.checks} == CANON_CHECK_IDS
    assert rep.generated_at_source == "duckdb"


def test_report_bounds_synthetic(mem_db, no_samples) -> None:
    """Каждая проверка: 0 ≤ ratio ≤ 1, affected ≤ total, sample_ids ≤ 5."""
    _synth_checks(
        mem_db,
        [
            ("incident_no_video", 3, 54),
            ("coordinate_sanity", 55, 6690),
            ("timestamp_monotonicity", 29, 51),
            ("speed_disagreement", 0, 55),
        ],
    )

    rep = cs.report(mem_db)
    for c in rep.checks:
        assert 0.0 <= c.ratio <= 1.0
        assert c.affected_count <= c.total
        assert len(c.sample_ids) <= 5


def test_empty_source_all_ok(mem_db, no_samples) -> None:
    """Пустая таблица-источник → total=0, ratio=0, status='ok' (§10.5)."""
    _synth_checks(mem_db, [])

    rep = cs.report(mem_db)
    assert all(c.status == "ok" and c.ratio == 0.0 and c.total == 0 for c in rep.checks)


# ---------------------------------------------------------------------------
# Инварианты сводных долей (§10.2) — точность 1e-9 на чистых дробях.
# ---------------------------------------------------------------------------


def test_evidence_rate_invariant(mem_db, no_samples) -> None:
    """`evidence_rate == 1 − ratio(incident_no_video)` (§10.2)."""
    _synth_checks(mem_db, [("incident_no_video", 1, 10)])

    rep = cs.report(mem_db)
    inv = next(c for c in rep.checks if c.check_id == "incident_no_video")
    assert abs(rep.evidence_rate - (1.0 - inv.ratio)) < 1e-9


def test_speed_agreement_rate_invariant(mem_db, no_samples) -> None:
    """`speed_agreement_rate == 1 − ratio(speed_disagreement)` (§10.2)."""
    _synth_checks(mem_db, [("speed_disagreement", 2, 10)])

    rep = cs.report(mem_db)
    inv = next(c for c in rep.checks if c.check_id == "speed_disagreement")
    assert abs(rep.speed_agreement_rate - (1.0 - inv.ratio)) < 1e-9


def test_report_deterministic_synthetic(mem_db, no_samples) -> None:
    """Два вызова сервиса на одном источнике → равные объекты (детерминизм §10.0)."""
    _synth_checks(mem_db, [("incident_no_video", 1, 10), ("coordinate_sanity", 2, 8)])

    assert cs.report(mem_db) == cs.report(mem_db)


# ---------------------------------------------------------------------------
# Датасет-факты на реальной базе (skip без сборки / без SQL view).
# ---------------------------------------------------------------------------


def test_endpoint_200_seven_checks(trust_client) -> None:
    """`GET /api/consistency` → 200; 7 проверок; все канонические check_id (§10.1)."""
    resp = trust_client.get("/api/consistency")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["checks"]) == 7
    assert {c["check_id"] for c in body["checks"]} == CANON_CHECK_IDS
    assert body["generated_at_source"] == "duckdb"


def test_real_report_bounds(trust_db) -> None:
    """На реальных данных: ratio∈[0,1], affected≤total, sample_ids≤5 (§10.2)."""
    rep = cs.report(trust_db)

    assert len(rep.checks) == 7
    for c in rep.checks:
        assert 0.0 <= c.ratio <= 1.0
        assert c.affected_count <= c.total
        assert len(c.sample_ids) <= 5


def test_coordinate_sanity_present_in_dataset(trust_db) -> None:
    """`coordinate_sanity.affected_count > 0`: пустые координаты в alarms реально есть."""
    rep = cs.report(trust_db)
    coord = next(c for c in rep.checks if c.check_id == "coordinate_sanity")

    assert coord.affected_count > 0


def test_real_report_deterministic(trust_db) -> None:
    """Повторный вызов на реальной базе → байт-идентичный отчёт (§10.5)."""
    assert cs.report(trust_db) == cs.report(trust_db)
