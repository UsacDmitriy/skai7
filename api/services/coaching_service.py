"""Coaching-сервис — KPI цикла обучения водителя (§12.2–12.4).

Агрегирует таблицу `training_assignments` (детерминированный синтетический датасет
b31, §12.1) в сводку по водителям и карточку конкретного ТС. Связь с водителем —
из `driver_reference` (§7.1): `plate` не из справочника → 404 (§12.2).

Чистый слой данных: без сети/`now()`, детерминизм чтения (Check §12). Статус
назначения и KPI вычисляются здесь (§12.3) — в таблице их нет. `synthetic: true`
проставляется в карточке литералом (честность §12.0).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import duckdb

from api.domain.coaching import (
    CoachingAssignment,
    CoachingCard,
    CoachingKpi,
    CoachingStatus,
    CoachingSummary,
)
from api.repositories import rows_to_dicts

# Колонки назначения (§12.1) — порядок не важен, читаем по имени.
_ASSIGNMENT_COLUMNS = (
    '"assignment_id", "incident_id", "vehicle_plate", "course_id", '
    '"course_title_ru", "assigned_at", "due_at", "test_score", "passed", '
    '"completed_at", "repeat_within_30d"'
)


def _format_ts(value) -> Optional[str]:
    """TIMESTAMPTZ DuckDB → ISO-8601 UTC с суффиксом `Z` (или None).

    Детерминированно: приводим к UTC независимо от зоны хранения. Пустой
    `completed_at` (NULL) → None (§12.3, status=incomplete).
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(value)


def _status(passed: bool, completed_at: Optional[str]) -> CoachingStatus:
    """Статус назначения (§12.3): passed → failed (завершён, не сдал) → incomplete."""
    if passed:
        return "passed"
    if completed_at is not None:
        return "failed"
    return "incomplete"


def _to_assignment(row: dict) -> CoachingAssignment:
    completed_at = _format_ts(row["completed_at"])
    return CoachingAssignment(
        assignment_id=row["assignment_id"],
        incident_id=str(row["incident_id"]),
        course_id=row["course_id"],
        course_title_ru=row["course_title_ru"],
        assigned_at=_format_ts(row["assigned_at"]),
        due_at=_format_ts(row["due_at"]),
        test_score=int(row["test_score"]),
        status=_status(bool(row["passed"]), completed_at),
        completed_at=completed_at,
        repeat_within_30d=bool(row["repeat_within_30d"]),
    )


def _kpi(assignments: list[CoachingAssignment]) -> CoachingKpi:
    """KPI цикла (§12.3) — все доли ∈ [0,1]; пустой список → нули.

    completion = с `completed_at`/всего; pass = passed/завершивших (0 завершивших → 0.0);
    repeat = с `repeat_within_30d`/всего.
    """
    total = len(assignments)
    if total == 0:
        return CoachingKpi(completion_rate=0.0, pass_rate=0.0, repeat_violation_rate=0.0)
    completed = [a for a in assignments if a.completed_at is not None]
    passed = sum(1 for a in assignments if a.status == "passed")
    repeats = sum(1 for a in assignments if a.repeat_within_30d)
    return CoachingKpi(
        completion_rate=len(completed) / total,
        pass_rate=(passed / len(completed)) if completed else 0.0,
        repeat_violation_rate=repeats / total,
    )


def _driver_lookup(db: duckdb.DuckDBPyConnection) -> dict[str, dict]:
    """`vehicle_plate -> {driver_id, driver_name}` из `driver_reference` (§7.1)."""
    rows = rows_to_dicts(
        db.execute(
            'SELECT "vehicle_plate", "driver_id", "driver_name" FROM "driver_reference"'
        )
    )
    return {r["vehicle_plate"]: r for r in rows}


def _assignments_by_plate(
    db: duckdb.DuckDBPyConnection, plate: Optional[str] = None
) -> dict[str, list[CoachingAssignment]]:
    """Назначения, сгруппированные по ТС; сортировка детерминирована.

    Внутри ТС — по `assigned_at`, тай-брейк `assignment_id` (детерминизм §12).
    `plate=None` — все ТС; иначе только указанный.
    """
    where = ' WHERE "vehicle_plate" = ?' if plate is not None else ""
    params = [plate] if plate is not None else []
    rows = rows_to_dicts(
        db.execute(
            f'SELECT {_ASSIGNMENT_COLUMNS} FROM "training_assignments"{where} '
            'ORDER BY "vehicle_plate", "assigned_at", "assignment_id"',
            params,
        )
    )
    grouped: dict[str, list[CoachingAssignment]] = {}
    for row in rows:
        grouped.setdefault(row["vehicle_plate"], []).append(_to_assignment(row))
    return grouped


def summary(db: duckdb.DuckDBPyConnection) -> list[CoachingSummary]:
    """Сводка по водителям (§12.2): агрегат `training_assignments` по ТС.

    `driver_id`/`driver_name` — из `driver_reference`; сортировка по
    `repeat_violation_rate` desc, тай-брейк `vehicle_plate` asc (детерминизм §12).
    """
    drivers = _driver_lookup(db)
    grouped = _assignments_by_plate(db)
    summaries: list[CoachingSummary] = []
    for plate, assignments in grouped.items():
        driver = drivers.get(plate, {})
        summaries.append(
            CoachingSummary(
                vehicle_plate=plate,
                driver_id=driver.get("driver_id", ""),
                driver_name=driver.get("driver_name", ""),
                total=len(assignments),
                kpi=_kpi(assignments),
            )
        )
    summaries.sort(key=lambda s: (-s.kpi.repeat_violation_rate, s.vehicle_plate))
    return summaries


def card(db: duckdb.DuckDBPyConnection, plate: str) -> Optional[CoachingCard]:
    """Карточка водителя (§12.2). `plate` не из `driver_reference` → None (404).

    Водитель без назначений → пустой список + нулевые KPI (200, §12.4).
    """
    driver = _driver_lookup(db).get(plate)
    if driver is None:
        return None  # роутер → 404 (§12.2)
    assignments = _assignments_by_plate(db, plate).get(plate, [])
    return CoachingCard(
        vehicle_plate=plate,
        driver_id=driver["driver_id"],
        driver_name=driver["driver_name"],
        assignments=assignments,
        kpi=_kpi(assignments),
    )
