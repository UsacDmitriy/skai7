"""Репозиторий домена incidents (DuckDB → dict).

Все запросы параметризованы (`?`-плейсхолдеры DuckDB) — без конкатенации
пользовательского ввода в SQL. Идентификаторы (таблицы/колонки) — в двойных кавычках.
"""

from __future__ import annotations

from typing import Any

import duckdb

from api.repositories import rows_to_dicts

# `status` НЕ материализуется в v_incidents (рантайм-поле журнала действий, §1.3) →
# фильтрация по статусу выполняется в сервисном слое, не здесь.
_SQL_FILTERABLE = ("severity", "source", "vehicle_plate")


def list_incidents(
    db: duckdb.DuckDBPyConnection,
    *,
    severity: str | None = None,
    source: str | None = None,
    vehicle_plate: str | None = None,
    limit: int = 100,
    offset: int = 0,
    **_ignored: Any,
) -> list[dict[str, Any]]:
    """`SELECT * FROM v_incidents` + WHERE по severity/source/plate + LIMIT/OFFSET.

    `status` сюда не приходит (фильтруется сервисом по рантайм-журналу).
    Доп. неизвестные фильтры игнорируются (`**_ignored`).
    """
    where: list[str] = []
    params: list[Any] = []
    for col, val in (
        ("severity", severity),
        ("source", source),
        ("vehicle_plate", vehicle_plate),
    ):
        if val is not None:
            where.append(f'"{col}" = ?')
            params.append(val)

    sql = 'SELECT * FROM "v_incidents"'
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY \"ts\" DESC LIMIT ? OFFSET ?"
    params.extend([int(limit), int(offset)])

    return rows_to_dicts(db.execute(sql, params))


def get_incident(db: duckdb.DuckDBPyConnection, incident_id: str) -> dict[str, Any] | None:
    """Одна строка v_incidents по id или None."""
    rows = rows_to_dicts(
        db.execute('SELECT * FROM "v_incidents" WHERE "id" = ?', [incident_id])
    )
    return rows[0] if rows else None


def track_points_for(
    db: duckdb.DuckDBPyConnection, incident_id: str
) -> list[dict[str, Any]]:
    """Точки трека алярма (для телеметрии), упорядочены по point_index."""
    return rows_to_dicts(
        db.execute(
            'SELECT * FROM "video_events__track_points" '
            'WHERE "alarm_id" = ? ORDER BY "point_index"',
            [incident_id],
        )
    )


def video_files_for(
    db: duckdb.DuckDBPyConnection, incident_id: str
) -> list[dict[str, Any]]:
    """Строки video_files алярма (для камер / cam_extra)."""
    return rows_to_dicts(
        db.execute(
            'SELECT * FROM "video_events__video_files" WHERE "alarm_id" = ?',
            [incident_id],
        )
    )


def count_alarms_in_window(
    db: duckdb.DuckDBPyConnection, plate: str, ts: str, days: int = 7
) -> int:
    """COUNT алярмов того же ТС за `days` до `ts` (для events_last_7d, §2).

    Окно: (ts - days, ts] по `Begin`. `Begin` — TIMESTAMP, `ts` — ISO-строка из v_incidents.
    """
    row = db.execute(
        'SELECT COUNT(*) FROM "video_events__selected_video_alarms" '
        'WHERE "UnitStateNumber" = ? '
        'AND "Begin" <= CAST(? AS TIMESTAMP) '
        'AND "Begin" > CAST(? AS TIMESTAMP) - INTERVAL (?) DAY',
        [plate, ts, ts, int(days)],
    ).fetchone()
    return int(row[0]) if row else 0


def video_path_for(
    db: duckdb.DuckDBPyConnection, incident_id: str, channel: int
) -> str | None:
    """`media_relative_path` для (алярм, канал). Скачанный файл приоритетнее.

    Для FileResponse в b6 (`GET /incidents/{id}/video/{channel}`).
    """
    row = db.execute(
        'SELECT "media_relative_path" FROM "video_events__video_files" '
        'WHERE "alarm_id" = ? AND "channel" = ? '
        'ORDER BY CASE WHEN "download_status" = \'downloaded\' THEN 0 ELSE 1 END, '
        '"media_relative_path" '
        "LIMIT 1",
        [incident_id, int(channel)],
    ).fetchone()
    if row and row[0]:
        return str(row[0])
    return None
