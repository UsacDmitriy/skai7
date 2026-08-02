# f3 · Фикстуры (фронт работает до бэка)

> Трек **Frontend**. Против `00-CONTRACT.md` §3.1. **Владеет:** `web/src/api/fixtures.ts`.
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — механическая транскрипция против точной спеки; гейт ловит ошибку.
> Источник эталонной формы — `data/mock/incidents.py` (перенести в TS, сохранив поля).

## Цель

Статичные данные, повторяющие контракт ответов, чтобы экраны f4 разрабатывались и демонстрировались
без запущенного FastAPI (через флаг `VITE_USE_FIXTURES`).

## Задачи

1. `web/src/api/fixtures.ts` — экспорт типизированных констант (типы из f2 `types.ts`):
   - `INCIDENTS: IncidentSummary[]` — ≥5 записей (перенести из `data/mock/incidents.py`: inc-001…inc-005, поля по §3.1; учесть кейсы «есть видео»/«нет видео»).
   - `INCIDENT_DETAILS: Record<string, IncidentDetail>` — детали по id с `cameras[]`, `telemetry[]`, `evidence_summary` (взять telemetry прямо из `data/mock/incidents.py`, включая кейс «датчик удара» 54→0).
   - `VEHICLES: VehicleSummary[]`, `DRIVER_REPORT`, `FLEET_REPORT` — минимально валидные.
2. Хелперы `getFixtureIncident(id)`, `listFixtureIncidents(filters?)` — повторяют сигнатуры клиента f2.

## Требования

- Формы **строго** соответствуют типам f2 (которые = §3.1). Любое расхождение ломает экраны — недопустимо.
- Severity-значения: `critical|high|medium|low` (не `warning`/`ok` — это только токены дизайна).

## Check

- `npm run typecheck` проходит; `INCIDENTS` типизирован как `IncidentSummary[]`.
- При `VITE_USE_FIXTURES=true` экран «Карточка инцидента» (f4) рендерится на фикстурах.
