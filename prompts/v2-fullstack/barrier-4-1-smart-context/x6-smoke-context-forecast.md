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

## Универсальный гейт + AI-негативы (обязательно)

Прогнать **полный** [`../barrier-CHECKLIST.md`](../barrier-CHECKLIST.md): `bash scripts/check.sh` целиком
(весь регресс P0/P1/P2/Волна 3 — не только `tu-*`), `make db` **дважды** идентично, пост-условие git (`main` не тронут).

AI-специфичные негативы/детерминизм/офлайн (доп.):
```bash
code(){ curl -s -o /dev/null -w '%{http_code}' "localhost:8000$1"; }
test "$(code /api/incidents/__nope__/scene)" = 404                          # неизвестный инцидент
test "$(code /api/reports/forecast/__nope__)" = 404                         # неизвестный водитель
curl -s 'localhost:8000/api/zones?hour=99' | jq -e 'type=="array"'          # битый фильтр → [] (не 500)
# офлайн-устойчивость: без сети/ключей — кэш/фолбэк, не 5xx
unset GROQ_API_KEY; diff <(curl -s localhost:8000/api/incidents/<id>/scene) <(curl -s localhost:8000/api/incidents/<id>/scene)  # детерминизм
# data-reality §8.0: b18 — детерминированный fallback (НЕ ARIMA), b20 — пустой набор валиден
curl -s localhost:8000/api/reports/forecast/<plate> | jq -e '.trend|length>=1 and (.anomaly==false)'   # наивный коридор
curl -s localhost:8000/api/fatigue | jq -e 'type=="array"'                  # пустые цепочки → [] (не падение)
# governance §8.6: мета и флаг
curl -s localhost:8000/api/incidents/<id>/scene | jq -e 'has("source") or has("state")'   # source/AiFeatureState
AI_FORECAST_ENABLED=disabled curl -s -o /dev/null -w '%{http_code}' localhost:8000/api/reports/forecast/<plate>  # → 200 «disabled», не 5xx
```
- Без кэша (`rm -f data/ai/*.json` во временной копии) → `risk_score` прежний (bonus=0), эндпоинты не падают.
- Паритет: d7-экраны на живом API **и** `VITE_USE_FIXTURES=true`; типы §8.4 совпадают; консоль чистая.

## Критерии приёмки

- Предрасчёт детерминирован и работает офлайн (нет сети → кэш, без 5xx); повтор `make db`/эндпоинта идентичен.
- Все 4 эндпоинта §8.3 отвечают валидной схемой (happy) **и** негативом (404/[]); флаг расхождения и рекомендации присутствуют.
- `risk_score` обратно совместим (без кэша — прежний); **полный** `scripts/check.sh` зелёный (регресс не сломан).
- `b18` — fallback-only (§8.0); `b20` пустой набор валиден; governance-мета/флаг работают.
- `main` НЕ тронут. Красный smoke → дефект треку, чиним на `integration`, к Волне 4.2 не переходим.

## Коммит (обязательно)

Барьер фиксирует smoke-правки (если были) в `integration`:

```bash
git add -A && git commit -m "x6: smoke wave 4.1 (умное событие + прогнозы)"
```
