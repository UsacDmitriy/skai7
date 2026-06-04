# f2 · Типизированный API-клиент

> Трек **Frontend**. Против `00-CONTRACT.md` §3 (эндпоинты + схемы). **Владеет:**
> `web/src/api/client.ts`, `web/src/api/types.ts`. Кодит против контракта — не ждёт рантайма бэка.

## Цель

TypeScript-типы, точно повторяющие Pydantic-схемы контракта, и тонкий fetch-клиент к FastAPI.
Базовый URL — `/api` (через Vite proxy, его настроит x2). Возможность подмены на фикстуры f3.

## Задачи

1. `web/src/api/types.ts` — типы **пополю по §3.1**:
   `Severity`, `Source`, `Status`, `Camera` (`hasVideo`), `TelemetryPoint`, `IncidentSummary`, `IncidentDetail`,
   `VehicleSummary`, `DriverReport`, `FleetReport`, `ReportQuery`, `Action`.
2. `web/src/api/client.ts`:
   - `const BASE = import.meta.env.VITE_API_BASE ?? '/api'`.
   - Хелпер `request<T>(path, init?)` с обработкой ошибок (бросать на `!res.ok`, парсить `{detail}`).
   - Методы:
     - `listIncidents(filters?) → IncidentSummary[]` (query-строка из filters).
     - `getIncident(id) → IncidentDetail`.
     - `getTelemetry(id) → TelemetryPoint[]`.
     - `videoUrl(id, channel) → string` (просто URL, для `<video src>`).
     - `listVehicles() → VehicleSummary[]`.
     - `driverReport(plate)`, `fleetReport()`, `queryReport(text)`.
     - `postAction(action: Action) → Action`.
   - Флаг `USE_FIXTURES` (env `VITE_USE_FIXTURES`): если true — методы возвращают данные из `./fixtures` (f3) вместо fetch. Так фронт работает до готовности бэка.

## Check

- `npm run typecheck` проходит; типы совпадают с контрактом §3.1.
- При `VITE_USE_FIXTURES=true` `listIncidents()`/`getIncident()` отдают фикстуры без сети.
- При выключенном флаге методы реально ходят на `/api/...`.
