# f15 · Scene context на карточке (идея #11)

> Трек **Frontend**. Против `00-CONTRACT.md` §8.3/§8.4. **Владеет:** **аддитивная** правка
> `web/src/pages/IncidentCard.tsx`; использует d7 (`SceneContextChip`/`DiscrepancyBadge`), f2-клиент.
> **Модель:** 🔵 Sonnet — вёрстка/состояния против контракта; гейт = typecheck.
> **Волна 4.2**, окно 2 (web). Зависит от: d7, `GET /api/incidents/{id}/scene`, фикстуры.

## Цель

Показать на карточке инцидента контекст сцены (погода/день-ночь/покрытие) и **флаг расхождения**
«камера ↔ погода». Работает на живом API и фикстурах (`VITE_USE_FIXTURES`).

## Состав

- f2-клиент: метод `getScene(id) → SceneContext & WeatherCrossCheck` (тип в `types.ts` по §8.4).
- В `IncidentCard.tsx` (аддитивно): блок «Контекст» с `SceneContextChip` + `DiscrepancyBadge`;
  состояния loading/empty/error (нет данных сцены → скрыть блок, не падать).
- Фикстуры `fixtures.ts`: scene/weather для inc-001…inc-005 (включая 1 кейс расхождения).

## Check

- `/incidents/:id` на живом API и фикстурах показывает чип сцены; кейс расхождения → бейдж «⚠ Камера ↔ погода».
- Нет данных сцены → блок скрыт, карточка не падает; `npm run typecheck` зелёный.
- Регрессий по f14 (карточка) нет (блок аддитивный).

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# параллельно в одном worktree — стейджи только свои файлы (НЕ git add -A)
git add web/src/pages/IncidentCard.tsx
git commit -m "f15: <что сделано>"
```
