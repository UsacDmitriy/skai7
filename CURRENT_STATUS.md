# CURRENT_STATUS — реализовано vs план

> ⚠️ **Не редактировать вручную.** Источник — `scripts/gen_status.py` (00-CONTRACT §8.9).
> Перечень роутеров/таблиц берётся из факта (`api/routers`, `api/sql`), не из README.
> Статус: ✅ реализовано · 🟡 заглушка (501)/в работе · ⬜ план (файла нет).
> Скелет (w3-19); t5 доводит до сверки с прогоном тестов (pytest/vitest).

## Сводка

- Роутеры (`api/routers`): **12** (✅ 9 · 🟡 3)
- SQL-объекты (`api/sql`): **6** (✅ 6)

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

## Волна 3 · Тёмные данные — fuel · sensors · navigation (подъём из 501)

- 🟡 `fuel` (`/api/fuel`) — заглушка 501
- 🟡 `navigation` (`/api/navigation`) — заглушка 501
- 🟡 `sensors` (`/api/sensors`) — заглушка 501

## Волна 4 · AI Ops & Trust (каркас w3-16…19; логика — Волна 4.3)

- ⬜ `metrics` — роутер (план, файла нет)
- ⬜ `ai_metric_events` — план, объекта нет

## Инвентарь (факт с диска)

### Роутеры (`api/routers/*.py`)

- ✅ `actions` (`/api/actions`)
- ✅ `alerts` (`/api/alerts`)
- 🟡 `fuel` (`/api/fuel`) — заглушка 501
- ✅ `incidents` (`/api/incidents`)
- 🟡 `navigation` (`/api/navigation`) — заглушка 501
- ✅ `reb` (`/api`)
- ✅ `reports` (`/api/reports`)
- ✅ `sabotage` (`/api`)
- 🟡 `sensors` (`/api/sensors`) — заглушка 501
- ✅ `tickets` (`/api/tickets`)
- ✅ `trips` (`/api/trips`)
- ✅ `vehicles` (`/api/vehicles`)

### SQL-объекты (`api/sql/*.sql`)

- ✅ `v_driver_report`
- ✅ `v_fleet`
- ✅ `v_incidents`
- ✅ `v_reb`
- ✅ `v_sabotage`
- ✅ `v_vehicle`
