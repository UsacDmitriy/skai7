"""Сервис домена fuel (§9.0–§9.3, аддендум волны 3 — топливная сверка ЗИС vs карты).

Топливо — изолированный остров (§9.0: пересечение с видеопарком = 0): к инцидентам/
водителям/РЭБ не линкуется. Паттерн как `reb_service` (b12): читаем view/таблицы через
`rows_to_dicts`, сборку Pydantic делаем здесь (репозиторного слоя не вводим).
Headline KPI — `volume_delta_zis_minus_card_l` (расхождение бак-сенсор ЗИС vs карты).
"""

from __future__ import annotations

from typing import Any

import duckdb

from api.domain.fleet_health import (
    FuelEvent,
    FuelReconRow,
    FuelSummary,
    FuelVehicleCard,
    FuelVehicleSummary,
)
from api.repositories import rows_to_dicts


def _f(value: Any) -> float | None:
    """float или None (сохраняет nullable-семантику колонок §9.2)."""
    return float(value) if value is not None else None


def _ts(value: Any) -> str | None:
    """Таймстамп DuckDB (datetime|None) → строка ISO|None."""
    return str(value) if value is not None else None


def _str_or_none(value: Any) -> str | None:
    return str(value) if value is not None else None


def _summary_from_row(r: dict[str, Any]) -> FuelVehicleSummary:
    """Строка `v_fuel` → `FuelVehicleSummary` (§9.2)."""
    return FuelVehicleSummary(
        vehicle_id=str(r["vehicle_id"]),
        model=str(r["model"] or ""),
        vin=str(r["vin"] or ""),
        fuel_volume_zis_l=float(r["fuel_volume_zis_l"] or 0.0),
        fuel_volume_card_l=float(r["fuel_volume_card_l"] or 0.0),
        volume_delta_zis_minus_card_l=float(r["volume_delta_zis_minus_card_l"] or 0.0),
        refuel_count_zis=int(r["refuel_count_zis"] or 0),
        transaction_count_card=int(r["transaction_count_card"] or 0),
        period_start=str(r["period_start"] or ""),
        period_end=str(r["period_end"] or ""),
        recon_status=str(r["recon_status"] or "matched"),  # type: ignore[arg-type]
    )


def list_fuel(db: duckdb.DuckDBPyConnection) -> list[FuelVehicleSummary]:
    """Топливный ростер (§9.1): `FuelVehicleSummary[]` из `v_fuel` (10 строк)."""
    rows = rows_to_dicts(db.execute('SELECT * FROM "v_fuel" ORDER BY "vehicle_id"'))
    return [_summary_from_row(r) for r in rows]


def get_fuel(
    db: duckdb.DuckDBPyConnection, plate: str
) -> FuelVehicleCard | None:
    """Карточка топлива ТС (§9.2) по госномеру. `None` если ТС нет (роутер → 404).

    Госномер нормализуется (strip пробелов + регистр, Unicode-aware `upper`),
    чтобы `/api/fuel/А144ЕВ193` матчился независимо от ввода из UI.
    Списки `reconciliation`/`events` читаются по `vehicle_id` напрямую (во view
    не материализуются); пустые списки — валидны (§9.5).
    """
    base = rows_to_dicts(
        db.execute(
            'SELECT * FROM "v_fuel" '
            "WHERE upper(replace(\"vehicle_id\", ' ', '')) "
            "     = upper(replace(?, ' ', '')) "
            "LIMIT 1",
            [plate],
        )
    )
    if not base:
        return None

    summary_row = _summary_from_row(base[0])
    vehicle_id = summary_row.vehicle_id

    # summary: агрегаты пробега/расхода (None, если строки нет — валидно, §9.5).
    summary_rows = rows_to_dicts(
        db.execute(
            'SELECT * FROM "fuel__fuel_summary" WHERE "vehicle_id" = ?',
            [vehicle_id],
        )
    )
    summary: FuelSummary | None = None
    if summary_rows:
        s = summary_rows[0]
        summary = FuelSummary(
            fuel_spent_l=float(s["fuel_spent_l"] or 0.0),
            total_mileage_km=float(s["total_mileage_km"] or 0.0),
            average_consumption_l_per_100km=float(
                s["average_consumption_l_per_100km"] or 0.0
            ),
            average_speed_kmh=float(s["average_speed_kmh"] or 0.0),
            fuelings_count=int(s["fuelings_count"] or 0),
            defuelings_count=int(s["defuelings_count"] or 0),
        )

    # reconciliation: строки сверки транзакция ↔ событие сенсора.
    recon_rows = rows_to_dicts(
        db.execute(
            'SELECT "row_id", "transaction_ts", "event_ts", "transaction_volume_l", '
            '       "sensor_volume_l", "volume_delta_l", "time_delta_min", '
            '       "amount_rub", "status", "reason" '
            'FROM "fuel__fuel_reconciliation" WHERE "vehicle_id" = ? '
            'ORDER BY "transaction_ts", "row_id"',
            [vehicle_id],
        )
    )
    reconciliation = [
        FuelReconRow(
            row_id=str(r["row_id"]),
            transaction_ts=_ts(r["transaction_ts"]),
            event_ts=_ts(r["event_ts"]),
            transaction_volume_l=_f(r["transaction_volume_l"]),
            sensor_volume_l=_f(r["sensor_volume_l"]),
            volume_delta_l=_f(r["volume_delta_l"]),
            time_delta_min=_f(r["time_delta_min"]),
            amount_rub=_f(r["amount_rub"]),
            status=str(r["status"] or ""),
            reason=_str_or_none(r["reason"]),
        )
        for r in recon_rows
    ]

    # events: топливные события ЗИС (заправки/сливы).
    event_rows = rows_to_dicts(
        db.execute(
            'SELECT "event_id", "event_ts", "event_name", "volume_l", "before_l", '
            '       "after_l", "lat", "lon", "address" '
            'FROM "fuel__fuel_events" WHERE "vehicle_id" = ? '
            'ORDER BY "event_ts", "event_id"',
            [vehicle_id],
        )
    )
    events = [
        FuelEvent(
            event_id=str(r["event_id"]),
            event_ts=str(r["event_ts"] or ""),
            event_name=str(r["event_name"] or ""),
            volume_l=float(r["volume_l"] or 0.0),
            before_l=_f(r["before_l"]),
            after_l=_f(r["after_l"]),
            lat=_f(r["lat"]),
            lon=_f(r["lon"]),
            address=_str_or_none(r["address"]),
        )
        for r in event_rows
    ]

    return FuelVehicleCard(
        **summary_row.model_dump(),
        summary=summary,
        reconciliation=reconciliation,
        events=events,
    )
