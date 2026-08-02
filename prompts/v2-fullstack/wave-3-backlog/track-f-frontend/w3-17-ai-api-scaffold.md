# W3-17 · AI API-каркас фронта: типы + клиент-заглушки + фикстуры (подготовка Волны 4)

> Волна 3 · бэклог (**подготовка под Волну 4**). Трек **Frontend** (владелец f2/f3). Против `00-CONTRACT.md`
> §8.4/§8.6/§8.7/§8.8. **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — типизация против контракта; гейт = typecheck.
> **Владеет:** `web/src/api/types.ts`, `web/src/api/client.ts`, `web/src/api/fixtures.ts` (строго **аддитивно**).
> **Граница:** единственный prep-промпт, правящий `api/*` фронта (как `w3-10`). Разблокирует **f15–f21** (Волна 4) —
> они только **используют** клиент/типы. **Не блокирует** P0/P1/P2.

## Цель

Дать всем AI-экранам Волны 4 типобезопасный клиент + фикстуры, чтобы f15–f21 были **аддитивными** и
работали в режиме `VITE_USE_FIXTURES=true` (демо без бэка) сразу.

## Что сделать

1. **`web/src/api/types.ts`** (аддитивно, 1:1 контракту §8.4/§8.6/§8.7/§8.8): `SceneContext`,
   `WeatherCrossCheck`, `RiskForecast` (+`narrative?`), `RiskZone`, `FatigueChain`, `CopilotMessage`,
   `AiFeatureState`, `AiMetrics`, `DataQuality`, `RiskBreakdown`. В `DriverReport`/`FleetReport` добавить `narrative?: string`.
2. **`web/src/api/client.ts`** — методы-заглушки с веткой `VITE_USE_FIXTURES` (как существующие): `getScene(id)`,
   `getForecast(plate)`, `getZones(params)`, `getFatigue(plate)`, `copilotChat(text)`, `getAiMetrics()`,
   `getDataQuality()`, `getRiskBreakdown(id)`. На живом API — обычный fetch; в фикстур-режиме — возврат из `fixtures.ts`.
3. **`web/src/api/fixtures.ts`** (аддитивно, **детерминированные** значения по §8.0): `SCENE`, `WEATHER`
   (`weather="unknown"`, day/night из часа), `FORECAST` (наивный коридор, `anomaly=false`,
   `anomaly_reason="недостаточно истории"`, `narrative`), `ZONES` (1–2 кластера incident+reb),
   `FATIGUE` (пустой/одиночный «ранний признак»), `COPILOT` (RU/EN примеры), `AI_METRICS`, `DATA_QUALITY`
   (реальные доли: `camera_offline≈0`, `missing_gps≈0.06`, `incidents_with_video=1.0`), `RISK_BREAKDOWN`
   (вклады суммируются в `risk_score`). Без `Date.now()`/`random`.

## Check

- `npm run typecheck` зелёный; новые типы экспортируются и совпадают с §8.4/§8.7/§8.8 (поля/типы 1:1).
- В фикстур-режиме `getScene/getForecast/getZones/getFatigue/copilotChat/getAiMetrics/getDataQuality/getRiskBreakdown`
  возвращают валидные объекты **без сети**.
- `RISK_BREAKDOWN`: сумма вкладов = `total_risk_score`; `DATA_QUALITY.*_ratio ∈ [0,1]`.
- Поле `narrative?` присутствует в типах `DriverReport`/`FleetReport`/`RiskForecast`.

## Коммит (обязательно)

```bash
git add -A && git commit -m "w3-17: AI API-каркас фронта (types/client/fixtures §8.4/8.7/8.8)"
```
