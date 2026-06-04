"""Репозиторий домена vehicles (DuckDB → dict)."""

from __future__ import annotations

from typing import Any

import duckdb

from api.repositories import rows_to_dicts


def list_vehicles(db: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """Все ТС из `video_events__vehicles` (сырые метрики; обогащение — сервис)."""
    return rows_to_dicts(
        db.execute(
            'SELECT * FROM "video_events__vehicles" ORDER BY "alarm_count" DESC'
        )
    )


def get_vehicle(
    db: duckdb.DuckDBPyConnection, plate: str
) -> dict[str, Any] | None:
    """Одно ТС по госномеру (`unit_state_number`) или None."""
    rows = rows_to_dicts(
        db.execute(
            'SELECT * FROM "video_events__vehicles" '
            'WHERE "unit_state_number" = ? LIMIT 1',
            [plate],
        )
    )
    return rows[0] if rows else None
