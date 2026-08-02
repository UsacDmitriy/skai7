# f16 · Прогноз + рекомендации в отчёте (идея #12)

> Трек **Frontend**. Против `00-CONTRACT.md` §8.3/§8.4. **Владеет:** **аддитивная** правка
> `web/src/pages/Report.tsx`; использует d7 (`ForecastSparkline`), f2-клиент.
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — вёрстка/состояния против контракта; гейт = typecheck.
> **Волна 4.2**, окно 2 (web). Зависит от: d7, `GET /api/reports/forecast/{plate}`, фикстуры.

## Цель

В отчёт В-1 (водитель) добавить **спарклайн тренда риска** + блок **рекомендаций**; в В-2 (парк) —
сводный прогноз/интервенции. Живой API и фикстуры.

## Состав

- f2-клиент: `getForecast(plate) → RiskForecast` (тип §8.4).
- В `Report.tsx` (аддитивно): в карточке водителя — `ForecastSparkline` (trend+коридор+аномалия) +
  список `recommendations`; warning-бейдж при `anomaly=true`. Состояния loading/empty/error.
- Фикстуры: `RiskForecast` для демо (один аномальный, один ровный).

## Check

- Отчёт В-1 показывает спарклайн + рекомендации; аномалия → warning. На фикстурах строится без сети.
- Пустой прогноз → осмысленный empty-state; `npm run typecheck` зелёный.
- Регрессий по f7 (Report) нет (блок аддитивный).
- **Метрики (b25):** при показе рекомендации эмитит `recommendation_shown`, при принятии — `recommendation_accepted`
  (эмиттер b25; без сети — no-op). Питает `recommendation_acceptance`.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# параллельно в одном worktree — стейджи только свои файлы (НЕ git add -A)
git add web/src/pages/Report.tsx
git commit -m "f16: <что сделано>"
```
