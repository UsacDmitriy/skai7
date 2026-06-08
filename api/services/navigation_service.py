"""Сервис домена navigation (§9.1–§9.3, аддендум волны 3 — список проблемных треков → РЭБ).

`navigation__navigation_problem_vehicles` (5 matched + 1 unmatched) ⋈ агрегат разрывов
`navigation__track_periods` (period_type=3 = потеря GPS) из view `v_nav_problem` →
список-вход к существующему `/api/reb/{id}` (§7.4, b12). Паттерн как `reb_service`:
читаем view через `rows_to_dicts`, сборку Pydantic делаем здесь. `reb_link_id =
public_unit_id` (UUID есть в обеих таблицах); у unmatched-ТС он `null` — строка не
кликабельна в РЭБ. `in_video_fleet` считается здесь: норм. госномер ∈ `v_incidents`.
"""

from __future__ import annotations

import duckdb

from api.domain.fleet_health import NavProblemVehicle
from api.repositories import rows_to_dicts


def _norm(plate: str | None) -> str:
    """Нормализация госномера для матчинга: верхний регистр без пробелов (§9.0)."""
    return (plate or "").upper().replace(" ", "")


def _video_fleet_plates(db: duckdb.DuckDBPyConnection) -> set[str]:
    """Норм. госномера видеопарка (`v_incidents.vehicle_plate`) — для `in_video_fleet` (§9.2)."""
    rows = rows_to_dicts(
        db.execute('SELECT DISTINCT "vehicle_plate" FROM "v_incidents"')
    )
    return {_norm(r["vehicle_plate"]) for r in rows if r["vehicle_plate"]}


def _to_model(row: dict, video_plates: set[str]) -> NavProblemVehicle:
    """Строка `v_nav_problem` → `NavProblemVehicle`; `in_video_fleet` по норм. госномеру."""
    plate = row["plate"]
    return NavProblemVehicle(
        public_unit_id=row["public_unit_id"],
        plate=plate,
        vehicle_label=row["vehicle_label"],
        brand=row["brand"],
        problem_description=str(row["problem_description"] or ""),
        match_status=row["match_status"],
        gap_count=int(row["gap_count"] or 0),
        total_periods=int(row["total_periods"] or 0),
        total_gap_duration_sec=int(row["total_gap_duration_sec"] or 0),
        reb_link_id=row["reb_link_id"],
        in_video_fleet=bool(plate) and _norm(plate) in video_plates,
    )


def list_nav_problems(db: duckdb.DuckDBPyConnection) -> list[NavProblemVehicle]:
    """Все проблемные ТС навигации (5 matched + 1 unmatched), §9.1. Порядок — из view."""
    video_plates = _video_fleet_plates(db)
    rows = rows_to_dicts(db.execute('SELECT * FROM "v_nav_problem"'))
    return [_to_model(r, video_plates) for r in rows]


def get_nav_problem(
    db: duckdb.DuckDBPyConnection, plate: str
) -> NavProblemVehicle | None:
    """Сводка одного ТС по госномеру/лейблу/unit_id. `None` → роутер 404 (§9.5).

    Матч по норм. ключам: чистый госномер, нормализованный лейбл, «грязный» лейбл
    и `public_unit_id` (UUID) — чтобы `/api/navigation/{plate}` работал из разных входов.
    """
    key = _norm(plate)
    if not key:
        return None
    video_plates = _video_fleet_plates(db)
    rows = rows_to_dicts(db.execute('SELECT * FROM "v_nav_problem"'))
    for r in rows:
        candidates = {
            _norm(r["plate"]),
            _norm(r["plate_norm"]),
            _norm(r["vehicle_label"]),
            _norm(r["public_unit_id"]),
        } - {""}
        if key in candidates:
            return _to_model(r, video_plates)
    return None
