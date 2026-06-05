"""Сервис домена sabotage (§7.2/§7.4/§7.5, идея #9).

Читает сырые строки view `v_sabotage` (b11) и обогащает каждую `driver_name`
через `driver_reference` (§7.1, b7) по `vehicle_plate`. При отсутствии записи в
справочнике — синтетическое ФИО из `enrichment.driver_for` (фолбэк §7.1).
"""

from __future__ import annotations

import duckdb

from api.core import enrichment
from api.domain.sabotage import SabotageEvent
from api.repositories import rows_to_dicts


def list_sabotage(db: duckdb.DuckDBPyConnection) -> list[SabotageEvent]:
    """GET /api/sabotage. Пустой `v_sabotage` → `[]` (не ошибка, не 404)."""
    rows = rows_to_dicts(db.execute('SELECT * FROM "v_sabotage"'))
    events: list[SabotageEvent] = []
    for row in rows:
        plate = row.get("vehicle_plate") or ""
        driver_name = enrichment.driver_for(db, plate)["driver"]
        events.append(
            SabotageEvent(
                id=row["id"],
                vehicle_plate=plate,
                ts=row.get("ts") or "",
                dms_dark=bool(row.get("dms_dark")),
                speed_kmh=float(row.get("speed_kmh") or 0.0),
                driver_name=driver_name,
                video_url=row.get("video_url"),
            )
        )
    return events
