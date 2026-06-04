"""Сервис домена reports (§3.3 / §7.5) — рабочая реализация.

Строит DriverReport/FleetReport поверх обогащённых сводок incidents_service +
метрик ТС из vehicles_repo. `query` — regex-NLU-заглушка (§3.3); реальный
Groq/Whisper-парсер придёт в b9 (`nlu_service`), сюда подключится через ReportQuery.
"""

from __future__ import annotations

import re
from typing import Any

import duckdb

from api.core import enrichment
from api.domain.incidents import IncidentSummary
from api.domain.reports import (
    DriverRef,
    DriverReport,
    FleetByDriver,
    FleetByVehicle,
    FleetReport,
    ReportKPI,
    ReportPeriod,
    ReportQuery,
    ViolationRow,
)
from api.repositories import vehicles_repo
from api.services import incidents_service

# «Грубые» нарушения (§7.5): critical ИЛИ курение/превышение.
_GROSS_CODES = {"OVERSPEED", "DMS_SMOKING"}
# Источники видео-детекции (ВА) — для ReportKPI.video_da.
_VIDEO_SOURCES = {"DMS", "ADAS", "COMBINED"}


def _is_gross(severity: str, alarm_code: str) -> bool:
    return severity == "critical" or alarm_code in _GROSS_CODES


def _violation_row(s: IncidentSummary) -> ViolationRow:
    return ViolationRow(
        id=s.id,
        ts=s.ts,
        alarm_code=s.alarm_code,
        alarm_label_ru=s.alarm_label_ru,
        source=s.source,
        severity=s.severity,
        is_gross=_is_gross(s.severity, s.alarm_code),
    )


def _kpi(summaries: list[IncidentSummary]) -> ReportKPI:
    return ReportKPI(
        total=len(summaries),
        video_da=sum(1 for s in summaries if s.source in _VIDEO_SOURCES),
        telematics=sum(1 for s in summaries if s.source == "TELEMATICS"),
        gross=sum(1 for s in summaries if _is_gross(s.severity, s.alarm_code)),
    )


def _period(summaries: list[IncidentSummary], days: int) -> ReportPeriod:
    timestamps = sorted(s.ts for s in summaries if s.ts)
    frm = timestamps[0] if timestamps else ""
    to = timestamps[-1] if timestamps else ""
    return ReportPeriod(**{"from": frm, "to": to, "days": days})


def _avg_risk(summaries: list[IncidentSummary]) -> int:
    if not summaries:
        return 0
    return round(sum(s.risk_score for s in summaries) / len(summaries))


def _cameras_ok(vehicle: dict[str, Any] | None) -> str:
    """Доля онлайн-камер «N/3». Без точного источника — по downloaded_video_count."""
    # TODO: реальный статус камер из v_vehicle (§7.2, b10).
    if not vehicle:
        return "0/3"
    online = 3 if (vehicle.get("downloaded_video_count") or 0) > 0 else 1
    return f"{min(online, 3)}/3"


def driver_report(
    db: duckdb.DuckDBPyConnection, plate: str, period_days: int = 3
) -> DriverReport:
    """GET /api/reports/driver/{plate} (§7.5, идея #2 В-1)."""
    summaries = incidents_service.list_summaries(db, {"vehicle_plate": plate})
    vehicle = vehicles_repo.get_vehicle(db, plate)

    risk = _avg_risk(summaries)
    safety_score = max(0, min(100, 100 - risk))
    gross = sum(1 for s in summaries if _is_gross(s.severity, s.alarm_code))
    trips = int(vehicle.get("track_window_count") or 0) if vehicle else 0
    mileage = float(vehicle.get("total_track_mileage_km") or 0.0) if vehicle else 0.0
    model = (
        summaries[0].vehicle_model if summaries else enrichment.vehicle_model_for(plate)
    )

    driver_ref = DriverRef(
        driver_id=enrichment.driver_id_for(plate),
        driver_name=enrichment.driver_for(plate),
        role="main",
        trips=trips,
        safety_score=safety_score,
        risk_score=risk,
    )

    return DriverReport(
        driver=driver_ref,
        vehicle_plate=plate,
        vehicle_model=model,
        period=_period(summaries, period_days),
        mileage_km=mileage,
        trips=trips,
        kpi=_kpi(summaries),
        disciplinary_warning=(gross >= 3 or safety_score < 60),
        violations=[_violation_row(s) for s in summaries],
    )


