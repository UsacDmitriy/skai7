"""Сервис кросс-сверки скоростей (§10.2/§10.5) — `GET /api/incidents/{id}/speed-check`.

Сравнивает скорость из события аларма ("Speed") и ближайшей точки GPS-трека (±10 с)
по view `v_speed_check` (b29). Слой доверия к скорости на инциденте (кейс Фомина) —
НЕ AI-фича: без сети/ML, детерминированно. Повторный вызов → идентичный ответ.

Разделение ответственности (§10.2):
  - `v_speed_check` (SQL) отдаёт сырьё: event/track/max-скорости на аларм.
  - `delta_kmh` и `agreement` (пороги ok/minor/major/no_data) считает ЗДЕСЬ сервис.
Негатив (§10.5): нет точки в окне / нет "Speed" события → `agreement='no_data'`,
`delta_kmh=None`, 200 (не 5xx); неизвестный `id` → None → 404 в роутере.
"""

from __future__ import annotations

import duckdb

from api.domain.speed import SpeedCheck
from api.repositories import rows_to_dicts

# Пороги расхождения по delta_kmh (§10.2). Зеркалит SQL-условие major в 34_v_consistency.sql.
_OK_MAX = 5.0
_MINOR_MAX = 15.0


def _agreement(delta: float | None) -> str:
    """`no_data` если delta None; иначе `ok` ≤ 5 · `minor` ≤ 15 · `major` > 15 (§10.2)."""
    if delta is None:
        return "no_data"
    if delta <= _OK_MAX:
        return "ok"
    if delta <= _MINOR_MAX:
        return "minor"
    return "major"


def speed_check(db: duckdb.DuckDBPyConnection, incident_id: str) -> SpeedCheck | None:
    """Сверка скорости инцидента или None, если аларм не найден (→ 404).

    `delta_kmh = |event − track|` при обоих не-NULL, иначе None (→ `agreement='no_data'`).
    Детерминированно из `v_speed_check`.
    """
    rows = rows_to_dicts(
        db.execute(
            'SELECT "id", "event_speed_kmh", "track_speed_kmh", "max_track_speed_kmh" '
            "FROM v_speed_check WHERE \"id\" = ? LIMIT 1",
            [incident_id],
        )
    )
    if not rows:
        return None

    row = rows[0]
    event = row["event_speed_kmh"]
    track = row["track_speed_kmh"]
    delta = abs(event - track) if event is not None and track is not None else None

    return SpeedCheck(
        id=str(row["id"]),
        event_speed_kmh=event,
        track_speed_kmh=track,
        max_track_speed_kmh=row["max_track_speed_kmh"],
        delta_kmh=round(delta, 4) if delta is not None else None,
        agreement=_agreement(delta),
        truth_source="gps_track",
    )
