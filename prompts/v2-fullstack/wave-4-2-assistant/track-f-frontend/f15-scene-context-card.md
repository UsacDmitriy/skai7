# f15 · Scene context на карточке (идея #11)

> Трек **Frontend**. Против `00-CONTRACT.md` §8.3/§8.4. **Владеет:** **аддитивная** правка
> `web/src/pages/IncidentCard.tsx` + **аддитивная** правка фикстур `web/src/api/fixtures.ts`
> (id-aware `getFixtureScene` + 1 кейс расхождения — иначе бейдж не на чем показать). Использует
> готовые d7 (`SceneContextChip`/`DiscrepancyBadge`) и **существующий** клиент `getScene`.
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — вёрстка/состояния против контракта; гейт = typecheck.
> **Волна 4.2**, окно 2 (web). Зависит от: d7, `GET /api/incidents/{id}/scene`, фикстуры.

## Цель

Показать на карточке инцидента контекст сцены (погода/день-ночь/покрытие) и **флаг расхождения**
«камера ↔ погода». Работает на живом API и фикстурах (`VITE_USE_FIXTURES`).

## Состав

- Клиент `getScene(id)` **уже существует** (`client.ts`) и возвращает `SceneResponse =
  { scene: SceneContext, weather: WeatherCrossCheck, state?: AiFeatureState }` (§8.4). Потребляй
  `scene`+`weather`; опц. `state.source` (live/cache/fallback) — для governance-индикатора (§8.6).
- В `IncidentCard.tsx` (аддитивно): блок «Контекст» с `SceneContextChip` + `DiscrepancyBadge`;
  состояния loading/empty/error (нет данных сцены / `404` → скрыть блок, не падать).
- Фикстуры `fixtures.ts` (аддитивно): `getFixtureScene` делаем id-aware и добавляем ≥1 запись с
  `weather.discrepancy=true` (демо бейджа на `VITE_USE_FIXTURES`; сейчас всегда `false`).

## Check

- `/incidents/:id` на живом API и фикстурах показывает чип сцены; кейс расхождения → бейдж «⚠ Камера ↔ погода».
- Нет данных сцены → блок скрыт, карточка не падает; `npm run typecheck` зелёный.
- Регрессий по f14 (карточка) нет (блок аддитивный).

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# параллельно в одном worktree — стейджи только свои файлы (НЕ git add -A).
# f15→f16 идут последовательно, обе правят fixtures.ts аддитивно — гонки нет.
git add web/src/pages/IncidentCard.tsx web/src/api/fixtures.ts
git commit -m "f15: <что сделано>"
```
