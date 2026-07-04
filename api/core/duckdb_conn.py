"""
DuckDB connection management.

Opens settings.db_path read-only. One cached connection per process; the
FastAPI dependency `get_db` yields a per-request thread-local cursor of it.

DuckDB-коннект НЕ потокобезопасен: FastAPI исполняет sync-эндпоинты в
threadpool, поэтому конкурентные запросы, делящие один объект коннекта,
перемешивают курсоры (KeyError на колонках, пустые ответы). Канонический
фикс DuckDB — каждый поток работает через `connection.cursor()`
(thread-local курсор того же инстанса БД). См. docs/clients/python.
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

    # PRAGMA-оптимизации под многопоточную нагрузку.
    threads = getattr(settings, "duckdb_threads", 0)
    if threads > 0:
        _connection.execute(f"PRAGMA threads={threads}")
    mem_mb = getattr(settings, "duckdb_memory_limit_mb", 0)
    if mem_mb > 0:
        _connection.execute(f"PRAGMA memory_limit='{mem_mb}MB'")

    return _connection


def get_db() -> Iterator[duckdb.DuckDBPyConnection]:
    """FastAPI yield-dependency: per-request thread-local cursor.

    `cursor()` создаёт изолированный курсор поверх общего инстанса БД —
    конкурентные запросы из threadpool больше не делят один объект коннекта
    и не гонятся за результатами. Курсор закрывается по завершении запроса.
    """
    cursor = get_connection().cursor()
    try:
        yield cursor
    finally:
        cursor.close()


def close_connection() -> None:
    """Close the cached connection (used on app shutdown / in tests)."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
