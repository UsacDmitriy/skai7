"""
ETL: generate data/seed/driver_reference.csv and data/seed/driver_trips.csv,
then load both into data/skai.duckdb as tables "driver_reference" / "driver_trips".

Usage:
    python -m api.etl.seed_drivers
    python api/etl/seed_drivers.py
"""
from __future__ import annotations

import csv
import sys
import zlib
from pathlib import Path

# Allow `python api/etl/seed_drivers.py` entry point (no -m flag)
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import duckdb

from api.core.enrichment import (
    _DEPARTMENTS,
    _DRIVER_NAMES,
    _REGIONS,
    is_night,
    risk_score,
    speed_limit_for,
)

DB_PATH = Path("data/skai.duckdb")
SEED_DIR = Path("data/seed")
CSV_REF = SEED_DIR / "driver_reference.csv"
CSV_TRIPS = SEED_DIR / "driver_trips.csv"

_FIELDS_REF = [
    "vehicle_plate", "unit_id", "driver_id", "driver_name",
    "driver_phone", "department", "region", "safety_score",
]
_FIELDS_TRIPS = ["vehicle_plate", "driver_id", "driver_name", "role", "trips"]


def _crc(s: str) -> int:
    return zlib.crc32(s.encode()) & 0xFFFFFFFF


def _synthetic(plate: str) -> tuple[str, str, str, str, str]:
    """(driver_id, driver_name, driver_phone, department, region) — детерминированно."""
    seed = _crc(plate)
    drv_id = "DRV-" + str(seed % 9000 + 1000)
    drv_name = _DRIVER_NAMES[seed % len(_DRIVER_NAMES)]
    p1 = seed % 100000
    p2 = (seed // 100000) % 100000
    phone = "+7" + f"{p1:05d}{p2:05d}"
    dept = _DEPARTMENTS[(seed // 7) % len(_DEPARTMENTS)]
    region = _REGIONS[seed % len(_REGIONS)]
    return drv_id, drv_name, phone, dept, region


def _safety_score(conn: duckdb.DuckDBPyConnection, plate: str) -> int:
    """round(100 - avg(risk_score)) по алармам ТС; при отсутствии алармов = 100."""
    alarms = conn.execute(
        'SELECT a."Type", a."Speed", a."Begin"::VARCHAR, cat."severity" '
        'FROM "video_events__selected_video_alarms" a '
        'LEFT JOIN alarm_type_catalog cat ON cat.raw = a."Type" '
        'WHERE a."UnitStateNumber"=?',
        [plate],
    ).fetchall()

    if not alarms:
        return 100

    n = len(alarms)
    scores: list[int] = []
    for atype, speed, begin_str, severity in alarms:
        sev = severity or "low"
        spd = float(speed) if speed is not None else 0.0
        sl = speed_limit_for(atype or "")
        night = is_night(begin_str) if begin_str else False
        scores.append(risk_score(sev, spd, sl, night, n))

    avg_risk = sum(scores) / len(scores)
    return max(0, min(100, round(100 - avg_risk)))


def _build_ref(conn: duckdb.DuckDBPyConnection) -> list[dict]:
    pairs = conn.execute(
        'SELECT DISTINCT "UnitStateNumber", "UnitId" '
        'FROM "video_events__selected_video_alarms" '
        'ORDER BY "UnitStateNumber"'
    ).fetchall()

    rows: list[dict] = []
    for plate, unit_id in pairs:
        drv_id, drv_name, phone, dept, region = _synthetic(plate)
        safety = _safety_score(conn, plate)
        rows.append({
            "vehicle_plate": plate,
            "unit_id": unit_id,
            "driver_id": drv_id,
            "driver_name": drv_name,
            "driver_phone": phone,
            "department": dept,
            "region": region,
            "safety_score": safety,
        })
    return rows


def _build_trips(ref_rows: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for r in ref_rows:
        plate = r["vehicle_plate"]
        seed = _crc(plate)
        main_trips = 60 + seed % 21  # 60–80

        rows.append({
            "vehicle_plate": plate,
            "driver_id": r["driver_id"],
            "driver_name": r["driver_name"],
            "role": "main",
            "trips": main_trips,
        })

        # 0 или 1 вторичный водитель (seed % 2 == 1)
        if seed % 2 == 1:
            sec_seed = _crc(plate + "_secondary")
            sec_num = sec_seed % 9000 + 1000
            # гарантируем отличие от main
            main_num = seed % 9000 + 1000
            if sec_num == main_num:
                sec_num = (sec_num % 9000) + 1001
            sec_id = "DRV-" + str(sec_num)
            sec_name = _DRIVER_NAMES[(sec_seed + 3) % len(_DRIVER_NAMES)]
            if sec_name == r["driver_name"]:
                sec_name = _DRIVER_NAMES[(sec_seed + 7) % len(_DRIVER_NAMES)]
            sec_trips = max(1, (seed * 13) % 20 + 1)

            rows.append({
                "vehicle_plate": plate,
                "driver_id": sec_id,
                "driver_name": sec_name,
                "role": "secondary",
                "trips": sec_trips,
            })
    return rows


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _load_table(conn: duckdb.DuckDBPyConnection, table: str, csv_path: Path) -> int:
    literal = str(csv_path.resolve()).replace("'", "''")
    conn.execute(
        f'CREATE OR REPLACE TABLE "{table}" AS '
        f"SELECT * FROM read_csv_auto('{literal}', header=true)"
    )
    row = conn.execute(f'SELECT count(*) FROM "{table}"').fetchone()
    return int(row[0]) if row else 0


def seed(db_path: Path = DB_PATH) -> None:
    """Генерирует CSV-сиды и загружает таблицы в DuckDB. Идемпотентно."""
    SEED_DIR.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(db_path)) as conn:
        ref_rows = _build_ref(conn)
        trip_rows = _build_trips(ref_rows)

        _write_csv(CSV_REF, _FIELDS_REF, ref_rows)
        _write_csv(CSV_TRIPS, _FIELDS_TRIPS, trip_rows)

        n_ref = _load_table(conn, "driver_reference", CSV_REF)
        n_trips = _load_table(conn, "driver_trips", CSV_TRIPS)

    print(f"driver_reference : {n_ref:>3} rows  → {CSV_REF}")
    print(f"driver_trips     : {n_trips:>3} rows  → {CSV_TRIPS}")


if __name__ == "__main__":
    args = sys.argv[1:]
    seed(Path(args[0]) if args else DB_PATH)
