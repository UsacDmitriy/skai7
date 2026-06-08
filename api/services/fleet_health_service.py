"""Сервис домена fleet-health (§9.0/§9.6, аддендум волны 3 — хаб «Здоровье парка»).

Объединение disjoint-популяций (fuel ∪ sensors ∪ navigation) по нормализованному
госномеру материализовано во view `v_fleet_health` (w3-9). Паттерн как `reb_service`/
`navigation_service`: читаем view через `rows_to_dicts`, сборку Pydantic — здесь.
`coverage()` отдаёт РАЗМЕРЫ ИСТОЧНИКОВ для баннера (§9.0): fuel/sensors — число строк
своих view, navigation — число matched-ТС, in_video_fleet — пересечение ростера с
видеопарком. Кросс-связей там, где общих ТС нет, не обещаем (§9.0): топливо — остров.
"""

from __future__ import annotations

from typing import Any

import duckdb

from api.domain.fleet_health import FleetCoverage, FleetHealthResponse, FleetHealthRow
from api.repositories import rows_to_dicts


def _f(value: Any) -> float | None:
    """float|None (сохраняет nullable-семантику KPI: «—» у отсутствующего домена)."""
    return float(value) if value is not None else None


def _i(value: Any) -> int | None:
    """int|None (gap_count = null у ТС без навигации)."""
    return int(value) if value is not None else None


def _str_or_none(value: Any) -> str | None:
    return str(value) if value is not None else None


def _to_row(r: dict[str, Any]) -> FleetHealthRow:
    """Строка `v_fleet_health` → `FleetHealthRow` (§9.6). KPI nullable → «—» на фронте."""
    return FleetHealthRow(
        plate=str(r["plate"]),
        plate_norm=str(r["plate_norm"]),
        has_fuel=bool(r["has_fuel"]),
        has_sensors=bool(r["has_sensors"]),
        has_nav=bool(r["has_nav"]),
        fuel_delta_l=_f(r["fuel_delta_l"]),
        sensors_gap_can_gps_km=_f(r["sensors_gap_can_gps_km"]),
        sensors_online_status=_str_or_none(r["sensors_online_status"]),  # type: ignore[arg-type]
        nav_gap_count=_i(r["nav_gap_count"]),
        reb_link_id=_str_or_none(r["reb_link_id"]),
        in_video_fleet=bool(r["in_video_fleet"]),
    )


def list_fleet_health(db: duckdb.DuckDBPyConnection) -> list[FleetHealthRow]:
    """Ростер «Здоровье парка» (17 ТС объединения, §9.6). Порядок — из view (детерминирован)."""
    rows = rows_to_dicts(db.execute('SELECT * FROM "v_fleet_health"'))
    return [_to_row(r) for r in rows]


def coverage(db: duckdb.DuckDBPyConnection) -> FleetCoverage:
    """Баннер покрытия (§9.0): {fuel:10, sensors:7, navigation:5, in_video_fleet:2}.

    fuel/sensors — размеры одноимённых view; navigation — число matched-ТС
    (unmatched в популяцию не входит); in_video_fleet — строки ростера в видеопарке.
    """

    def scalar(sql: str) -> int:
        return int(db.execute(sql).fetchone()[0])

    return FleetCoverage(
        fuel=scalar('SELECT count(*) FROM "v_fuel"'),
        sensors=scalar('SELECT count(*) FROM "v_sensors"'),
        navigation=scalar(
            "SELECT count(*) FROM \"v_nav_problem\" WHERE \"match_status\" = 'matched'"
        ),
        in_video_fleet=scalar(
            'SELECT count(*) FROM "v_fleet_health" WHERE "in_video_fleet"'
        ),
    )


def get_fleet_health(db: duckdb.DuckDBPyConnection) -> FleetHealthResponse:
    """Полный ответ `/api/fleet-health` (§9.6): баннер покрытия + ростер ТС."""
    return FleetHealthResponse(coverage=coverage(db), rows=list_fleet_health(db))
