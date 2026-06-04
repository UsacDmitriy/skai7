"""Стаб домена sensors (§3.4). Эндпоинты отдают 501; таблицы в DuckDB уже есть."""

from __future__ import annotations

from typing import Any


def list_sensors(*_args: Any, **_kwargs: Any) -> None:
    """TODO: сенсорная диагностика (`sensors__*`)."""
    raise NotImplementedError("sensors domain not implemented (§3.4)")
