"""Стаб-репозитории для доменов fuel/sensors/navigation (§3.4).

Таблицы в DuckDB уже существуют (`fuel__*`, `sensors__*`, `navigation__*`),
но домены не реализованы в P0/P1 — эндпоинты отдают 501. Функции-заглушки
держат контракт сигнатур, чтобы b6/b1x подключили их без правок репозитория.
"""

from __future__ import annotations

from typing import Any

import duckdb


def list_fuel(db: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """TODO: расхождения топлива из `fuel__fuel_vehicles`."""
    return []


def list_sensors(db: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """TODO: сенсорная диагностика из `sensors__*`."""
    return []


def list_navigation(db: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """TODO: проблемные треки навигации из `navigation__*` (реализуется b12 → /api/reb)."""
    return []
