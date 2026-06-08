"""Сервис домена sensors (§9.2/§9.3, идея — расхождение пробега CAN − GPS).

Сводка `list_sensors` собирается из view `v_sensors` (1 строка = 1 ТС, 7 шт.);
карточка `get_sensors` дочитывает per-ТС таблицы (`daily_mileage` — 7 точек,
`engine_statistics`, `fuel_level_summary`, `online_snapshot`) по `public_unit_id`.
Репозиторного слоя не требует: читает view/таблицы напрямую через `rows_to_dicts`
(b5-хелпер), сборку в доменные модели делает здесь.

959k `sensors__sensor_graph_points`/`graph_status` НЕ читаются (§9.3): динамика —
из 7-точечного `daily_mileage`, не из графовых таблиц.
"""

from __future__ import annotations

from typing import Any

import duckdb

from api.domain.fleet_health import (
    SensorDailyPoint,
    SensorEngine,
    SensorFuelLevel,
    SensorSnapshot,
    SensorVehicleCard,
    SensorVehicleSummary,
)
from api.repositories import rows_to_dicts


def _norm(value: str | None) -> str:
    """Нормализация госномера для матчинга: верхний регистр, только буквы/цифры.

    §9.0: госномера сравниваются без пробелов/регистра/разделителей —
    `«А 230 КУ/550 RUS»`, `«С725АТ159(ТМ)»` и чистый `«С725АТ159»` сводятся к
    сопоставимому ключу. `isalnum()` сохраняет кириллицу.
    """
    if not value:
        return ""
    return "".join(ch for ch in value.upper() if ch.isalnum())


def _iso(value: Any) -> str | None:
    """`datetime`/`date` → ISO-строка; `None` → `None`; прочее → `str`."""
    if value is None:
        return None
    iso = getattr(value, "isoformat", None)
    return iso() if callable(iso) else str(value)


def _to_summary(row: dict[str, Any]) -> SensorVehicleSummary:
    """Строка `v_sensors` → `SensorVehicleSummary`. NULL-числа остаются `None`."""
    return SensorVehicleSummary(
        public_unit_id=str(row["public_unit_id"]),
        vehicle_label=str(row["vehicle_label"] or ""),
        plate=row["plate"],
        gps_total_distance_km=float(row["gps_total_distance_km"]),
        distance_odometer_km=(
            float(row["distance_odometer_km"])
            if row["distance_odometer_km"] is not None
            else None
        ),
        distance_gap_odometer_minus_gps_km=(
            float(row["distance_gap_odometer_minus_gps_km"])
            if row["distance_gap_odometer_minus_gps_km"] is not None
            else None
        ),
        max_speed_kmh=float(row["max_speed_kmh"]),
        average_speed_kmh=float(row["average_speed_kmh"]),
        satellite_amount=int(row["satellite_amount"] or 0),
        online_status=row["online_status"],
        sensor_count=int(row["sensor_count"] or 0),
    )


def list_sensors(db: duckdb.DuckDBPyConnection) -> list[SensorVehicleSummary]:
    """Сводка сенсорной диагностики по всем ТС (§9.2) — 7 строк из `v_sensors`."""
    rows = rows_to_dicts(db.execute('SELECT * FROM "v_sensors"'))
    return [_to_summary(r) for r in rows]


def _resolve_unit_id(
    db: duckdb.DuckDBPyConnection, plate: str
) -> str | None:
    """`public_unit_id` по входу: точный UUID **или** нормализованный госномер.

    Матч по нормализованной форме `vehicle_id` (лейбл), `public_state_number`
    (plate из summary) и `normalized_vehicle` (чистый ключ хаба). `None` →
    роутер вернёт 404.
    """
    rows = rows_to_dicts(
        db.execute(
            'SELECT m."public_unit_id" AS uid, m."vehicle_id" AS label, '
            '       vm."public_state_number" AS plate, '
            '       vm."normalized_vehicle" AS norm '
            'FROM "sensors__mileage_and_speed" m '
            'LEFT JOIN "reference__vehicle_matches" vm '
            "  ON vm.\"public_unit_id\" = m.\"public_unit_id\" "
            "  AND vm.\"source_list\" = 'sensors_bv'"
        )
    )
    key = _norm(plate)
    for r in rows:
        if r["uid"] == plate:
            return str(r["uid"])
        if key and key in {_norm(r["label"]), _norm(r["plate"]), _norm(r["norm"])}:
            return str(r["uid"])
    return None


