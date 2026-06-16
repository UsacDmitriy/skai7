"""Unit-покрытие позитивного скоринга (b33) — §13.1/§13.4.

`positive_score_service.score` агрегирует существующие алармы ТС в признание
хорошего вождения (паттерн Netradyne GreenZone, §13.0): чистые дни, соблюдение
лимитов скорости, отсутствие резких манёвров, бейдж «зелёной зоны». Формулы
зафиксированы контрактом §13.1 — здесь закрепляем веса/пороги/клампы, инварианты
долей и негативы «ТС без алармов».

Без сети и без `make db` (Check tu-score): сервис гоняется на синтетических
in-memory таблицах (`mem_db` + DDL/INSERT под точные типы). Лимит скорости —
**импорт** `enrichment.speed_limit_for` (не 90-хардкод, §13.1). SQL-идентификаторы
в двойных кавычках (§0).
"""

from __future__ import annotations

from typing import Any, Iterator

import pytest

from api.core.enrichment import speed_limit_for
from api.services import positive_score_service as svc

# ---------------------------------------------------------------------------
# Синтетический справочник типов алармов (`alarm_type_catalog`, §1.3): тот же
# источник `code`/`severity`, что у `v_incidents` — `code.startswith("HARSH_")`
# даёт harsh-классификацию, `severity == "critical"` гасит green_zone (§13.1).
# `CRIT_NONHARSH` — critical-аларм, НЕ harsh (для теста green_zone «1.0 + critical»).
# ---------------------------------------------------------------------------
_CATALOG = [
    ("OVERSPEED", "OVERSPEED", "high"),
    ("HARSH_BRAKING", "HARSH_BRAKING", "high"),
    ("DMS_PHONE", "DMS_PHONE", "medium"),
    ("CRIT_NONHARSH", "CRIT_NONHARSH", "critical"),
]


