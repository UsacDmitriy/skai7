# CURRENT_STATUS — реализовано vs план

> ⚠️ **Не редактировать вручную.** Источник — `scripts/gen_status.py` (00-CONTRACT §8.9).
> Перечень роутеров/таблиц берётся из факта (`api/routers`, `api/sql`), не из README.
> Статус: ✅ реализовано (тесты зелёные) · 🟡 заглушка (501)/в работе · ❌ тесты падают · ⬜ план (файла нет).
> «✅ требует зелёных тестов»: сверка с последним прогоном pytest/vitest (`reports/`).

## Тесты (последний прогон)

- Итог: **✅ всё зелёное** — 679 passed · 0 failed · 0 errors · 2 skipped (всего 681).
- Источник: `reports/pytest-junit.xml` (pytest) + `reports/vitest-junit.xml` (vitest), последний прогон.

## Сводка

- Роутеры (`api/routers`): **18** (✅ 18 · 🟡 0 · ❌ 0)
- SQL-объекты (`api/sql`): **13** (✅ 13 · ❌ 0)

## P0 · Ядро MVP — инциденты · отчёты · парк

- ✅ `actions` (`/api/actions`)
- ✅ `incidents` (`/api/incidents`)
- ✅ `reports` (`/api/reports`)
- ✅ `vehicles` (`/api/vehicles`)
- ✅ `v_driver_report`
- ✅ `v_fleet`
- ✅ `v_incidents`
- ✅ `v_vehicle`

## P1 · Мониторинг и реакция — алерты · заявки · рейсы

- ✅ `alerts` (`/api/alerts`)
- ✅ `tickets` (`/api/tickets`)
- ✅ `trips` (`/api/trips`)

## P2 · РЭБ и саботаж

- ✅ `reb` (`/api`)
- ✅ `sabotage` (`/api`)
- ✅ `v_reb`
- ✅ `v_sabotage`

## Волна 3 · Тёмные данные — fuel · sensors · navigation · здоровье парка

- ✅ `fleet_health` (`/api/fleet-health`)
- ✅ `fuel` (`/api/fuel`)
- ✅ `navigation` (`/api/navigation`)
- ✅ `sensors` (`/api/sensors`)
- ✅ `v_fleet_health`
- ✅ `v_fuel`
- ✅ `v_nav_problem`
- ✅ `v_sensors`

## Волна 4 · AI Ops & Trust — копилот · прогноз · усталость · сцена · риск-зоны

- ✅ `copilot` (`/api/copilot`)
- ✅ `fatigue` (`/api/fatigue`)
- ✅ `forecast` (`/api/reports`)
- ✅ `scene` (`/api/incidents`)
- ✅ `zones` (`/api/zones`)
- ✅ `ai_metric_events`
- ✅ `incident_scene`
- ✅ `incident_weather`

## Инвентарь (факт с диска)

### Роутеры (`api/routers/*.py`)

- ✅ `actions` (`/api/actions`)
- ✅ `alerts` (`/api/alerts`)
- ✅ `copilot` (`/api/copilot`)
- ✅ `fatigue` (`/api/fatigue`)
- ✅ `fleet_health` (`/api/fleet-health`)
- ✅ `forecast` (`/api/reports`)
- ✅ `fuel` (`/api/fuel`)
- ✅ `incidents` (`/api/incidents`)
- ✅ `navigation` (`/api/navigation`)
- ✅ `reb` (`/api`)
- ✅ `reports` (`/api/reports`)
- ✅ `sabotage` (`/api`)
- ✅ `scene` (`/api/incidents`)
- ✅ `sensors` (`/api/sensors`)
- ✅ `tickets` (`/api/tickets`)
- ✅ `trips` (`/api/trips`)
- ✅ `vehicles` (`/api/vehicles`)
- ✅ `zones` (`/api/zones`)

### SQL-объекты (`api/sql/*.sql`)

- ✅ `ai_metric_events`
- ✅ `incident_scene`
- ✅ `incident_weather`
- ✅ `v_driver_report`
- ✅ `v_fleet`
- ✅ `v_fleet_health`
- ✅ `v_fuel`
- ✅ `v_incidents`
- ✅ `v_nav_problem`
- ✅ `v_reb`
- ✅ `v_sabotage`
- ✅ `v_sensors`
- ✅ `v_vehicle`
