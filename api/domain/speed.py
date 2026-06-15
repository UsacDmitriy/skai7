"""Схема домена speed (контракт §10.2) — кросс-сверка скоростей событие↔GPS-трек.

`SpeedCheck` — видимый слой доверия к скорости на каждом инциденте: скорость из
события аларма против ближайшей точки GPS-трека (кейс Фомина). Не AI-фича (§10.0):
без сети/ML, детерминированно из DuckDB.

b5 — владелец `api/domain/*`; b29 добавляет схему аддитивно (§10.6).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SpeedCheck(BaseModel):
    """Сверка скорости события и GPS-трека (§10.2).

    `delta_kmh = |event − track|` (оба не NULL), иначе None. Пороги (считает сервис):
    `ok` ≤ 5 · `minor` ≤ 15 · `major` > 15; `no_data` если любой источник NULL.
    ASSUMPTION (§10.2): истина — GPS-трек → `truth_source` всегда `'gps_track'`.
    """

    id: str
    event_speed_kmh: float | None = None
    track_speed_kmh: float | None = None
    max_track_speed_kmh: float | None = None
    delta_kmh: float | None = None
    agreement: Literal["ok", "minor", "major", "no_data"]
    truth_source: Literal["gps_track"] = "gps_track"
