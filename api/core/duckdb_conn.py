"""
DuckDB connection management.

Opens settings.db_path read-only. One cached connection per process; the
FastAPI dependency `get_db` yields that connection to routers.
"""
from __future__ import annotations

from typing import Iterator

import duckdb

from api.core.config import settings

_connection: duckdb.DuckDBPyConnection | None = None


def get_connection() -> duckdb.DuckDBPyConnection:
    """Return a process-wide read-only DuckDB connection (lazily opened).

    Raises a clear error if the database file is missing.
    """
    global _connection

    if _connection is not None:
        return _connection

    if not settings.db_path.exists():
        raise FileNotFoundError(
            f"DuckDB не найден: {settings.db_path}. "
            "Запусти `make db` (или `python -m api.etl.build_duckdb`), "
            "чтобы собрать базу из datasets/ready/."
        )

    _connection = duckdb.connect(str(settings.db_path), read_only=True)
    return _connection


def get_db() -> Iterator[duckdb.DuckDBPyConnection]:
    """FastAPI yield-dependency: provides the shared read-only connection."""
    conn = get_connection()
    yield conn


def close_connection() -> None:
    """Close the cached connection (used on app shutdown / in tests)."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
