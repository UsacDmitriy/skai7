"""Unit-покрытие единого рейтинга водителя (b34) — §13.2/§13.4.

`driver_score_service` смешивает риск (§2) и позитив (§13.1) в одно число 0..100:
`unified_score = clamp(round(0.6·(100−avg_risk_score) + 0.4·positive_score), 0, 100)`.
Здесь закрепляем инвариант бленда на всём лидерборде, точность компонент (float без
промежуточных округлений — урок b27), стабильность/тай-брейк лидерборда и негатив
«ТС без алармов».

Изоляция (Check tu-score, без сети/`make db`):
  * `avg_risk_score` берётся из `incidents_service.list_summaries` (§2) —
    **monkeypatch** на синтетику с известным `risk_score` (формулу §2 не пересчитываем);
  * `positive_score`/`green_zone` — РЕАЛЬНЫЙ вызов сервиса b33 на in-memory алармах
    (§13.2: «вызов, не дубль»), поэтому строка лидерборда обязана совпасть с прямым
    вызовом `positive_score_service.score`.
SQL-идентификаторы в двойных кавычках (§0).
"""

from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Any, Callable, Iterator

import pytest

from api.services import driver_score_service as svc
from api.services import incidents_service, positive_score_service

# Тот же catalog, что в tu для b33 (§1.3): code/severity для harsh/critical-веток.
_CATALOG = [
    ("OVERSPEED", "OVERSPEED", "high"),
    ("HARSH_BRAKING", "HARSH_BRAKING", "high"),
]


def _round_half_up(x: float) -> int:
    """Округление «от нуля» полушага — как jq `round` в Check §13.2 (см. сервис)."""
    return math.floor(x + 0.5)


def _seed(
    mem_db: Any,
    *,
    drivers: list[str],
    alarms: list[tuple[str, str, Any, str]],
) -> Any:
    """In-memory `driver_reference` + алармы для РЕАЛЬНОГО b33 (§13.1).

    `drivers` — plate для лидерборда (включая ТС без алармов). `alarms` —
    `(plate, Type, Speed, Begin)`. `avg_risk_score` сюда не входит — он приходит
    из monkeypatch-а `incidents_service` (см. `score_env`).
    """
    mem_db.execute(
        'CREATE TABLE "driver_reference" '
        '("vehicle_plate" VARCHAR, "driver_id" VARCHAR, "driver_name" VARCHAR)'
    )
    mem_db.executemany(
        'INSERT INTO "driver_reference" VALUES (?, ?, ?)',
        [(p, f"DRV-{i}", f"Driver {p}") for i, p in enumerate(drivers)],
    )
    mem_db.execute(
        'CREATE TABLE "alarm_type_catalog" '
        '("raw" VARCHAR, "code" VARCHAR, "severity" VARCHAR)'
    )
    mem_db.executemany(
        'INSERT INTO "alarm_type_catalog" VALUES (?, ?, ?)', _CATALOG
    )
    mem_db.execute(
        'CREATE TABLE "video_events__selected_video_alarms" '
        '("UnitStateNumber" VARCHAR, "Type" VARCHAR, '
        '"Speed" VARCHAR, "Begin" TIMESTAMP)'
    )
    if alarms:
        mem_db.executemany(
            'INSERT INTO "video_events__selected_video_alarms" '
            '("UnitStateNumber","Type","Speed","Begin") VALUES (?, ?, ?, ?)',
            alarms,
        )
    return mem_db


@pytest.fixture
def score_env(
    mem_db: Any, monkeypatch: pytest.MonkeyPatch
) -> Callable[..., Any]:
    """Фабрика среды: сидит БД и подменяет `incidents_service.list_summaries`.

    `risk_map: plate -> [risk_score, ...]` задаёт средний риск ТС из «готовых данных
    инцидентов» (§13.2), минуя пересчёт формулы §2. Отсутствие ключа → нет алармов
    → `avg_risk_score == 0.0` (§13.4). Сервис b34 зовёт сервис b33 на реальных
    алармах — поэтому их тоже сидим.
    """

    def _build(
        *,
        drivers: list[str],
        alarms: list[tuple[str, str, Any, str]],
        risk_map: dict[str, list[float]],
    ) -> Any:
        db = _seed(mem_db, drivers=drivers, alarms=alarms)

        def _fake_list_summaries(_db, filters=None):
            plate = (filters or {}).get("vehicle_plate")
            return [SimpleNamespace(risk_score=r) for r in risk_map.get(plate, [])]

        # b34 читает риск через атрибут модуля → патчим сам модуль incidents_service.
        monkeypatch.setattr(
            incidents_service, "list_summaries", _fake_list_summaries
        )
        return db

    return _build


# Базовый сценарий: 3 ТС с разным риском/позитивом + 1 без алармов (CCC).
def _base_env(score_env) -> Any:
    return score_env(
        drivers=["AAA", "BBB", "CCC"],
        alarms=[
            ("AAA", "OVERSPEED", "80", "2026-06-01 08:00:00"),       # compliant
            ("AAA", "HARSH_BRAKING", "100", "2026-06-02 08:00:00"),  # non, harsh
            ("BBB", "OVERSPEED", "70", "2026-06-03 08:00:00"),       # compliant
            # CCC — без алармов (§13.4).
        ],
        risk_map={"AAA": [20.0, 40.0], "BBB": [10.0]},  # avg: 30 / 10 / 0(CCC)
    )


# ===========================================================================
# Инвариант бленда §13.2 — на всём лидерборде.
# ===========================================================================


