"""Сервис цепочек усталости (b20).

Детектирует «цепочки» алармов усталости в скользящем окне 90 минут:
DMS_YAWNING, DMS_DROWSY, HARSH_BRAKING, HARSH_ACCEL, HARSH_CORNERING.

Алгоритм — жадные максимальные цепочки (non-overlapping):
    Сортируем события по ts (tie-break: alarm_code).
    Для каждого i расширяем правый указатель j пока ts[j+1] - ts[i] ≤ window.
    Если j > i — эмитируем цепочку events[i..j], сдвигаем i = j+1.
    Иначе i += 1.

Нет datetime.now() — вся логика детерминирована относительно ts событий.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import duckdb

from api.domain.common import Severity
from api.domain.entities import FatigueChain, FatigueEvent
from api.repositories import rows_to_dicts

FATIGUE_CODES: set[str] = {
    "DMS_YAWNING",
    "DMS_DROWSY",
    "HARSH_BRAKING",
    "HARSH_ACCEL",
    "HARSH_CORNERING",
}

_WINDOW_MIN = 90


def _severity(events: list[FatigueEvent]) -> Severity:
    """Формула severity детерминирована по длине цепочки и наличию DMS_DROWSY."""
    n = len(events)
    has_drowsy = any(e.code == "DMS_DROWSY" for e in events)
    if n >= 4 or (n >= 3 and has_drowsy):
        return "critical"
    if n == 3 or (n == 2 and has_drowsy):
        return "high"
    if n == 2:
        return "medium"
    return "low"


def _build_chains(rows: list[dict[str, Any]], window_min: int = _WINDOW_MIN) -> list[FatigueChain]:
    """Чистая функция: list[dict] → list[FatigueChain].

    rows — строки с ключами alarm_code, ts, vehicle_plate (уже отфильтрованные
    по FATIGUE_CODES). Разбита для упрощения unit-тестирования.
    """
    # Группируем по plate
    by_plate: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        plate = str(row["vehicle_plate"])
        by_plate.setdefault(plate, []).append(row)

    window = timedelta(minutes=window_min)
    chains: list[FatigueChain] = []

    for plate, plate_rows in sorted(by_plate.items()):
        # Сортировка: ts первичный ключ, alarm_code — tie-break (детерминированность)
        plate_rows.sort(key=lambda r: (str(r["ts"]), str(r["alarm_code"])))

        ts_list = [datetime.fromisoformat(str(r["ts"])) for r in plate_rows]
        n = len(ts_list)

        i = 0
        while i < n:
            j = i
            while j + 1 < n and ts_list[j + 1] - ts_list[i] <= window:
                j += 1

            if j > i:
                # Цепочка из ≥2 событий
                chain_rows = plate_rows[i : j + 1]
                events = [
                    FatigueEvent(code=str(r["alarm_code"]), ts=str(r["ts"]))
                    for r in chain_rows
                ]
                chains.append(
                    FatigueChain(
                        plate=plate,
                        trip_id=None,
                        events=events,
                        window_min=window_min,
                        severity=_severity(events),
                    )
                )
                i = j + 1
            else:
                i += 1

    return chains


def chains(
    db: duckdb.DuckDBPyConnection,
    plate: str | None = None,
    window_min: int = _WINDOW_MIN,
) -> list[FatigueChain]:
    """Возвращает цепочки усталости. Опционально фильтрует по госномеру."""
    in_list = ", ".join(f"'{c}'" for c in sorted(FATIGUE_CODES))

    if plate is not None:
        sql = (
            f'SELECT "alarm_code", "ts", "vehicle_plate" '
            f'FROM "v_incidents" '
            f'WHERE "alarm_code" IN ({in_list}) '
            f'  AND "vehicle_plate" = ? '
            f'ORDER BY "vehicle_plate", "ts"'
        )
        result = db.execute(sql, [plate])
    else:
        sql = (
            f'SELECT "alarm_code", "ts", "vehicle_plate" '
            f'FROM "v_incidents" '
            f'WHERE "alarm_code" IN ({in_list}) '
            f'ORDER BY "vehicle_plate", "ts"'
        )
        result = db.execute(sql)

    rows = rows_to_dicts(result)
    return _build_chains(rows, window_min=window_min)
