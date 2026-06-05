# W3-7 · Домен sensors (диагностика, CAN−GPS разрыв) — снять 501-стаб

> Волна 3 · бэклог. Трек **Backend/Data**. Против `00-CONTRACT.md` **§9** (§9.1/§9.2/§9.3/§9.5).
> **Модель:** 🔵 Sonnet — детерминированная логика против контракта; гейт = секция Check.
> **Владеет:** `api/sql/26_v_sensors.sql`, `api/services/sensors_service.py`, роутер
> `api/routers/sensors.py` (сейчас → `501`). **Паттерн:** как `api/services/reb_service.py`. **Не блокирует** P0/P1/P2.

## Контекст (тёмные данные)

В БД лежат `sensors__mileage_and_speed` (7 ТС), `sensors__online_snapshot` (7), `sensors__daily_mileage` (49),
`sensors__engine_statistics` (7), `sensors__fuel_level_summary` (7), `sensors__sensor_catalog` (627),
а также **`sensors__sensor_graph_points` (959 782 строк)** и `sensors__sensor_graph_status` (490). Роутер
[`api/routers/sensors.py`](../../../../api/routers/sensors.py) отдаёт `501`. Содержательный сигнал —
**расхождение пробега CAN(одометр) − GPS** (`distance_gap_odometer_minus_gps_km`, диапазон −290…+540 км).

> ⚠️ **959k `graph_points` и `graph_status` НЕ отдавать наружу** (§9.3, §1: большие таблицы не держим
> в памяти приложения). Сводки — из маленьких per-ТС таблиц; динамика — спарклайн из 7-точечного `daily_mileage`.

## Что сделать

1. **View `api/sql/26_v_sensors.sql`** (`DROP VIEW IF EXISTS "v_sensors"`): `sensors__mileage_and_speed`
   ⋈ `sensors__online_snapshot` ⋈ `count(sensors__sensor_catalog)` по `public_unit_id`, LEFT JOIN
   `reference__vehicle_matches` (`source_list='sensors_bv'`) → `plate` (`public_state_number`). Колонки —
   под `SensorVehicleSummary` (§9.2). `online_status`: сравнение `last_valid_navigation_timestamp` с
   `timestamp_utc` строки (**не `Date.now()`**); `NULL` → `stale`.
2. **Сервис `api/services/sensors_service.py`**:
   - `list_sensors(db) -> list[SensorVehicleSummary]` (7 строк).
   - `get_sensors(db, plate) -> SensorVehicleCard | None` — `daily_mileage` (7 точек), `engine`,
     `fuel_level`, `snapshot` по `public_unit_id`; матч по нормализованному госномеру **или** UUID.
3. **Pydantic-схемы** — в `api/domain/fleet_health.py`: `SensorVehicleSummary`, `SensorDailyPoint`,
   `SensorVehicleCard` строго по §9.2.
4. **Роутер `api/routers/sensors.py`** — заменить стабы: `GET /api/sensors` → `SensorVehicleSummary[]`,
   `GET /api/sensors/{plate}` → `SensorVehicleCard` (404 при `None`).

## Check

- `make db`; `SELECT count(*) FROM v_sensors` = **7**.
- `curl -s :8000/api/sensors | jq length` = **7**; элемент содержит `distance_gap_odometer_minus_gps_km`, `online_status`.
- Ровно **2 из 7** ТС с `last_valid_navigation_timestamp=NULL` → `online_status="stale"` (не падение).
- `curl -s :8000/api/sensors/<plate> | jq '.daily_mileage|length'` = **7**; ответ **не содержит** `graph_points`/`graph_status`.
- ТС без CAN−GPS разрыва → `distance_gap…=null` (ячейка «нет данных», не 0).
- Неизвестный госномер → **404**; `grep -L 501 api/routers/sensors.py` (стаб снят).

## Коммит (обязательно)

```bash
git add -A && git commit -m "w3-7: домен sensors (v_sensors + sensors_service + роутер), снят 501"
```
