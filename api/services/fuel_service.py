"""Стаб домена fuel (§3.4). Эндпоинты отдают 501; таблицы в DuckDB уже есть."""

from __future__ import annotations

from typing import Any


def list_fuel(*_args: Any, **_kwargs: Any) -> None:
    """TODO: расхождение топлива ЗИС vs карты (`fuel__fuel_vehicles`)."""
    raise NotImplementedError("fuel domain not implemented (§3.4)")