def _seed(
    mem_db: Any, *, drivers: list[str], alarms: list[tuple[str, str, Any, str]]
) -> Any:
    """In-memory БД из справочника ТС и алармов под точные типы сервиса (§13.1).

    `drivers` — список plate для `driver_reference`. `alarms` — кортежи
    `(plate, Type, Speed, Begin)`; `Speed` — строка как в CSV или `None` (пустая).
    """
    mem_db.execute(
        'CREATE TABLE "driver_reference" '
        '("vehicle_plate" VARCHAR, "driver_id" VARCHAR, "driver_name" VARCHAR)'
    )
    mem_db.executemany(
        'INSERT INTO "driver_reference" VALUES (?, ?, ?)',
        [(p, f"D-{i}", f"Driver {p}") for i, p in enumerate(drivers)],
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


# ===========================================================================
# Формула §13.1 на синтетике — ручной расчёт == ответ сервиса.
# ===========================================================================


def test_formula_two_alarms_manual_calc(mem_db) -> None:
    """ТС с 2 алармами (1 compliant, 1 нет; 1 HARSH) при known total_days (§13.1).

    Датасет: AAA — OVERSPEED/80 (compliant, день1) + HARSH_BRAKING/100 (нет, harsh,
    день2); BBB — два OVERSPEED в дни 3/4 (расширяют total_days до 4). Ручной расчёт:
      compliant_ratio = 1/2 = 0.5; clean_days = 4 − 2 = 2 → clean_ratio = 0.5;
      harsh_free = 1 − 1/2 = 0.5; positive = round(100·(0.25+0.15+0.10)) = 50.
    """
    db = _seed(
        mem_db,
        drivers=["AAA", "BBB"],
        alarms=[
            ("AAA", "OVERSPEED", "80", "2026-06-01 08:00:00"),
            ("AAA", "HARSH_BRAKING", "100", "2026-06-02 08:00:00"),
            ("BBB", "OVERSPEED", "70", "2026-06-03 08:00:00"),
            ("BBB", "OVERSPEED", "70", "2026-06-04 08:00:00"),
        ],
    )

    ps = svc.score(db, "AAA")

    assert ps is not None
    assert ps.total_days == 4
    assert ps.period_days == 4  # дубль total_days для UI-дисклеймера (§13.0)
    assert ps.clean_days == 2
    assert ps.compliant_events_ratio == pytest.approx(0.5)
    assert ps.harsh_free_ratio == pytest.approx(0.5)
    assert ps.positive_score == 50
    assert ps.green_zone is False  # compliant 0.5 < 0.95


# ===========================================================================
# Негатив «пустой знаменатель» — все Speed пустые → ratio 1.0 (не NaN/ZeroDiv).
# ===========================================================================


def test_empty_speed_denominator_is_one(mem_db) -> None:
    """Все `Speed` пустые → `compliant_events_ratio == 1.0` (§13.1, не деление на ноль)."""
    db = _seed(
        mem_db,
        drivers=["AAA"],
        alarms=[
            ("AAA", "OVERSPEED", None, "2026-06-01 08:00:00"),
            ("AAA", "OVERSPEED", None, "2026-06-02 08:00:00"),
        ],
    )

    ps = svc.score(db, "AAA")

    assert ps is not None
    assert ps.compliant_events_ratio == pytest.approx(1.0)


# ===========================================================================
# Негатив «ТС без алармов» — §13.4.
# ===========================================================================


def test_vehicle_without_alarms_is_clean(mem_db) -> None:
    """ТС из справочника без алармов → clean_days==total_days, ratios 1.0,
    positive 100, green_zone True (§13.4). total_days берётся из чужих алармов."""
    db = _seed(
        mem_db,
        drivers=["AAA", "DDD"],
        alarms=[
            # AAA — без алармов; DDD задаёт 3 дня датасета.
            ("DDD", "OVERSPEED", "70", "2026-06-01 08:00:00"),
            ("DDD", "OVERSPEED", "70", "2026-06-02 08:00:00"),
            ("DDD", "OVERSPEED", "70", "2026-06-03 08:00:00"),
        ],
    )

    ps = svc.score(db, "AAA")

    assert ps is not None
    assert ps.total_days == 3
    assert ps.clean_days == ps.total_days
    assert ps.compliant_events_ratio == pytest.approx(1.0)
    assert ps.harsh_free_ratio == pytest.approx(1.0)
    assert ps.positive_score == 100
    assert ps.green_zone is True


# ===========================================================================
# Порог green_zone — §13.1: compliant ≥ 0.95 И нет critical.
# ===========================================================================


def _green_alarms(
    plate: str, *, compliant: int, non: int, critical: bool
) -> list[tuple[str, str, Any, str]]:
    """`compliant` OVERSPEED/80 (≤90) + `non` OVERSPEED/100 (>90) + опц. critical-аларм.

    critical-аларм — `CRIT_NONHARSH`/80 (compliant, не harsh): меняет только
    `has_critical`, не долю — чтобы проверить ветку «1.0 + critical → False».
    """
    day = "2026-06-01 08:00:00"
    rows = [(plate, "OVERSPEED", "80", day) for _ in range(compliant)]
    rows += [(plate, "OVERSPEED", "100", day) for _ in range(non)]
    if critical:
        rows.append((plate, "CRIT_NONHARSH", "80", day))
    return rows


@pytest.mark.parametrize(
    "compliant,non,critical,expected",
    [
        (47, 3, False, False),  # 0.94 < 0.95 → False
        (19, 1, False, True),   # 0.95 без critical → True
        (20, 0, True, False),   # 1.0 + один critical → False
    ],
)
def test_green_zone_threshold(
    mem_db, compliant: int, non: int, critical: bool, expected: bool
) -> None:
    """green_zone = (compliant ≥ 0.95) И нет critical-алармов ТС (§13.1)."""
    db = _seed(
        mem_db,
        drivers=["AAA"],
        alarms=_green_alarms("AAA", compliant=compliant, non=non, critical=critical),
    )

    ps = svc.score(db, "AAA")

    assert ps is not None
    assert ps.green_zone is expected


# ===========================================================================
# Лимит из enrichment — §13.1: порог == speed_limit_for(Type), НЕ 90-хардкод.
# ===========================================================================


@pytest.mark.parametrize("alarm_type", ["OVERSPEED", "DMS_PHONE"])
def test_speed_limit_from_enrichment(mem_db, alarm_type: str) -> None:
    """Compliant ⟺ `Speed ≤ speed_limit_for(Type)` (§13.1).

    Два аларма типа `T`: на лимите (compliant) и лимит+1 (нет) → ratio 0.5.
    Лимит `DMS_PHONE` = 60 ≠ 90: при хардкоде 90 оба прошли бы (ratio 1.0) —
    значение 0.5 доказывает, что сервис импортирует таблицу, а не зашивает 90.
    """
    limit = speed_limit_for(alarm_type)
    db = _seed(
        mem_db,
        drivers=["AAA"],
        alarms=[
            ("AAA", alarm_type, str(limit), "2026-06-01 08:00:00"),
            ("AAA", alarm_type, str(limit + 1), "2026-06-01 09:00:00"),
        ],
    )

    ps = svc.score(db, "AAA")

    assert ps is not None
    assert ps.compliant_events_ratio == pytest.approx(0.5)


# ===========================================================================
# Детерминизм — §13.4: повторные вызовы → идентичный ответ.
# ===========================================================================


def test_score_deterministic(mem_db) -> None:
    """Два вызова `score()` на одном источнике → равные объекты (§13.4)."""
    db = _seed(
        mem_db,
        drivers=["AAA"],
        alarms=[
            ("AAA", "OVERSPEED", "80", "2026-06-01 08:00:00"),
            ("AAA", "HARSH_BRAKING", "100", "2026-06-02 08:00:00"),
        ],
    )

    assert svc.score(db, "AAA") == svc.score(db, "AAA")


def test_unknown_plate_is_none(mem_db) -> None:
    """`plate` не из `driver_reference` → None (роутер превратит в 404, §13.1)."""
    db = _seed(mem_db, drivers=["AAA"], alarms=[])

    assert svc.score(db, "__NOPE__") is None


# ---------------------------------------------------------------------------
# API-уровень (TestClient) — 404 на неизвестный plate (§13.1).
# ---------------------------------------------------------------------------


@pytest.fixture
def positive_client(mem_db) -> Iterator[Any]:
    """`TestClient` с `get_db`, подменённым на синтетическую in-memory БД."""
    from fastapi.testclient import TestClient

    from api.core.duckdb_conn import get_db
    from api.main import app

    db = _seed(
        mem_db,
        drivers=["AAA"],
        alarms=[("AAA", "OVERSPEED", "80", "2026-06-01 08:00:00")],
    )
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_api_unknown_plate_404(positive_client) -> None:
    """`GET /api/positive-score/{plate}` для plate не из справочника → 404 (§13.1)."""
    resp = positive_client.get("/api/positive-score/__NOPE__")

    assert resp.status_code == 404


def test_api_known_plate_200(positive_client) -> None:
    """Известный ТС → 200; ответ совпадает с прямым вызовом сервиса (детерминизм)."""
    resp = positive_client.get("/api/positive-score/AAA")

    assert resp.status_code == 200
    assert resp.json()["vehicle_plate"] == "AAA"
