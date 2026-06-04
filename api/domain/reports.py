"""Схемы домена reports (контракт §7.5, полная форма).

`ReportQuery` — новая форма `{kind, plate?, driver_name?, period_days, view?}`,
заменяет старую `{text}` из §3.3 (её НЕ создавать).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from api.domain.common import Severity, Source
from api.domain.incidents import Camera


class ReportQuery(BaseModel):
    """Разобранный NLU-запрос (§7.3/§7.5). Результат `nlu_service.parse`."""

    kind: Literal["driver", "fleet"]
    plate: str | None = None
    driver_name: str | None = None
    period_days: int = 3
    view: Literal["drivers", "vehicles"] | None = None


class ReportKPI(BaseModel):
    """Сводка периода (§7.5). total/ВА видео-детекции/телематика/грубых."""

    total: int
    video_da: int
    telematics: int
    gross: int


class ReportPeriod(BaseModel):
    """Период отчёта (§7.5). `from` — зарезервированное слово Python → alias."""

    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(alias="from")
    to: str
    days: int


class ViolationRow(BaseModel):
    """Строка нарушения в отчёте (§7.5). Клик → IncidentDetail (killer-feature)."""

    id: str
    ts: str
    alarm_code: str
    alarm_label_ru: str
    source: Source
    severity: Severity
    is_gross: bool


class DriverRef(BaseModel):
    """Ссылка на водителя (§7.5)."""

    driver_id: str
    driver_name: str
    role: Literal["main", "secondary"] = "main"
    trips: int
    safety_score: int
    risk_score: int


class DriverReport(BaseModel):
    """GET /api/reports/driver/{plate} (§7.5, идея #2 В-1)."""

    driver: DriverRef
    vehicle_plate: str
    vehicle_model: str
    period: ReportPeriod
    mileage_km: float
    trips: int
    kpi: ReportKPI
    disciplinary_warning: bool  # порог: gross>=3 ИЛИ safety_score<60
    violations: list[ViolationRow] = []


class FleetByDriver(BaseModel):
    """Строка агрегата по водителю (§7.5 FleetReport.by_drivers)."""

    driver: DriverRef
    vehicle_plate: str
    vehicle_model: str
    mileage_km: float
    risk_score: int
    gross: int
    total: int


class FleetByVehicle(BaseModel):
    """Строка агрегата по ТС (§7.5 FleetReport.by_vehicles)."""

    plate: str
    vehicle_model: str
    main_driver: str
    mileage_km: float
    risk_score: int
    gross: int
    total: int
    cameras_ok: str  # «2/3»


class FleetReport(BaseModel):
    """GET /api/reports/fleet (§7.5, идея #2 В-2)."""

    period: ReportPeriod
    kpi: ReportKPI
    vehicles_count: int
    by_drivers: list[FleetByDriver] = []
    by_vehicles: list[FleetByVehicle] = []


class VehicleReport(BaseModel):
    """GET /api/reports/vehicle/{plate} (§7.5, идея #2 В-2/ТС, #10). len(cameras)=3."""

    plate: str
    vehicle_model: str
    risk_score: int
    cameras: list[Camera]  # len == 3 (ADAS/DMS/СНЗ)
    drivers: list[DriverRef] = []
    period: ReportPeriod
    period_alarms: list[ViolationRow] = []
    mileage_km: float
    trips: int
