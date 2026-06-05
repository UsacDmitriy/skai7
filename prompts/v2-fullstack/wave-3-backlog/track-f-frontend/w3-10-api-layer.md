# W3-10 · API-слой fleet-health (types + client + fixtures) — f2/f3

> Волна 3 · бэклог. Трек **Frontend** (владелец f2/f3 — API-клиент и фикстуры). Против `00-CONTRACT.md` **§9** (§9.1/§9.2/§9.4).
> **Модель:** 🔵 Sonnet — детерминированная типизация против контракта; гейт = секция Check.
> **Владеет:** `web/src/api/types.ts`, `web/src/api/client.ts`, `web/src/api/fixtures.ts` (строго **аддитивно**).
> **Граница владения:** этот промпт — единственный, кто правит `api/*` (избегаем кросс-трекового конфликта
> мерджа); экраны (w3-11) и врезки (w3-12) только **используют** клиент. **Не блокирует** P0/P1/P2.

## Цель

Дать экранам «Здоровья парка» (w3-11) типобезопасный клиент к новым доменам fuel/sensors/navigation +
`/api/fleet-health`, с обязательным режимом фикстур `VITE_USE_FIXTURES=true` (демо без бэка).

## Что сделать

1. **`web/src/api/types.ts`** (аддитивно) — интерфейсы по §9.2: `FuelVehicleSummary`, `FuelReconRow`,
   `FuelEvent`, `FuelVehicleCard`, `SensorVehicleSummary`, `SensorDailyPoint`, `SensorVehicleCard`,
   `NavProblemVehicle`, `FleetHealthRow`, `FleetHealthResponse`. (Типы `RebRecovery` уже есть.)
2. **`web/src/api/client.ts`** — методы с веткой `VITE_USE_FIXTURES` (как у существующих, ~стр.39–40/84–85):
   `listFuel()`, `getFuel(plate)`, `listSensors()`, `getSensors(plate)`, `listNavProblems()`,
   `getFleetHealth()`. **Починить пропущенную fixtures-ветку у `getReb(id)` и `getVehicleReport(plate)`**
   (сейчас в фикстур-режиме они идут в сеть → демо-сирота). Базовый префикс/проксирование — без изменений.
3. **`web/src/api/fixtures.ts`** (аддитивно) — экспортируемые константы и lookup'ы из **2–3 реальных строк**
   на домен (под `fixtures.ts:311–690` стиль `INCIDENT_DETAILS`/`getFixtureIncident`):
   - `FUEL_VEHICLES`, `FUEL_CARDS` + `getFixtureFuel(plate)` (напр. `А144ЕВ193`),
   - `SENSOR_VEHICLES`, `SENSOR_CARDS` + `getFixtureSensor(plate)` (напр. `Т671КР31` с разрывом 540 км),
   - `NAV_PROBLEMS` (вкл. `О802УЕ198`, `in_video_fleet=true`),
   - `REB_RECOVERY` + `getFixtureReb(id)` (закрыть дыру из п.2),
   - `FLEET_HEALTH` (объединение с «—»-доменами и баннером покрытия 10/7/5/2).
   Значения — реалистичные (числа сходятся), без `Date.now()`.

## Check

- `npm run typecheck` зелёный; новые типы экспортируются и совпадают с §9.2 (поля/типы 1:1).
- На живом API: `client.listFuel()`/`listSensors()`/`listNavProblems()`/`getFleetHealth()` отдают данные;
  на фикстурах (`VITE_USE_FIXTURES=true`) — те же формы из `fixtures.ts`, **без** сетевых запросов.
- `getReb('<id>')` и `getVehicleReport('<plate>')` в фикстур-режиме возвращают фикстуру (не падают/не идут в сеть).
- `fixtures.ts` содержит ≥2 реальных госномера на домен; `FLEET_HEALTH` имеет строки с `null`-доменами.

## Коммит (обязательно)

```bash
git add -A && git commit -m "w3-10: API-слой fleet-health (types/client/fixtures) + fix getReb/getVehicleReport фикстуры"
```
