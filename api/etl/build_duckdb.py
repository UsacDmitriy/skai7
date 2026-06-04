"""
ETL: build data/skai.duckdb from datasets/ready/ CSVs + alarm_type_catalog.

Usage:
    python -m api.etl.build_duckdb
    python api/etl/build_duckdb.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

# Mapping: top-level folder under datasets/ready/ -> prefix.
# The nested folder video_events/work_rest_single_vehicle/ maps to video_events__wr.
FOLDER_PREFIX: dict[str, str] = {
    "video_events": "video_events",
    "fuel_reconciliation": "fuel",
    "sensor_diagnostics": "sensors",
    "navigation_problem_tracks": "navigation",
    "normal_tracks_zis": "normal_zis",
    "reference": "reference",
}

# Special nested folder overrides: relative path (from ready_dir) -> prefix
NESTED_PREFIX: dict[str, str] = {
    "video_events/work_rest_single_vehicle": "video_events__wr",
}


def _resolve_prefix(csv_path: Path, ready_dir: Path) -> str | None:
    """Return table prefix for a CSV, or None if the file should be skipped."""
    rel = csv_path.relative_to(ready_dir)
    parts = rel.parts  # e.g. ('video_events', 'work_rest_single_vehicle', 'track_points.csv')

    if len(parts) < 2:
        # File directly under ready_dir (e.g. manifest.csv) — skip
        return None

    top_folder = parts[0]

    # Build the folder path (without filename) to check nested overrides
    folder_rel = "/".join(parts[:-1])  # e.g. "video_events/work_rest_single_vehicle"

    # Check nested overrides first (longest match wins, but we only have one level)
    for nested_key, nested_pfx in NESTED_PREFIX.items():
        if folder_rel == nested_key or folder_rel.startswith(nested_key + "/"):
            return nested_pfx

    # Fall back to top-level folder mapping
    return FOLDER_PREFIX.get(top_folder)  # None if unknown folder


def _table_name(prefix: str, csv_path: Path) -> str:
    """Construct table name: {prefix}__{csv_stem_lowercase}."""
    stem = csv_path.stem.lower()
    return f"{prefix}__{stem}"


def _load_csvs(conn: duckdb.DuckDBPyConnection, ready_dir: Path) -> int:
    """Load all CSVs from ready_dir into DuckDB. Returns number of tables created."""
    csv_files = sorted(ready_dir.rglob("*.csv"))
    tables_created = 0

    for csv_path in csv_files:
        prefix = _resolve_prefix(csv_path, ready_dir)
        if prefix is None:
            print(f"  [skip] {csv_path.relative_to(ready_dir)} (no prefix mapping)")
            continue

        table = _table_name(prefix, csv_path)
        sql = (
            f'CREATE OR REPLACE TABLE "{table}" AS '
            f"SELECT * FROM read_csv_auto('{csv_path}', header=true, all_varchar=false)"
        )
        conn.execute(sql)
        row_count = conn.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
        print(f"  [load] {table!r:60s} {row_count:>6} rows  <- {csv_path.relative_to(ready_dir)}")
        tables_created += 1

    return tables_created


def _load_alarm_catalog(conn: duckdb.DuckDBPyConnection, json_path: Path) -> int:
    """Load alarm_type_catalog from JSON. Returns row count."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    alarm_types: list[dict] = data["alarm_types"]

    conn.execute('DROP TABLE IF EXISTS "alarm_type_catalog"')
    conn.execute(
        """
        CREATE TABLE "alarm_type_catalog" (
            raw               VARCHAR,
            code              VARCHAR,
            label_ru          VARCHAR,
            source            VARCHAR,
            severity          VARCHAR,
            requires_video    BOOLEAN,
            auto_request_video BOOLEAN
        )
        """
    )

    for row in alarm_types:
        conn.execute(
            'INSERT INTO "alarm_type_catalog" VALUES (?, ?, ?, ?, ?, ?, ?)',
            [
                row["raw"],
                row["code"],
                row["label_ru"],
                row["source"],
                row["severity"],
                bool(row["requires_video"]),
                bool(row["auto_request_video"]),
            ],
        )

    count = conn.execute('SELECT count(*) FROM "alarm_type_catalog"').fetchone()[0]
    print(f"  [load] 'alarm_type_catalog'                                       {count:>6} rows  <- {json_path.name}")
    return count


def _apply_sql_files(conn: duckdb.DuckDBPyConnection, sql_dir: Path) -> int:
    """Execute all *.sql files in sql_dir in lexicographic order. Returns file count."""
    if not sql_dir.exists():
        print(f"  [sql]  {sql_dir} not found — skipping (views will be added later)")
        return 0

    sql_files = sorted(sql_dir.glob("*.sql"))
    if not sql_files:
        print(f"  [sql]  {sql_dir} is empty — skipping")
        return 0

    for sql_file in sql_files:
        sql_text = sql_file.read_text(encoding="utf-8")
        conn.execute(sql_text)
        print(f"  [sql]  applied {sql_file.name}")

    return len(sql_files)


def _print_summary(conn: duckdb.DuckDBPyConnection, tables_total: int) -> None:
    """Print post-build summary to stdout."""
    print()
    print("=" * 60)
    print("BUILD SUMMARY")
    print("=" * 60)
    print(f"  Total tables/views loaded: {tables_total}")

    # Key row counts
    checks = [
        ("video_events__selected_video_alarms", 54),
        ("alarm_type_catalog", 14),
        ("video_events__track_points", None),
        ("navigation__track_points", None),
    ]
    for table, expected in checks:
        try:
            count = conn.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
            status = ""
            if expected is not None:
                status = " OK" if count == expected else f" WARN expected={expected}"
            print(f"  {table!r:50s}: {count:>6} rows{status}")
        except Exception as exc:
            print(f"  {table!r:50s}: ERROR — {exc}")

    # Check v_incidents view
    try:
        conn.execute("SELECT count(*) FROM v_incidents")
        print("  view 'v_incidents'                                : EXISTS")
    except Exception:
        print("  view 'v_incidents'                                : not yet (b3)")

    print("=" * 60)


def build(
    db_path: Path = Path("data/skai.duckdb"),
    ready_dir: Path = Path("datasets/ready"),
    json_path: Path = Path("data/analysis/alarm_types.json"),
    sql_dir: Path = Path("api/sql"),
) -> None:
    """Build (or rebuild) data/skai.duckdb idempotently."""
    db_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Building {db_path} ...")
    with duckdb.connect(str(db_path)) as conn:
        print("\n-- Loading CSVs --")
        n_tables = _load_csvs(conn, ready_dir)

        print("\n-- Loading alarm_type_catalog --")
        _load_alarm_catalog(conn, json_path)
        n_tables += 1  # catalog counts as a table

        print("\n-- Applying SQL files --")
        n_sql = _apply_sql_files(conn, sql_dir)

        _print_summary(conn, tables_total=n_tables + n_sql)

    print(f"\nDone. Database written to {db_path.resolve()}")


if __name__ == "__main__":
    # Support running as: python api/etl/build_duckdb.py [db_path [ready_dir [json_path [sql_dir]]]]
    args = sys.argv[1:]
    kwargs: dict = {}
    if len(args) >= 1:
        kwargs["db_path"] = Path(args[0])
    if len(args) >= 2:
        kwargs["ready_dir"] = Path(args[1])
    if len(args) >= 3:
        kwargs["json_path"] = Path(args[2])
    if len(args) >= 4:
        kwargs["sql_dir"] = Path(args[3])
    build(**kwargs)