def test_blend_invariant_each_row(score_env) -> None:
    """`clamp(round(risk_component + positive_component), 0, 100) == unified_score`
    для каждой строки лидерборда (§13.2): итог округляется ОДИН раз, без дрейфа."""
    board = svc.leaderboard(_base_env(score_env))

    assert board  # лидерборд не пуст
    for row in board:
        expected = max(
            0, min(100, _round_half_up(row.risk_component + row.positive_component))
        )
        assert row.unified_score == expected


def test_components_exact_formula(score_env) -> None:
    """`risk_component == 0.6·(100−avg_risk_score)` и
    `positive_component == 0.4·positive_score` (1e-9, float без округлений, §13.2)."""
    board = svc.leaderboard(_base_env(score_env))

    for row in board:
        assert row.risk_component == pytest.approx(
            0.6 * (100.0 - row.avg_risk_score), abs=1e-9
        )
        assert row.positive_component == pytest.approx(
            0.4 * row.positive_score, abs=1e-9
        )


def test_known_unified_values(score_env) -> None:
    """Контроль чисел сценария: AAA=60, BBB=90, CCC=100 (ручной расчёт §13.2)."""
    board = {r.vehicle_plate: r for r in svc.leaderboard(_base_env(score_env))}

    # AAA: avg_risk 30 → risk 42; positive 45 → pos 18 → unified 60.
    assert board["AAA"].unified_score == 60
    # BBB: avg_risk 10 → risk 54; positive 90 → pos 36 → unified 90.
    assert board["BBB"].unified_score == 90
    # CCC: без алармов → risk 60 + pos 40 → unified 100.
    assert board["CCC"].unified_score == 100


# ===========================================================================
# Лидерборд — длина, сортировка, тай-брейк (§13.2/§13.4).
# ===========================================================================


def test_leaderboard_length_matches_driver_reference(score_env) -> None:
    """Длина лидерборда == числу ТС в `driver_reference` (ВСЕ ТС, §13.2)."""
    db = _base_env(score_env)
    board = svc.leaderboard(db)

    expected = db.execute(
        'SELECT COUNT(*) FROM "driver_reference"'
    ).fetchone()[0]
    assert len(board) == expected == 3


def test_leaderboard_sorted_desc(score_env) -> None:
    """Сортировка по `unified_score` desc (§13.2)."""
    board = svc.leaderboard(_base_env(score_env))
    scores = [r.unified_score for r in board]

    assert scores == sorted(scores, reverse=True)


def test_leaderboard_tie_break_by_plate_asc(score_env) -> None:
    """При равном `unified_score` — тай-брейк по `vehicle_plate` asc (§13.2/§13.4).

    Два ТС без алармов и без риска → оба `unified_score == 100`; порядок строк
    задаётся plate (VA < VB), а НЕ порядком вставки в `driver_reference` (VB, VA).
    """
    db = score_env(
        drivers=["VB", "VA"],  # вставка в обратном порядке — сортировка должна выправить
        alarms=[],
        risk_map={},  # оба без риска → avg 0.0
    )
    board = svc.leaderboard(db)

    assert [r.unified_score for r in board] == [100, 100]
    assert [r.vehicle_plate for r in board] == ["VA", "VB"]


# ===========================================================================
# Негатив «ТС без алармов» — §13.4.
# ===========================================================================


def test_vehicle_without_alarms_zero_risk_and_present(score_env) -> None:
    """ТС без алармов: `avg_risk_score == 0.0` и присутствует в лидерборде (§13.4)."""
    board = {r.vehicle_plate: r for r in svc.leaderboard(_base_env(score_env))}

    assert "CCC" in board
    assert board["CCC"].avg_risk_score == 0.0


# ===========================================================================
# Связь с b33 — строка несёт ответ сервиса позитивного скоринга (вызов, не дубль).
# ===========================================================================


def test_positive_score_matches_b33_service(score_env) -> None:
    """`positive_score`/`green_zone` строки == прямому вызову b33 (§13.2: вызов, не дубль)."""
    db = _base_env(score_env)
    board = {r.vehicle_plate: r for r in svc.leaderboard(db)}

    for plate in ("AAA", "BBB", "CCC"):
        ps = positive_score_service.score(db, plate)
        assert ps is not None
        assert board[plate].positive_score == ps.positive_score
        assert board[plate].green_zone == ps.green_zone


# ===========================================================================
# Негативы — 404 и детерминизм (§13.4).
# ===========================================================================


def test_unknown_plate_is_none(score_env) -> None:
    """`plate` не из `driver_reference` → None (роутер → 404, §13.2)."""
    db = _base_env(score_env)

    assert svc.score(db, "__NOPE__") is None


def test_leaderboard_deterministic(score_env) -> None:
    """Два вызова `leaderboard()` → идентичный порядок и значения (§13.4)."""
    db = _base_env(score_env)

    assert svc.leaderboard(db) == svc.leaderboard(db)


# ---------------------------------------------------------------------------
# API-уровень (TestClient) — лидерборд 200, неизвестный plate 404 (§13.2).
# ---------------------------------------------------------------------------


@pytest.fixture
def driver_client(score_env) -> Iterator[Any]:
    """`TestClient` с `get_db`, подменённым на синтетическую in-memory БД."""
    from fastapi.testclient import TestClient

    from api.core.duckdb_conn import get_db
    from api.main import app

    db = _base_env(score_env)
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_api_leaderboard_200(driver_client) -> None:
    """`GET /api/driver-score` → 200, длина == числу ТС, сортировка desc (§13.2)."""
    resp = driver_client.get("/api/driver-score")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 3
    scores = [r["unified_score"] for r in body]
    assert scores == sorted(scores, reverse=True)


def test_api_unknown_plate_404(driver_client) -> None:
    """`GET /api/driver-score/{plate}` для plate не из справочника → 404 (§13.2)."""
    resp = driver_client.get("/api/driver-score/__NOPE__")

    assert resp.status_code == 404