def fleet_report(db: duckdb.DuckDBPyConnection, period_days: int = 3) -> FleetReport:
    """GET /api/reports/fleet (§7.5, идея #2 В-2)."""
    summaries = incidents_service.list_summaries(db, {})

    by_plate: dict[str, list[IncidentSummary]] = {}
    for s in summaries:
        by_plate.setdefault(s.vehicle_plate, []).append(s)

    by_drivers: list[FleetByDriver] = []
    by_vehicles: list[FleetByVehicle] = []
    for plate, items in sorted(by_plate.items()):
        risk = _avg_risk(items)
        gross = sum(1 for s in items if _is_gross(s.severity, s.alarm_code))
        model = items[0].vehicle_model
        vehicle = vehicles_repo.get_vehicle(db, plate)
        mileage = float(vehicle.get("total_track_mileage_km") or 0.0) if vehicle else 0.0
        trips = int(vehicle.get("track_window_count") or 0) if vehicle else 0
        driver_name = enrichment.driver_for(plate)

        by_drivers.append(
            FleetByDriver(
                driver=DriverRef(
                    driver_id=enrichment.driver_id_for(plate),
                    driver_name=driver_name,
                    role="main",
                    trips=trips,
                    safety_score=max(0, min(100, 100 - risk)),
                    risk_score=risk,
                ),
                vehicle_plate=plate,
                vehicle_model=model,
                mileage_km=mileage,
                risk_score=risk,
                gross=gross,
                total=len(items),
            )
        )
        by_vehicles.append(
            FleetByVehicle(
                plate=plate,
                vehicle_model=model,
                main_driver=driver_name,
                mileage_km=mileage,
                risk_score=risk,
                gross=gross,
                total=len(items),
                cameras_ok=_cameras_ok(vehicle),
            )
        )

    return FleetReport(
        period=_period(summaries, period_days),
        kpi=_kpi(summaries),
        vehicles_count=len(by_plate),
        by_drivers=by_drivers,
        by_vehicles=by_vehicles,
    )


def report_for_query(
    db: duckdb.DuckDBPyConnection, q: ReportQuery
) -> DriverReport | FleetReport:
    """POST /api/reports/query (§7.5): уже разобранный ReportQuery → отчёт.

    kind="driver": берём plate напрямую или резолвим по driver_name; нет ТС →
    fleet-отчёт как фолбэк. kind="fleet": сводка по парку.
    """
    if q.kind == "driver":
        plate = q.plate
        if not plate and q.driver_name:
            plate = _plate_for_driver_name(db, q.driver_name)
        if plate:
            return driver_report(db, plate.upper().replace(" ", ""), q.period_days)
    return fleet_report(db, q.period_days)


# ---------------------------------------------------------------------------
# NLU-заглушка (§3.3). Реальный парсер — b9 nlu_service (Groq/Whisper).
# ---------------------------------------------------------------------------

# Госномер РФ: буква + 3 цифры + 2 буквы + 2–3 цифры региона (кириллица), пробелы опц.
_PLATE_RE = re.compile(r"[АВЕКМНОРСТУХ]\s?\d{3}\s?[АВЕКМНОРСТУХ]{2}\s?\d{2,3}", re.IGNORECASE)
_PERIOD_RE = re.compile(r"за\s+(\d+)\s+(?:дн|день|дня|дней)", re.IGNORECASE)
# ФИО: 2–3 слова с заглавной кириллической буквы.
_NAME_RE = re.compile(r"[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2}")


def query(
    db: duckdb.DuckDBPyConnection, text: str
) -> DriverReport | FleetReport:
    """POST /api/reports/query (§3.3): regex-парс «ФИО/госномер/период» → отчёт.

    Возвращает DriverReport если найден госномер/ФИО, иначе FleetReport.
    # TODO: заменить regex на Groq/Whisper (b9 nlu_service, §7.3).
    """
    period_match = _PERIOD_RE.search(text)
    period_days = int(period_match.group(1)) if period_match else 3

    plate_match = _PLATE_RE.search(text)
    if plate_match:
        plate = plate_match.group(0).upper().replace(" ", "")
        return driver_report(db, plate, period_days)

    name_match = _NAME_RE.search(text)
    if name_match:
        # ФИО → ищем ТС с таким водителем (enrichment детерминирован по plate).
        plate = _plate_for_driver_name(db, name_match.group(0))
        if plate:
            return driver_report(db, plate, period_days)

    return fleet_report(db, period_days)


def _plate_for_driver_name(
    db: duckdb.DuckDBPyConnection, name: str
) -> str | None:
    """Обратный поиск ТС по ФИО (enrichment.driver_for детерминирован по plate)."""
    target = name.strip().lower()
    for vehicle in vehicles_repo.list_vehicles(db):
        plate = vehicle.get("unit_state_number") or ""
        if plate and enrichment.driver_for(plate).lower() == target:
            return plate
    return None
