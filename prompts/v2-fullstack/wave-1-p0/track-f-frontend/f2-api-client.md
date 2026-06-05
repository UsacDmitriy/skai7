# f2 · Типизированный API-клиент

> Трек **Frontend**. Против `00-CONTRACT.md` §3 + §7.4/§7.5 (эндпоинты + схемы). **Владеет:**
> **Модель:** 🔵 Sonnet — детерминированная логика/вёрстка против контракта; гейт = секция Check.
> `web/src/api/client.ts`, `web/src/api/types.ts`. **Единственный владелец** этих файлов — все типы и
> client-методы (P0 + P1/P2) определяются здесь; f7–f13 их только **используют**, НЕ дописывают. Кодит против контракта.

## Цель

TypeScript-типы, точно повторяющие Pydantic-схемы контракта, и тонкий fetch-клиент к FastAPI.
Базовый URL — `/api` (через Vite proxy, его настроит x2). Возможность подмены на фикстуры f3.

## Задачи

1. `web/src/api/types.ts` — типы **пополю по §3.1 + §7.5** (полный набор full-scope):
   - P0: `Severity`, `Source`, `Status`, `Camera` (`hasVideo`, `offline_from/to`), `TelemetryPoint`,
     `IncidentSummary`, `IncidentDetail` (с `confidence`, `event_version`, `driver_region/department/safety_score`,
     `sensor_active_after_sec`, `cam_extra[]`), `VehicleSummary`, `Action`.
   - §7.5: `ReportQuery {kind,plate?,driver_name?,period_days?,view?}`, `ReportKPI`, `ReportPeriod`,
     `ViolationRow`, `DriverRef`, `DriverReport`, `FleetReport`, `VehicleReport`, `Ticket`, `DispatchAlert`,
     `TripDossier`, `RebRecovery`, `SabotageEvent`.
2. `web/src/api/client.ts`:
   - `const BASE = import.meta.env.VITE_API_BASE ?? '/api'`.
   - Хелпер `request<T>(path, init?)` с обработкой ошибок (бросать на `!res.ok`, парсить `{detail}`).
   - Методы P0: `listIncidents(filters?)`, `getIncident(id)`, `getTelemetry(id)`,
     `videoUrl(id, channel) → string`, `listVehicles()`, `postAction(action)`.
   - Методы §7.4 (full-scope): `transcribe(blob, lang?) → {text,lang,confidence}` (multipart),
     `queryReport(text) → {query, report}`, `driverReport(plate)`, `fleetReport(view?)`,
     `getVehicleReport(plate)`, `getTickets()`, `getAlert(id)`, `getTrip(id)`, `getReb(id)`, `getSabotage()`.
   - Флаг `USE_FIXTURES` (env `VITE_USE_FIXTURES`): если true — методы возвращают данные из `./fixtures` (f3) вместо fetch.

## Check

- `npm run typecheck` проходит; типы совпадают с контрактом §3.1 + §7.5.
- Все client-методы P0 и §7.4 присутствуют (f7–f13 ничего не дописывают в `client.ts`/`types.ts`).
- При `VITE_USE_FIXTURES=true` методы отдают фикстуры без сети; при выключенном — ходят на `/api/...`.