def get_sensors(
    db: duckdb.DuckDBPyConnection, plate: str
) -> SensorVehicleCard | None:
    """`SensorVehicleCard` (§9.2) по госномеру/UUID; `None` (→404) если не найдено.

    Динамика — 7 точек `daily_mileage` (НЕ graph_points). `engine`/`fuel_level`/
    `snapshot` = `None`, если у ТС нет соответствующей строки.
    """
    unit_id = _resolve_unit_id(db, plate)
    if unit_id is None:
        return None

    summary_rows = rows_to_dicts(
        db.execute(
            'SELECT * FROM "v_sensors" WHERE "public_unit_id" = ?', [unit_id]
        )
    )
    if not summary_rows:
        return None
    summary = _to_summary(summary_rows[0])

    # daily_mileage: спарклайн (7 точек), упорядочен по дате.
    daily = [
        SensorDailyPoint(
            date=str(_iso(r["date"]) or ""),
            distance_km=float(r["distance_km"] or 0.0),
        )
        for r in rows_to_dicts(
            db.execute(
                'SELECT "date", "distance_km" FROM "sensors__daily_mileage" '
                'WHERE "public_unit_id" = ? ORDER BY "date"',
                [unit_id],
            )
        )
    ]

    engine = None
    eng_rows = rows_to_dicts(
        db.execute(
            'SELECT "first_ignition_on", "last_ignition_off", '
            '       "ignition_duration", "idle_duration" '
            'FROM "sensors__engine_statistics" WHERE "public_unit_id" = ?',
            [unit_id],
        )
    )
    if eng_rows:
        e = eng_rows[0]
        engine = SensorEngine(
            first_ignition_on=_iso(e["first_ignition_on"]),
            last_ignition_off=_iso(e["last_ignition_off"]),
            ignition_duration=(
                str(e["ignition_duration"])
                if e["ignition_duration"] is not None
                else None
            ),
            idle_duration=(
                str(e["idle_duration"])
                if e["idle_duration"] is not None
                else None
            ),
        )

    fuel_level = None
    fl_rows = rows_to_dicts(
        db.execute(
            'SELECT "first_fuel_level", "last_fuel_level", "delta_fuel_level" '
            'FROM "sensors__fuel_level_summary" WHERE "public_unit_id" = ?',
            [unit_id],
        )
    )
    if fl_rows:
        f = fl_rows[0]
        fuel_level = SensorFuelLevel(
            first_fuel_level=_opt_float(f["first_fuel_level"]),
            last_fuel_level=_opt_float(f["last_fuel_level"]),
            delta_fuel_level=_opt_float(f["delta_fuel_level"]),
        )

    snapshot = None
    snap_rows = rows_to_dicts(
        db.execute(
            'SELECT "speed_kmh", "fuel_volume", "satellite_amount", '
            '       "timestamp_utc", "last_valid_navigation_timestamp", '
            '       "odometer_mileage", "longitude", "latitude" '
            'FROM "sensors__online_snapshot" WHERE "public_unit_id" = ?',
            [unit_id],
        )
    )
    if snap_rows:
        s = snap_rows[0]
        snapshot = SensorSnapshot(
            speed_kmh=_opt_float(s["speed_kmh"]),
            fuel_volume=_opt_float(s["fuel_volume"]),
            satellite_amount=(
                int(s["satellite_amount"])
                if s["satellite_amount"] is not None
                else None
            ),
            timestamp_utc=_iso(s["timestamp_utc"]),
            last_valid_navigation_timestamp=_iso(
                s["last_valid_navigation_timestamp"]
            ),
            odometer_mileage=_opt_float(s["odometer_mileage"]),
            longitude=_opt_float(s["longitude"]),
            latitude=_opt_float(s["latitude"]),
        )

    return SensorVehicleCard(
        **summary.model_dump(),
        daily_mileage=daily,
        engine=engine,
        fuel_level=fuel_level,
        snapshot=snapshot,
    )


def _opt_float(value: Any) -> float | None:
    """`None`-safe `float`: NULL остаётся `None` («нет данных», не 0)."""
    return float(value) if value is not None else None
