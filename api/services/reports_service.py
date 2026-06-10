"""Сервис домена reports (§7.2/§7.4/§7.5) — рабочая реализация (b5 + b10).

Строит DriverReport/FleetReport/VehicleReport поверх обогащённых сводок
incidents_service (источник risk_score — формула §2, как в §1.3 для v_incidents),
справочника водителей `driver_reference`/`driver_trips` (b7) и SQL-views
v_driver_report/v_fleet/v_vehicle (b10). `query` использует реальный NLU
(`nlu_service.parse`, b9): голос/текст → ReportQuery → отчёт (формат ответа §7.4).
"""

from __future__ import annotations

from typing import Any

import duckdb

from api.core import enrichment
from api.domain.incidents import Camera, IncidentSummary
from api.domain.reports import (
    DriverRef,
    DriverReport,
    FleetByDriver,
    FleetByVehicle,
    FleetReport,
    ReportKPI,
    ReportPeriod,
    ReportQuery,
    VehicleReport,
    ViolationRow,
)
from api.repositories import rows_to_dicts, vehicles_repo
from api.services import incidents_service, narrative_service, nlu_service

# «Грубые» нарушения (§7.5): critical ИЛИ курение/превышение.
_GROSS_CODES = {"OVERSPEED", "DMS_SMOKING"}
# Источники видео-детекции (ВА) — для ReportKPI.video_da.
_VIDEO_SOURCES = {"DMS", "ADAS", "COMBINED"}


# ---------------------------------------------------------------------------
# Единое правило «грубых» (§7.5) — один хелпер для driver/fleet/vehicle.
# ---------------------------------------------------------------------------


def is_gross(row: IncidentSummary) -> bool:
    """Грубое нарушение (§7.5): severity=critical ИЛИ alarm_code ∈ {OVERSPEED, DMS_SMOKING}."""
    return row.severity == "critical" or row.alarm_code in _GROSS_CODES


def _violation_row(s: IncidentSummary) -> ViolationRow:
    return ViolationRow(
        id=s.id,
        ts=s.ts,
        alarm_code=s.alarm_code,
        alarm_label_ru=s.alarm_label_ru,
        source=s.source,
        severity=s.severity,
        is_gross=is_gross(s),
    )


