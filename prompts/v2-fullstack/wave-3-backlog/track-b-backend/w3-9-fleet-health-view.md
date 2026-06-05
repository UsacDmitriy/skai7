# W3-9 · View «Здоровье парка» (объединение ТС по доменам) + эндпоинт

> Волна 3 · бэклог. Трек **Backend/Data**. Против `00-CONTRACT.md` **§9** (§9.0/§9.3/§9.6).
> **Модель:** 🔴 Opus — самый рискованный кросс-доменный join (disjoint-популяции, нормализация
> госномера, разные ключи). **Владеет:** `api/sql/28_v_fleet_health.sql`,
> `api/services/fleet_health_service.py`, роутер `api/routers/fleet_health.py` (`GET /api/fleet-health`).
> **Зависит от** w3-6 (`v_fuel`), w3-7 (`v_sensors`), w3-8 (`v_nav_problem`). **Не блокирует** P0/P1/P2.

## Контекст (disjoint-популяции — §9.0)

Популяции ТС почти не пересекаются: `fuel(10) ∩ video = 0`, `sensors(7)`, `navigation(5)`,
**объединение = 17 ТС, из них 2 в видеопарке**. Хаб «Здоровье парка» строится на **объединении** и честно
показывает «—» там, где у ТС нет домена. Ключи разные: sensors/navigation резолвятся через
`reference__vehicle_matches` (`public_state_number`), **топливо — по собственному `fuel__fuel_vehicles.vehicle_id`**
(в `reference__vehicle_matches` топлива нет). Объединение — по **нормализованному** госномеру (strip пробелов/регистра).

## Что сделать

1. **View `api/sql/28_v_fleet_health.sql`** (`DROP VIEW IF EXISTS "v_fleet_health"`): `FULL`/`UNION`-объединение
   нормализованных госномеров из `v_fuel` ∪ `v_sensors` ∪ `v_nav_problem`, со столбцами-флагами наличия
   (`has_fuel`/`has_sensors`/`has_nav`) и заголовочными KPI каждого домена (топливо Δ, CAN−GPS, online_status,
   gap_count, `reb_link_id`), плюс `in_video_fleet`. Нормализация — единая SQL-функция/выражение
   (`regexp_replace` пробелов + `upper`), применяется ко всем источникам одинаково.
2. **Сервис `api/services/fleet_health_service.py`**: `list_fleet_health(db) -> list[FleetHealthRow]`
   из `v_fleet_health`; плюс `coverage()` → `{fuel:10, sensors:7, navigation:5, in_video_fleet:2}` для баннера.
3. **Pydantic-схема** `FleetHealthRow` + `FleetHealthResponse {coverage, rows}` — в `api/domain/fleet_health.py`.
4. **Роутер `api/routers/fleet_health.py`**: `GET /api/fleet-health` → `FleetHealthResponse`.

## Check

- `make db`; `SELECT count(*) FROM v_fleet_health` = **17** (объединение без дублей по норм. госномеру).
- `curl -s :8000/api/fleet-health | jq '.coverage'` = `{fuel:10, sensors:7, navigation:5, in_video_fleet:2}`.
- Ровно **2** строки с `in_video_fleet=true` (`О802УЕ198`, `С725АТ159`).
- У ТС без домена — соответствующий KPI `null` (фронт рендерит «—», не ошибка); ни один `reb_link_id` не «грязный лейбл».
- Повторный `make db` детерминирован (тот же набор 17 строк, тот же порядок при стабильной сортировке).

## Коммит (обязательно)

```bash
git add -A && git commit -m "w3-9: v_fleet_health (объединение 17 ТС) + /api/fleet-health"
```
