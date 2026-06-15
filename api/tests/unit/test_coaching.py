"""Unit-покрытие цикла обучения водителя (b31/b32) — §12.0–§12.4.

Две зоны ответственности:
  * **Генератор `api/etl/seed_coaching.py` (b31)** — детерминированный синтетический
    датасет из реальных алармов (§12.0/§12.1): повторный запуск → байт-идентичный CSV,
    словарь курсов, пороги `passed`/`completed_at`, реальный расчёт `repeat_within_30d`.
  * **Сервис `api/services/coaching_service.py` (b32)** — KPI/статусы из таблицы
    `training_assignments` (§12.2–12.3): статус назначения, инварианты долей ∈ [0,1],
    сортировка сводки, негативы (404 / водитель без назначений), детерминизм чтения.

Без сети и без `make db` (Check tu-coaching): генератор гонится в `tmp_path`, сервис —
на синтетических in-memory таблицах (`mem_db` + `load_rows`). SQL-идентификаторы в
двойных кавычках (§0).
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterator

import pytest

from api.etl import seed_coaching as gen

# Реальные источники генератора (§12.1) — те же файлы, что грузит ETL.
_ALARMS_CSV = gen.ALARMS_CSV
_TS_FMT = gen._TS_FMT


# ===========================================================================
# Генератор (b31) — §12.0/§12.1
# ===========================================================================


def _read_alarms() -> list[dict]:
    with open(_ALARMS_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.fixture
def generated_rows(tmp_path: Path) -> list[dict]:
    """Сгенерированный `training_assignments.csv` (в tmp) → list[dict]."""
    out = tmp_path / "training_assignments.csv"
    gen.seed(out)
    with out.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_generator_byte_identical_on_rerun(tmp_path: Path) -> None:
    """Повторная генерация → байт-идентичный CSV (§12.0: crc32, без random/now)."""
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    gen.seed(a)
    gen.seed(b)

    assert a.read_bytes() == b.read_bytes()


def test_generator_row_count_matches_alarms(generated_rows: list[dict]) -> None:
    """Число строк == числу алармов источника (по одному назначению на аларм, §12.1)."""
    assert len(generated_rows) == len(_read_alarms())


def test_generator_assignment_ids_unique_and_sorted(generated_rows: list[dict]) -> None:
    """`assignment_id` уникальны и файл отсортирован по ним (детерминизм §12.0)."""
    ids = [r["assignment_id"] for r in generated_rows]

    assert len(ids) == len(set(ids)), "assignment_id должны быть уникальны"
    assert ids == sorted(ids), "строки должны быть отсортированы по assignment_id"


@pytest.mark.parametrize(
    "code,course_id",
    [
        ("DMS_DROWSY", "C-FATIGUE"),
        ("HARSH_BRAKING", "C-SMOOTH"),
        ("OVERSPEED", "C-SPEED"),
        ("CAMERA_TAMPER", "C-RULES"),
        ("__UNKNOWN__", "C-BASE"),
    ],
)
def test_course_for_code_table(code: str, course_id: str) -> None:
    """Словарь курсов по коду аларма (§12.1); неизвестный код → базовый курс."""
    assert gen._course_for(code)[0] == course_id


def test_score_threshold_passed(generated_rows: list[dict]) -> None:
    """`passed` ⟺ `test_score >= 18` (порог Оздоева, §12.1) — на всём датасете."""
    for r in generated_rows:
        passed = r["passed"] == "true"
        assert passed == (int(r["test_score"]) >= 18)


def test_completed_at_threshold(generated_rows: list[dict]) -> None:
    """`completed_at` пуст ⟺ `test_score < 10` (§12.1) — на всём датасете."""
    for r in generated_rows:
        assert (r["completed_at"] == "") == (int(r["test_score"]) < 10)


def _alarm(alarm_id: str, plate: str, type_: str, begin: datetime) -> dict:
    return {
        "AlarmId": alarm_id,
        "UnitStateNumber": plate,
        "Type": type_,
        "Begin": begin.strftime(_TS_FMT),
    }


def _repeat_flags(alarms: list[dict]) -> list[bool]:
    """`repeat_within_30d` каждой строки из `_build_rows` (raw Type, без справочников)."""
    rows = gen._build_rows(alarms, type_to_code={}, driver_index={})
    return [r["repeat_within_30d"] == "true" for r in rows]


def test_repeat_within_30d_same_type_inside_window() -> None:
    """Два аларма той же plate/Type с разницей 10 дней → оба `repeat_within_30d`=true."""
    base = datetime(2026, 5, 1)
    alarms = [
        _alarm("1", "P1", "OVERSPEED", base),
        _alarm("2", "P1", "OVERSPEED", base + timedelta(days=10)),
    ]
    assert _repeat_flags(alarms) == [True, True]


def test_repeat_within_30d_same_type_outside_window() -> None:
    """Разница 40 дней (>30) → `repeat_within_30d`=false у обоих."""
    base = datetime(2026, 5, 1)
    alarms = [
        _alarm("1", "P1", "OVERSPEED", base),
        _alarm("2", "P1", "OVERSPEED", base + timedelta(days=40)),
    ]
    assert _repeat_flags(alarms) == [False, False]


def test_repeat_within_30d_different_type_no_repeat() -> None:
    """Разные Type (даже в окне) → не повтор: ключ (plate, Type) различается."""
    base = datetime(2026, 5, 1)
    alarms = [
        _alarm("1", "P1", "OVERSPEED", base),
        _alarm("2", "P1", "HARSH_BRAKING", base + timedelta(days=5)),
    ]
    assert _repeat_flags(alarms) == [False, False]


# ===========================================================================
# Сервис (b32) — §12.2/§12.3
# ===========================================================================

from api.services import coaching_service as svc  # noqa: E402

# Синтетический справочник водителей (§7.1): plate → driver.
_DRIVERS = [
    {"vehicle_plate": "P1", "driver_id": "D-1", "driver_name": "Иванов И."},
    {"vehicle_plate": "P2", "driver_id": "D-2", "driver_name": "Петров П."},
    {"vehicle_plate": "P3", "driver_id": "D-3", "driver_name": "Сидоров С."},
]


def _assignment(
    assignment_id: str,
    plate: str,
    *,
    test_score: int,
    passed: bool,
    completed_at: Any,
    repeat: bool = False,
    assigned_at: str = "2026-05-01T10:00:00Z",
) -> dict:
    """Строка `training_assignments` (§12.1) с дефолтным happy-кейсом."""
    return {
        "assignment_id": assignment_id,
        "incident_id": assignment_id.replace("TA-", ""),
        "vehicle_plate": plate,
        "course_id": "C-SPEED",
        "course_title_ru": "Скоростной режим",
        "assigned_at": assigned_at,
        "due_at": "2026-05-04T10:00:00Z",
        "test_score": test_score,
        "passed": passed,
        "completed_at": completed_at,
        "repeat_within_30d": repeat,
    }


@pytest.fixture
def coaching_db(
    mem_db: Any, load_rows: Callable[..., None]
) -> Callable[[list[dict]], Any]:
    """Фабрика in-memory БД: грузит `driver_reference` + переданные назначения."""

    def _build(assignments: list[dict]) -> Any:
        load_rows(mem_db, "driver_reference", _DRIVERS)
        load_rows(
            mem_db,
            "training_assignments",
            assignments,
            columns=list(_assignment("TA-x", "P1", test_score=0,
                                     passed=False, completed_at=None).keys()),
        )
        return mem_db

    return _build


@pytest.mark.parametrize(
    "test_score,passed,completed_at,expected",
    [
        (19, True, "2026-05-02T10:00:00Z", "passed"),     # сдал
        (12, False, "2026-05-02T10:00:00Z", "failed"),    # завершил, не сдал
        (5, False, None, "incomplete"),                   # не завершил
    ],
)
def test_card_status_table(
    coaching_db, test_score: int, passed: bool, completed_at: Any, expected: str
) -> None:
    """Статус назначения в карточке (§12.3): passed / failed / incomplete."""
    db = coaching_db(
        [_assignment("TA-1", "P1", test_score=test_score,
                     passed=passed, completed_at=completed_at)]
    )
    card = svc.card(db, "P1")

    assert card is not None
    assert card.assignments[0].status == expected


def test_card_synthetic_literal(coaching_db) -> None:
    """Карточка несёт `synthetic == True` (§12.0: честный демо-режим)."""
    db = coaching_db(
        [_assignment("TA-1", "P1", test_score=19, passed=True,
                     completed_at="2026-05-02T10:00:00Z")]
    )
    card = svc.card(db, "P1")

    assert card is not None and card.synthetic is True


def test_kpi_in_unit_range_and_consistent(coaching_db) -> None:
    """Все KPI ∈ [0,1] и согласованы с назначениями (пересчёт в тесте, §12.3)."""
    assignments = [
        _assignment("TA-1", "P1", test_score=19, passed=True,
                    completed_at="2026-05-02T10:00:00Z", repeat=True),
        _assignment("TA-2", "P1", test_score=12, passed=False,
                    completed_at="2026-05-02T10:00:00Z", repeat=False),
        _assignment("TA-3", "P1", test_score=5, passed=False,
                    completed_at=None, repeat=True),
    ]
    db = coaching_db(assignments)
    card = svc.card(db, "P1")
    assert card is not None
    kpi = card.kpi

    for value in (kpi.completion_rate, kpi.pass_rate, kpi.repeat_violation_rate):
        assert 0.0 <= value <= 1.0

    # Пересчёт из источника: 3 назначения, 2 завершено, 1 сдан, 2 повтора.
    assert kpi.completion_rate == pytest.approx(2 / 3)
    assert kpi.pass_rate == pytest.approx(1 / 2)        # passed / завершивших
    assert kpi.repeat_violation_rate == pytest.approx(2 / 3)


def test_pass_rate_zero_when_none_completed(coaching_db) -> None:
    """0 завершивших → `pass_rate == 0.0` (не деление на ноль, §12.3)."""
    db = coaching_db(
        [_assignment("TA-1", "P1", test_score=5, passed=False, completed_at=None)]
    )
    card = svc.card(db, "P1")

    assert card is not None
    assert card.kpi.pass_rate == 0.0
    assert card.kpi.completion_rate == 0.0


def test_summary_sorted_by_repeat_rate_desc(coaching_db) -> None:
    """`summary()` отсортирован по `repeat_violation_rate` desc (§12.2)."""
    db = coaching_db(
        [
            # P1: 0 повторов из 1 → 0.0
            _assignment("TA-1", "P1", test_score=19, passed=True,
                        completed_at="2026-05-02T10:00:00Z", repeat=False),
            # P2: 1 повтор из 1 → 1.0
            _assignment("TA-2", "P2", test_score=19, passed=True,
                        completed_at="2026-05-02T10:00:00Z", repeat=True),
            # P3: 1 повтор из 2 → 0.5
            _assignment("TA-3", "P3", test_score=19, passed=True,
                        completed_at="2026-05-02T10:00:00Z", repeat=True),
            _assignment("TA-4", "P3", test_score=19, passed=True,
                        completed_at="2026-05-02T10:00:00Z", repeat=False),
        ]
    )
    rates = [s.kpi.repeat_violation_rate for s in svc.summary(db)]

    assert rates == sorted(rates, reverse=True)
    assert rates == [pytest.approx(1.0), pytest.approx(0.5), pytest.approx(0.0)]


def test_driver_without_assignments_returns_zero_kpi(coaching_db) -> None:
    """Водитель из справочника без назначений → пустой список + нулевые KPI, 200 (§12.4)."""
    db = coaching_db([_assignment("TA-1", "P1", test_score=19, passed=True,
                                  completed_at="2026-05-02T10:00:00Z")])
    card = svc.card(db, "P2")  # P2 есть в справочнике, но без назначений

    assert card is not None  # не None → роутер вернёт 200, не 404
    assert card.assignments == []
    assert card.kpi.completion_rate == 0.0
    assert card.kpi.pass_rate == 0.0
    assert card.kpi.repeat_violation_rate == 0.0


def test_card_unknown_plate_is_none(coaching_db) -> None:
    """`plate` не из `driver_reference` → `None` (роутер превратит в 404, §12.2)."""
    db = coaching_db([_assignment("TA-1", "P1", test_score=19, passed=True,
                                  completed_at="2026-05-02T10:00:00Z")])

    assert svc.card(db, "__NOPE__") is None


def test_card_deterministic(coaching_db) -> None:
    """Два вызова `card()` → равные объекты (детерминизм чтения, §12)."""
    assignments = [
        _assignment("TA-1", "P1", test_score=19, passed=True,
                    completed_at="2026-05-02T10:00:00Z", repeat=True),
        _assignment("TA-2", "P1", test_score=5, passed=False,
                    completed_at=None, repeat=False),
    ]
    db = coaching_db(assignments)

    assert svc.card(db, "P1") == svc.card(db, "P1")


def test_summary_deterministic(coaching_db) -> None:
    """Два вызова `summary()` → равные списки (детерминизм §12)."""
    db = coaching_db(
        [
            _assignment("TA-1", "P1", test_score=19, passed=True,
                        completed_at="2026-05-02T10:00:00Z", repeat=True),
            _assignment("TA-2", "P2", test_score=5, passed=False,
                        completed_at=None, repeat=False),
        ]
    )

    assert svc.summary(db) == svc.summary(db)


# ---------------------------------------------------------------------------
# API-уровень (TestClient) — 404 на неизвестный plate, 200 на пустого (§12.2).
# ---------------------------------------------------------------------------


@pytest.fixture
def coaching_client(coaching_db) -> Iterator[Any]:
    """`TestClient` с `get_db`, подменённым на синтетическую in-memory БД."""
    from fastapi.testclient import TestClient

    from api.core.duckdb_conn import get_db
    from api.main import app

    db = coaching_db(
        [_assignment("TA-1", "P1", test_score=19, passed=True,
                     completed_at="2026-05-02T10:00:00Z")]
    )
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_api_unknown_plate_404(coaching_client) -> None:
    """`GET /api/coaching/{plate}` для plate не из справочника → 404 (§12.2)."""
    resp = coaching_client.get("/api/coaching/__NOPE__")

    assert resp.status_code == 404


def test_api_driver_without_assignments_200(coaching_client) -> None:
    """`GET /api/coaching/{plate}` для водителя без назначений → 200, нулевые KPI (§12.4)."""
    resp = coaching_client.get("/api/coaching/P2")

    assert resp.status_code == 200
    body = resp.json()
    assert body["assignments"] == []
    assert body["kpi"]["completion_rate"] == 0.0
    assert body["synthetic"] is True
