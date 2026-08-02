# x5 · Барьер 3 — хардненинг Волны 3 (полный регресс + гейт покрытия)

> **Барьер 3 — финал Волны 3 (бэклог + тест-хардненинг).** **Владеет:** только запуск/проверки (regress + coverage).
> **Исполнение:** owner-only gate — Claude/Codex; ClinePass excluded from shared contracts, integration, deterministic acceptance, and commit — высокие ставки: интеграция / синк / алгоритм / анти-регресс / killer-feature / барьер.
> Авторство тестов — Track T (`w3-3`/`w3-4` покрытие, `w3-14`/`w3-15` тесты §9); доработки — `w3-1`
> (b13/Ticket), `w3-2` (DIAGNOSTIC), `w3-5` (no-video); **целостность MVP (§9)** — backend `w3-6`/`w3-7`/`w3-8`/`w3-9`
> (домены fuel/sensors/navigation + fleet-health), web `w3-10`…`w3-13` (хаб + кросс-врезки + ComingSoon).
> Ничего не переписывает — при провале заводит дефект треку-владельцу. Запускается **после Барьера 2
> (x4 зелёный, P1/P2 в `main`)** и завершения Волны 3.

## Перед стартом — склейка Волны 3 (main держим стабильным)

В окне `skai_7` на ветке `integration`. **`main` сейчас = стабильный P1/P2 (после x4) — не трогаем**,
пока полный регресс Волны 3 не зелёный.

```bash
cd /Users/dimausac/projects/skai_7
git checkout integration

# GUARD: merge берёт только коммиты — стоп, если в worktree есть незакоммиченные изменения.
for w in backend web tests; do
  d=".worktrees/$w"; [ -d "$d" ] || continue
  test -z "$(git -C "$d" status --porcelain)" || { echo "❌ $w: незакоммичено — закоммить в worktree и повтори барьер"; exit 1; }
done

git merge feat/backend feat/web feat/tests   # волна 3: w3-1..w3-19 (бэклог + §9 тёмные данные + кросс-врезки + §8 prep Волны 4)
```

Конфликты разруливаем на `integration`.

## Проверка предыдущего шага (x4 · P1/P2 зелёный)

Не валидируй хардненинг поверх сломанного релиза:

- P1/P2-smoke из x4 всё ещё проходит; `main` указывает на P1/P2-стабильный коммит (`git log main -1 --oneline`).
- Слияние Волны 3 прошло без конфликтов (`git status` чисто).

Не прошло — **стоп**, дефект, чиним на `integration`.

## Цель

Подтвердить, что бэклог-доработки применены и **всё решение покрыто unit-тестами по промптам**,
а полный регресс (unit + API + фронт) зелёный с заданным порогом покрытия.

## Доработки бэклога (w3-1 / w3-2 / w3-5)

1. `grep -n '"new"' prompts/v2-fullstack/wave-2-2-applied/track-b-backend/b13-tickets-alerts-trips.md` → **пусто** (W3-1: enum `Status` без `new`).
   Если `tickets_service` реализован — `Ticket.status` дефолт `"active"`, есть `deadline`/`is_overdue`.
2. W3-2: либо `grep -n DIAGNOSTIC data/analysis/alarm_types.json` непуст (есть строка `source:"DIAGNOSTIC"`),
   либо в `00-CONTRACT.md` рядом с changelog #1(a) зафиксировано, что значение зарезервировано без данных.
3. W3-5: `SELECT video_available, count(*) FROM v_incidents GROUP BY 1` содержит строку `(0, ≥1)`
   **или** в `00-CONTRACT.md` §1.3 зафиксировано, что no-video кейс приходит из Волны 2/§9 (тест в `skip`).

## Раскрытие тёмных данных + целостность (W3-6…W3-15, §9)

**Liveness доменов (стабы 501 сняты) — на запущенном бэке (`make db` + сервер):**

```bash
test "$(curl -s localhost:8000/api/fuel | jq 'length')" -ge 1          # fuel: 10
test "$(curl -s localhost:8000/api/sensors | jq 'length')" -ge 1       # sensors: 7
test "$(curl -s localhost:8000/api/navigation | jq 'length')" -ge 5    # navigation-list
curl -s localhost:8000/api/fleet-health | jq '.coverage'               # {fuel:10,sensors:7,navigation:5,in_video_fleet:2}
for r in fuel sensors navigation; do grep -L 501 api/routers/$r.py; done  # стабы 501 исчезли
curl -s -o /dev/null -w '%{http_code}' localhost:8000/api/fuel/НЕТ999   # → 404 (негатив)
curl -s localhost:8000/api/sensors/<plate> | jq 'has("graph_points")'   # → false (анти-регресс: 959k не отдаём)
```

**Граф навигации (целостность экранов — статические grep по исходникам):**

```bash
grep -q "/fleet-health" web/src/App.tsx                       # реальные роуты §9 подключены
grep -q "ComingSoon" web/src/App.tsx                          # generic Placeholder заменён в catch-all
grep -Eq "/trip/|getTickets" web/src/pages/IncidentCard.tsx   # маршрут-ссылка + «Связанные заявки»
grep -q "/incidents/" web/src/pages/TripDossier.tsx           # бэк-ссылка trip→incident
```