def _kpi(summaries: list[IncidentSummary]) -> ReportKPI:
    return ReportKPI(
        total=len(summaries),
        video_da=sum(1 for s in summaries if s.source in _VIDEO_SOURCES),
        telematics=sum(1 for s in summaries if s.source == "TELEMATICS"),
        gross=sum(1 for s in summaries if is_gross(s)),
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


# ---------------------------------------------------------------------------
# driver_reference (§7.1, b7): safety_score водителя ТС с синтетическим фолбэком.
# ---------------------------------------------------------------------------


def _safety_score(
    db: duckdb.DuckDBPyConnection, plate: str, summaries: list[IncidentSummary]
) -> int:
    """safety_score из driver_reference (§7.1); иначе 100 − среднего risk (синтетика)."""
    if db is not None and plate:
        try:
            row = db.execute(
                'SELECT "safety_score" FROM "driver_reference" WHERE "vehicle_plate"=?',
                [plate],
            ).fetchone()
            if row and row[0] is not None:
                return int(row[0])
        except Exception:
            pass
    return max(0, min(100, 100 - _avg_risk(summaries)))


def _cameras_ok(cameras: list[Camera]) -> str:
    """Доля онлайн-камер «N/3» (всегда из 3 канонических слотов)."""
    online = sum(1 for c in cameras if c.status == "online")
    return f"{online}/3"


def _vehicle_cameras(db: duckdb.DuckDBPyConnection, plate: str) -> list[Camera]:
    """3 канонических Camera ТС из video_files (по всем алярмам ТС)."""
    try:
        files = rows_to_dicts(
            db.execute(
                'SELECT * FROM "video_events__video_files" '
                'WHERE "unit_state_number"=?',
                [plate],
            )
        )
    except Exception:
        files = []
    return [Camera(**c) for c in enrichment.cameras_from_videofiles(files)]


# ---------------------------------------------------------------------------
# driver_report / fleet_report / vehicle_report
# ---------------------------------------------------------------------------


def driver_report(
    db: duckdb.DuckDBPyConnection, plate: str, period_days: int = 3
) -> DriverReport:
    """GET /api/reports/driver/{plate} (§7.5, идея #2 В-1) — поверх v_driver_report."""
    summaries = incidents_service.list_summaries(db, {"vehicle_plate": plate})
    vehicle = vehicles_repo.get_vehicle(db, plate)

    risk = _avg_risk(summaries)
    safety_score = _safety_score(db, plate, summaries)
    gross = sum(1 for s in summaries if is_gross(s))
    trips = int(vehicle.get("track_window_count") or 0) if vehicle else 0
    mileage = float(vehicle.get("total_track_mileage_km") or 0.0) if vehicle else 0.0
    model = (
        summaries[0].vehicle_model if summaries else enrichment.vehicle_model_for(plate)
    )

    drv = enrichment.driver_for(db, plate)
    driver_ref = DriverRef(
        driver_id=drv["driver_id"],
        driver_name=drv["driver"],
        role="main",
        trips=trips,
        safety_score=safety_score,
        risk_score=risk,
    )

    report = DriverReport(
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
    report.narrative = narrative_service.narrate(report)  # b22: нарратив + коучинг.
    return report


def fleet_report(
    db: duckdb.DuckDBPyConnection, period_days: int = 3, view: str = "drivers"
) -> FleetReport:
    """GET /api/reports/fleet (§7.5, идея #2 В-2) — поверх v_fleet.

    `view ∈ {"drivers","vehicles"}` — какой разрез приоритетен на UI; оба массива
    (`by_drivers`/`by_vehicles`) всегда заполнены из одного источника (v_incidents).
    """
    summaries = incidents_service.list_summaries(db, {})

    by_plate: dict[str, list[IncidentSummary]] = {}
    for s in summaries:
        by_plate.setdefault(s.vehicle_plate, []).append(s)

    by_drivers: list[FleetByDriver] = []
    by_vehicles: list[FleetByVehicle] = []
    for plate, items in sorted(by_plate.items()):
        risk = _avg_risk(items)
        gross = sum(1 for s in items if is_gross(s))
        model = items[0].vehicle_model
        vehicle = vehicles_repo.get_vehicle(db, plate)
        mileage = float(vehicle.get("total_track_mileage_km") or 0.0) if vehicle else 0.0
        trips = int(vehicle.get("track_window_count") or 0) if vehicle else 0
        safety = _safety_score(db, plate, items)
        drv = enrichment.driver_for(db, plate)
        driver_name = drv["driver"]

        by_drivers.append(
            FleetByDriver(
                driver=DriverRef(
                    driver_id=drv["driver_id"],
                    driver_name=driver_name,
                    role="main",
                    trips=trips,
                    safety_score=safety,
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
                cameras_ok=_cameras_ok(_vehicle_cameras(db, plate)),
            )
        )

    report = FleetReport(
        period=_period(summaries, period_days),
        kpi=_kpi(summaries),
        vehicles_count=len(by_plate),
        by_drivers=by_drivers,
        by_vehicles=by_vehicles,
    )
    report.narrative = narrative_service.narrate(report)  # b22: нарратив + коучинг.
    return report


def _driver_trips(db: duckdb.DuckDBPyConnection, plate: str) -> list[dict[str, Any]]:
    """Строки driver_trips ТС (1 ТС = N водителей), детерминированный порядок."""
    try:
        return rows_to_dicts(
            db.execute(
                'SELECT "driver_id","driver_name","role","trips" '
                'FROM "driver_trips" WHERE "vehicle_plate"=? '
                "ORDER BY CASE WHEN \"role\"='main' THEN 0 ELSE 1 END, \"driver_id\"",
                [plate],
            )
        )
    except Exception:
        return []


def vehicle_report(
    db: duckdb.DuckDBPyConnection, plate: str, period_days: int = 3
) -> VehicleReport:
    """GET /api/reports/vehicle/{plate} (§7.5, идея #2 В-2/ТС, #10) — поверх v_vehicle.

    `drivers` строится из driver_trips (1 ТС = N водителей, ровно один main);
    неизвестный ТС → синтетический main из driver_for (не падать, §61).
    `cameras` всегда длины 3.
    """
    summaries = incidents_service.list_summaries(db, {"vehicle_plate": plate})
    vehicle = vehicles_repo.get_vehicle(db, plate)

    risk = _avg_risk(summaries)
    safety = _safety_score(db, plate, summaries)
    model = (
        summaries[0].vehicle_model if summaries else enrichment.vehicle_model_for(plate)
    )
    trips_total = int(vehicle.get("track_window_count") or 0) if vehicle else 0
    mileage = float(vehicle.get("total_track_mileage_km") or 0.0) if vehicle else 0.0

    trip_rows = _driver_trips(db, plate)
    drivers: list[DriverRef] = []
    for r in trip_rows:
        drivers.append(
            DriverRef(
                driver_id=r["driver_id"],
                driver_name=r["driver_name"],
                role="secondary" if r.get("role") == "secondary" else "main",
                trips=int(r.get("trips") or 0),
                safety_score=safety,
                risk_score=risk,
            )
        )
    if not drivers:  # неизвестный ТС / нет driver_trips → синтетический main (§61).
        drv = enrichment.driver_for(db, plate)
        drivers.append(
            DriverRef(
                driver_id=drv["driver_id"],
                driver_name=drv["driver"],
                role="main",
                trips=trips_total,
                safety_score=safety,
                risk_score=risk,
            )
        )

    return VehicleReport(
        plate=plate,
        vehicle_model=model,
        risk_score=risk,
        cameras=_vehicle_cameras(db, plate),
        drivers=drivers,
        period=_period(summaries, period_days),
        period_alarms=[_violation_row(s) for s in summaries],
        mileage_km=mileage,
        trips=trips_total,
    )


# ---------------------------------------------------------------------------
# NLU-запрос (§7.4): реальный nlu_service.parse → ReportQuery → отчёт.
# ---------------------------------------------------------------------------


def _empty_driver_report(driver_name: str, period_days: int) -> DriverReport:
    """Пустой driver-отчёт для нерезолвенного ФИО (§61/§62): нулевые KPI, не падать."""
    report = DriverReport(
        driver=DriverRef(
            driver_id="—",
            driver_name=driver_name,
            role="main",
            trips=0,
            safety_score=100,
            risk_score=0,
        ),
        vehicle_plate="",
        vehicle_model="—",
        period=ReportPeriod(**{"from": "", "to": "", "days": period_days}),
        mileage_km=0.0,
        trips=0,
        kpi=ReportKPI(total=0, video_da=0, telematics=0, gross=0),
        disciplinary_warning=False,  # safety_score=100 → дисциплина не назначается.
        violations=[],
    )
    report.narrative = narrative_service.narrate(report)  # b22: «нет нарушений за период».
    return report


def report_for_query(
    db: duckdb.DuckDBPyConnection, q: ReportQuery
) -> DriverReport | FleetReport:
    """ReportQuery → отчёт. kind=driver: plate напрямую или резолв ФИО→plate;
    ФИО без совпадения → пустой driver-отчёт (§62). kind=fleet: сводка по парку.
    """
    if q.kind == "driver":
        plate = q.plate
        if not plate and q.driver_name:
            plate = _plate_for_driver_name(db, q.driver_name)
        if plate:
            return driver_report(db, plate.upper().replace(" ", ""), q.period_days)
        if q.driver_name:  # ФИО не резолвится в ТС → пустой driver-отчёт, не fleet.
            return _empty_driver_report(q.driver_name, q.period_days)
    return fleet_report(db, q.period_days, q.view or "drivers")


def query(
    db: duckdb.DuckDBPyConnection, text: str, period_days: int | None = None
) -> dict[str, Any]:
    """POST /api/reports/query (§7.4): текст → NLU (b9) → отчёт.

    Возвращает обёртку `{"query": ReportQuery, "report": DriverReport|FleetReport}`.
    Без ключа Groq nlu_service детерминированно уходит в regex (Check b10).
    """
    q = nlu_service.parse(text)
    if period_days is not None:  # явный период из API перекрывает распознанный.
        q = q.model_copy(update={"period_days": period_days})
    report = report_for_query(db, q)
    return {"query": q, "report": report}


def _plate_for_driver_name(
    db: duckdb.DuckDBPyConnection, name: str
) -> str | None:
    """ФИО → vehicle_plate через driver_reference (фамилия с учётом падежей).

    Детерминированный выбор при неоднозначности — первый по "vehicle_plate".
    Фолбэк (нет таблицы) — обратный скан по enrichment.driver_for.
    """
    parts = name.strip().lower().split()
    if not parts:
        return None
    target = parts[0]
    if len(target) < 3:
        return None

    try:
        rows = db.execute(
            'SELECT "vehicle_plate","driver_name" FROM "driver_reference" '
            'ORDER BY "vehicle_plate"'
        ).fetchall()
        for plate, dname in rows:
            surname = (dname or "").lower().split()
            if not surname:
                continue
            short, long = sorted([target, surname[0]], key=len)
            if len(short) >= 4 and long.startswith(short):
                return plate
    except Exception:
        pass

    # Фолбэк: обратный поиск через синтетику driver_for (enrichment детерминирован).
    for vehicle in vehicles_repo.list_vehicles(db):
        plate = vehicle.get("unit_state_number") or ""
        if not plate:
            continue
        surname = enrichment.driver_for(db, plate)["driver"].lower().split()
        if surname:
            short, long = sorted([target, surname[0]], key=len)
            if len(short) >= 4 and long.startswith(short):
                return plate
    return None
