"""Стаб домена navigation (§3.4).

Эндпоинты `/api/navigation/*` отдают 501. Реальная навигация (GPS-разрывы РЭБ)
реализуется b12 как `/api/reb` поверх `navigation__*`.
"""

from __future__ import annotations

from typing import Any


def list_navigation(*_args: Any, **_kwargs: Any) -> None:
    """TODO: проблемные треки навигации (реализуется b12 → /api/reb)."""
    raise NotImplementedError("navigation domain not implemented (§3.4; см. b12 /api/reb)")
