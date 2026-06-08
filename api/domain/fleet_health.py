"""Pydantic-схемы хаба «Здоровье парка» (контракт §9.2, аддендум волны 3).

Сосед `entities.py`. Здесь — топливный домен (w3-6): сверка бак-сенсор ЗИС vs
топливные карты. Sensors/navigation-схемы (w3-7/w3-8) добавляются сюда же.
Провенанс колонок — §9.2 (источник: `fuel__fuel_vehicles` / `fuel__fuel_summary` /
`fuel__fuel_reconciliation` / `fuel__fuel_events`). Топливо — изолированный остров
(§9.0: пересечение с видеопарком = 0), к инцидентам/водителям/РЭБ не линкуется.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

# Статус сверки ЗИС vs карта (худший по ТС): matched < review < missing_sensor_event.
FuelReconStatus = Literal["matched", "review", "missing_sensor_event"]


class FuelVehicleSummary(BaseModel):
    """Строка топливного ростера (§9.2). Headline KPI — `volume_delta_zis_minus_card_l`."""

    vehicle_id: str
    model: str
    vin: str
    fuel_volume_zis_l: float
    fuel_volume_card_l: float
    volume_delta_zis_minus_card_l: float  # headline KPI: бак-сенсор ЗИС − карты
    refuel_count_zis: int
    transaction_count_card: int
    period_start: str
    period_end: str
    recon_status: FuelReconStatus  # худший статус сверки по ТС


class FuelReconRow(BaseModel):
    """Строка сверки транзакция карты ↔ событие сенсора (§9.2). Поля nullable."""

    row_id: str
    transaction_ts: str | None = None
    event_ts: str | None = None
    transaction_volume_l: float | None = None
    sensor_volume_l: float | None = None
    volume_delta_l: float | None = None
    time_delta_min: float | None = None
    amount_rub: float | None = None
    status: str
    reason: str | None = None


class FuelEvent(BaseModel):
    """Топливное событие ЗИС (заправка/слив) (§9.2)."""

    event_id: str
    event_ts: str
    event_name: str
    volume_l: float
    before_l: float | None = None
    after_l: float | None = None
    lat: float | None = None
    lon: float | None = None
    address: str | None = None


class FuelSummary(BaseModel):
    """Агрегаты пробега/расхода ТС (§9.2, из `fuel__fuel_summary`)."""

    fuel_spent_l: float
    total_mileage_km: float
    average_consumption_l_per_100km: float
    average_speed_kmh: float
    fuelings_count: int
    defuelings_count: int


class FuelVehicleCard(FuelVehicleSummary):
    """Карточка топлива ТС (§9.2): summary + списки сверки и событий.

    `summary` = None для ТС без строки в `fuel__fuel_summary` (валидно, не ошибка);
    пустые `reconciliation`/`events` — тоже валидны (§9.5).
    """

    summary: FuelSummary | None = None
    reconciliation: list[FuelReconRow] = []
    events: list[FuelEvent] = []


# ───────────────────────────── sensors (w3-7) ──────────────────────────────
# Сенсорная диагностика, headline — расхождение пробега CAN(одометр) − GPS.
# Источник: `sensors__mileage_and_speed` / `online_snapshot` / `daily_mileage` /
# `engine_statistics` / `fuel_level_summary` / `sensor_catalog` (см. v_sensors).
# 959k `sensors__sensor_graph_points`/`graph_status` наружу НЕ отдаются (§9.3).

# online_status: «свежий валидный фикс» / «не было валидной навигации (NULL)» /
# «фикс устарел». Считается во view по timestamp_utc снапшота (§9.3, не Date.now()).
OnlineStatus = Literal["online", "stale", "offline"]


class SensorVehicleSummary(BaseModel):
    """Строка сводки сенсорной диагностики ТС (§9.2). 1 строка = 1 ТС (7 шт.)."""

    public_unit_id: str
    vehicle_label: str
    plate: str | None = None  # public_state_number из sensors_bv; null у несматченного ТС
    gps_total_distance_km: float
    # CAN-одометр и расхождение CAN−GPS — оба могут быть NULL («нет данных», не 0).
    distance_odometer_km: float | None = None
    distance_gap_odometer_minus_gps_km: float | None = None  # headline KPI домена
    max_speed_kmh: float
    average_speed_kmh: float
    satellite_amount: int
    online_status: OnlineStatus
    sensor_count: int


class SensorDailyPoint(BaseModel):
    """Точка спарклайна суточного пробега (§9.2) — ровно 7/ТС из `daily_mileage`."""

    date: str
    distance_km: float


class SensorEngine(BaseModel):
    """Статистика двигателя ТС (`sensors__engine_statistics`)."""

    first_ignition_on: str | None = None
    last_ignition_off: str | None = None
    ignition_duration: str | None = None
    idle_duration: str | None = None


class SensorFuelLevel(BaseModel):
    """Сводка уровня топлива по датчику (`sensors__fuel_level_summary`)."""

    first_fuel_level: float | None = None
    last_fuel_level: float | None = None
    delta_fuel_level: float | None = None


class SensorSnapshot(BaseModel):
    """Последний онлайн-снапшот ТС (`sensors__online_snapshot`)."""

    speed_kmh: float | None = None
    fuel_volume: float | None = None
    satellite_amount: int | None = None
    timestamp_utc: str | None = None
    last_valid_navigation_timestamp: str | None = None
    odometer_mileage: float | None = None
    longitude: float | None = None
    latitude: float | None = None


class SensorVehicleCard(SensorVehicleSummary):
    """Карточка сенсоров ТС (§9.2): сводка + динамика + под-блоки.

    `daily_mileage` — спарклайн из 7-точечного `daily_mileage` (НЕ graph_points).
    `engine`/`fuel_level`/`snapshot` — null, если у ТС нет соответствующей строки.
    """

    daily_mileage: list[SensorDailyPoint] = []
    engine: SensorEngine | None = None
    fuel_level: SensorFuelLevel | None = None
    snapshot: SensorSnapshot | None = None


# ──────────────────────────── navigation (w3-8) ─────────────────────────────
# Список проблемных треков навигации → вход в существующий /api/reb/{id} (§7.4, b12).
# Источник: `navigation__navigation_problem_vehicles` ⋈ агрегат
# `navigation__track_periods` (gap = period_type=3 = потеря GPS), view `v_nav_problem`.
# reb_link_id = public_unit_id (UUID есть в обеих таблицах); у unmatched-ТС — null.

# Статус матчинга навигационного лейбла с публичным справочником ТС.
NavMatchStatus = Literal["matched", "unmatched"]


class NavProblemVehicle(BaseModel):
    """Строка списка проблемных треков (§9.2) → deep-view `/api/reb/{reb_link_id}`.

    5 matched + 1 unmatched ТС. У unmatched `public_unit_id`/`plate`/`reb_link_id`
    = null (строка не кликабельна в РЭБ), но `problem_description` живой (§9.5).
    """

    public_unit_id: str | None = None
    plate: str | None = None  # public_state_number (чистый); null у unmatched
    vehicle_label: str | None = None  # source_vehicle («грязный» лейбл, есть всегда)
    brand: str | None = None  # public_brand
    problem_description: str  # человеческая «история» проблемы (free text)
    match_status: NavMatchStatus
    gap_count: int  # число разрывов GPS (period_type=3)
    total_periods: int
    total_gap_duration_sec: int
    reb_link_id: str | None = None  # = public_unit_id; null у unmatched
    in_video_fleet: bool  # plate (норм.) ∈ v_incidents.vehicle_plate
