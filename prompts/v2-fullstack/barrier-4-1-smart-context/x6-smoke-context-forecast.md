# x6 · smoke умное событие + прогнозы (Волна 4.1)

> **Барьер-волна.** **Владеет:** только запуск/проверки (smoke). Авторство тестов — трек T (`tu-*`).
> **Модель:** 🔴 Opus — интеграция/приёмка/решение green-red на барьере.
> Запускать ПОСЛЕ Волны 4.1 (b16–b20, d7, tu-* готовы и проходят свои check). `main` не трогаем.

## Перед стартом — склейка Волны 4.1 (main держим стабильным)

В окне `skai_7` на ветке `integration`. **`main` = стабильный P1/P2 — не трогаем**, пока smoke не зелёный.

```bash
cd /Users/dimausac/projects/skai_7
git checkout integration

# GUARD: merge берёт только коммиты — стоп, если в worktree есть незакоммиченные изменения.
for w in backend web tests; do
  d=".worktrees/$w"; [ -d "$d" ] || continue
  test -z "$(git -C "$d" status --porcelain)" || { echo "❌ $w: незакоммичено — закоммить в worktree и повтори барьер"; exit 1; }
done

git merge feat/backend feat/web   # 4.1: b16–b20, d7
```

Конфликты разруливаем на `integration`.

## Цель

Подтвердить, что AI-слой 4.1 работает end-to-end на **кэше** (без сети/VLM/ключей) и питает risk/UI.

## Шаги

### Предрасчёт/данные
1. `python -m api.etl.scene_precompute` и `python -m api.etl.weather_precompute` — без сети читают кэш
   `data/ai/*.json` (с сетью — обновляют); идемпотентно.
2. `make db` → `incident_scene`=54, `incident_weather`=54, `v_risk_zones` непуст (incident+reb).

### API
3. `make api`, затем:
   - `GET /api/incidents/{id}/scene` → 200 `SceneContext`+`WeatherCrossCheck`; кейс расхождения виден.
   - `GET /api/reports/forecast/{plate}` → 200 `RiskForecast` (trend 7д, recommendations непуст).
   - `GET /api/zones?kind=reb` → 200 только РЭБ-зоны; `GET /api/fatigue` → 200 `FatigueChain[]`.
   - `risk_score` в `/api/incidents` с учётом погодной надбавки (не ниже прежнего).

### pytest
4. `pytest api/tests/unit/test_scene_context.py test_weather_crosscheck.py test_forecast.py test_zones.py test_fatigue.py -q` — зелёные.

### Фронт
5. `cd web && npm run typecheck` — без ошибок (типы §8.4 совпадают); d7-примитивы импортируются.

## Критерии приёмки

- Предрасчёт детерминирован и работает офлайн (нет сети → кэш, без падений).
- Все 4 эндпоинта §8.3 отвечают валидной схемой; флаг расхождения и рекомендации присутствуют.
- `risk_score` обратно совместим (без кэша — прежний); регресс t1/`tu-enrichment` зелёный.
- `main` НЕ тронут. Красный smoke → дефект треку, чиним на `integration`, к Волне 4.2 не переходим.

## Коммит (обязательно)

Барьер фиксирует smoke-правки (если были) в `integration`:

```bash
git add -A && git commit -m "x6: smoke wave 4.1 (умное событие + прогнозы)"
```