**Опц. сквозной путь (ручной/Playwright, в стиле smoke барьеров):** лента → инцидент → «Показать маршрут
поездки» (`/trip/:id`) → «К карточке инцидента» → «Здоровье парка» → fuel-карточка; «Навигация (РЭБ)»
список → `/reb/:id`; мёртвый пункт меню → `ComingSoon` с описанием (не пустой 404).

## Готовность подготовки Волны 4 (W3-16…W3-19, §8) — блокеры AI-слоя сняты

```bash
# w3-16 · ML-deps + data/ai кэш + ai_metric_events
python -c "import sklearn, statsmodels"                          # ML-стек ставится (b18/b19)
test -d data/ai && ls data/ai/scene_labels.json data/ai/weather_cache.json   # кэш-каркас есть
python -c "import json,sys; [sys.exit(0 if len(json.load(open('data/ai/'+f)))==54 else 1) for f in ['scene_labels.json','weather_cache.json']]"  # 54 строки
test -f api/sql/33_ai_metric_events.sql                          # DDL событий метрик
make db && python -c "import duckdb;print(duckdb.connect('data/skai.duckdb').execute('select count(*) from ai_metric_events').fetchone())"  # таблица есть (пустая)
# w3-17 · AI-типы/клиент/фикстуры
grep -Eq "AiMetrics|DataQuality|RiskBreakdown|SceneContext" web/src/api/types.ts   # типы §8.4/8.7/8.8
grep -Eq "getAiMetrics|getRiskBreakdown|getScene|copilotChat" web/src/api/client.ts
# w3-18 · маршруты/меню под f17/f21
grep -Eq "/copilot|/metrics" web/src/App.tsx                     # маршруты заведены (каркас сирот нет)
# w3-19 · CI/статус-каркас под t5/t6
test -f .github/workflows/ci.yml && test -f scripts/gen_status.py
```

Любой пункт красный → **дефект треку-владельцу prep-промпта**, Волну 4 не стартуем до зелёного
(иначе AI-слой упрётся в отсутствующий каркас). **Данные §8.0:** проверить, что `b18` помечен fallback-only.

## Регресс + гейт покрытия

> Сначала **универсальный гейт** [`../barrier-CHECKLIST.md`](../barrier-CHECKLIST.md): `bash scripts/check.sh`
> (ruff+pytest+typecheck+vitest целиком), `make db` дважды идемпотентно, негативы (404/[]/422), паритет
> live↔fixtures, пост-условие git. Ниже — добавочный гейт **покрытия** Волны 3.

**Backend (w3-3 + t1):**

```bash
make db
pytest api/tests -q                       # unit + integration — зелёный
pytest --cov=api api/tests/unit           # покрытие api/ ≥ 85%, enrichment.py ≥ 90%
```

**Frontend (w3-4 + t3):**

```bash
cd web && npm ci
npx vitest run --coverage                 # зелёный; покрытие web/src ≥ 80%
npm run typecheck                         # без ошибок (типы §3.1+§7.5)
```

## Критерии приёмки

- Полный регресс зелёный: `pytest api/tests` + `npx vitest run` без падений.
- Покрытие достигает порогов: `api/` ≥ 85% (enrichment ≥ 90%), `web/src` ≥ 80%.
- Все модули по промптам имеют unit-файл (b1–b13 в `api/tests/unit/**`; d3–d5/f5–f13 в `web/src/**/*.test.tsx`).
- W3-1/W3-2/W3-5 отражены (проверки выше зелёные).
- **Целостность (§9):** liveness fuel/sensors/navigation/fleet-health зелёный (стабы 501 сняты, негатив 404,
  sensors без graph_points); граф-навигация зелёный (роуты fleet-health, ComingSoon вместо пустого 404,
  incident↔trip↔tickets связаны). Провал любого — дефект треку-владельцу, `main` остаётся на P1/P2.
- **Готовность prep Волны 4 (§8, W3-16…19):** ML-deps ставятся; `data/ai/` + `ai_metric_events` есть;
  AI-типы/клиент (§8.4/8.7/8.8) и маршруты `/copilot`+`/metrics` заведены; CI-каркас (`ci.yml`+`gen_status.py`)
  на месте. Без этого AI-слой Волны 4 не стартует.

## Финализация — продвинуть main (Волна 3 стабильна)

**Только если все критерии приёмки выше зелёные:**

```bash
git -C /Users/dimausac/projects/skai_7 checkout main
git merge --ff-only integration       # main догоняет integration (fast-forward)
# если ff-only падает (в main снова попали прямые коммиты) →
#   git merge --no-ff integration -m "merge integration → main (Волна 3 hardening)"
git checkout integration
```

Регресс/покрытие красные → **`main` остаётся на P1/P2** (из x4), заводим дефект трека и чиним на `integration`.
`main` всегда = последний зелёный релиз.
