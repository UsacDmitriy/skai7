# W3-15 · Фронт-тесты «Здоровье парка» + кросс-врезки (vitest)

> Волна 3 · бэклог. Трек **T (tests)**. Против `00-CONTRACT.md` **§9.4** + §7.8-стиль состояний.
> **Модель:** 🔵 Sonnet — детерминированные тесты против контракта; гейт = секция Check.
> **Владеет:** `web/src/pages/FleetHealth.test.tsx`, `FuelCard.test.tsx`, `SensorCard.test.tsx`,
> и врезочные кейсы в `IncidentCard.test.tsx`/`TripDossier.test.tsx`/`App.test.tsx`. Режим `VITE_USE_FIXTURES=true`.
> Счёт в гейт web≥80% (Барьер 3). **Зависит от** w3-10..w3-13.

## Что покрыть (рендер + взаимодействие; happy + edge)

1. **FleetHealth.test.tsx** — ростер рендерит объединение; **баннер покрытия** «10 · 7 · 5 · 2» виден;
   у ТС без домена ячейка = «—»; 2 строки помечены «в видеопарке»; клик по строке навигирует в правильный домен.
2. **FuelCard.test.tsx** — таблица сверки и список заправок рендерятся; `recon_status`-бейдж окрашен; 404 →
   плашка «не найдено» (не белый экран).
3. **SensorCard.test.tsx** — спарклайн из 7 точек; `online_status="stale"` → нейтральный бейдж;
   `distance_gap=null` → «нет данных»; **в DOM нет сырых graph_points**.
4. **Кросс-врезки**:
   - `IncidentCard.test.tsx`: присутствует ссылка/кнопка на `/trip/<id>`; блок «Связанные заявки»
     фильтрует фикстурные заявки по `incident_id`; после `create_task` есть ссылка в `/tickets`.
   - `TripDossier.test.tsx`: есть бэк-ссылка на `/incidents/<id>`.
   - `App.test.tsx`: переход на мёртвый путь (напр. `/live`) рендерит `ComingSoon` с **описанием секции**
     и пилюлей «Волна 4», а не generic «Раздел в разработке»; `/fleet-health` рендерит реальный экран.

## Check

- `npx vitest run` — зелёный; новые файлы исполняются в режиме фикстур (без сети).
- Тесты на «—»-ячейки, баннер покрытия, отсутствие graph_points, наличие trip-ссылки и блока заявок,
  бэк-ссылку trip→incident и `ComingSoon` с описанием — все проходят.
- `npx vitest run --coverage` — вклад в гейт `web/src` ≥ 80% (Барьер 3); `npm run typecheck` зелёный.

## Коммит (обязательно)

```bash
git add -A && git commit -m "w3-15: vitest Здоровье парка + кросс-врезки + ComingSoon"
```
