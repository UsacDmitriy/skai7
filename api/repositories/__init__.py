"""Доступ к DuckDB (SQL → dict/list). b5 владеет `api/repositories/*`.

Репозитории не знают про Pydantic-модели — отдают сырые dict'ы;
сборка в доменные модели и обогащение — слой `api/services/*`.
"""

from __future__ import annotations

from typing import Any

import duckdb


def rows_to_dicts(result: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """Превращает результат `execute(...)` в список dict по именам колонок."""
    columns = [d[0] for d in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]
