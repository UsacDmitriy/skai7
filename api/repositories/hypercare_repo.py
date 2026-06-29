"""Репозиторий Hypercare: параметризованные read-only выборки.

Источники: "v_incidents" (триггеры-события) и "video_events__video_files"
(реальные клипы). Идентификаторы — в двойных кавычках; значения — через ?.
"""
from __future__ import annotations

import duckdb


def incidents_for_codes(
    db: duckdb.DuckDBPyConnection, alarm_codes: list[str], limit: int = 50
) -> list[dict]:
    if not alarm_codes:
        return []
    placeholders = ", ".join("?" for _ in alarm_codes)
    sql = (
        'SELECT "id", "alarm_code", "alarm_label_ru", "ts", '
        '"vehicle_plate" '
        'FROM "v_incidents" '
        f'WHERE "alarm_code" IN ({placeholders}) '
        'ORDER BY "ts" DESC LIMIT ?'
    )
    cur = db.execute(sql, [*alarm_codes, limit])
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def video_clips_for_incident(
    db: duckdb.DuckDBPyConnection, incident_id: str
) -> list[dict]:
    sql = (
        'SELECT "channel", "download_status", "media_relative_path" '
        'FROM "video_events__video_files" WHERE "alarm_id" = ? '
        'ORDER BY "channel"'
    )
    cur = db.execute(sql, [incident_id])
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]
