# Волна 3 · бэклог некритичных доработок

> **Не входит в P0/P1/P2-скоуп.** Накопленные неблокирующие правки и улучшения продукта,
> выявленные аудитами после Волн 1/2. Не блокируют релиз; выполняются **по мере готовности
> трека-владельца**, на его ветке `feat/*`, и сходятся на Барьере 3. Источник истины — `00-CONTRACT.md`.
> **Правило:** один промпт = один файл; промпт лежит в папке своего трека-владельца.

## Структура — по трекам (как Волна 1)

> **Расширение (2026-06-05, целостность MVP).** К бэклогу добавлен блок «раскрытие тёмных данных»
> (топливо/сенсоры/навигация — сейчас 501-стабы) + кросс-врезки экранов + хаб «Здоровье парка».
> Контракт — новый аддендум **§9** в `00-CONTRACT.md` (авторская правка оркестратора; не FROZEN).
> Добавлено **Окно 2 · feat/web** (как в Волне 2.2).

```text
wave-3-backlog/
├── track-b-backend/   🪟 Окно 1 · feat/backend — api/, data/
│   ├── w3-1 b13-ticket-sync           enum Status, deadline/is_overdue
│   ├── w3-2 diagnostic-source-data    source=DIAGNOSTIC, бейдж «⚙ Диагностика»
│   ├── w3-5 no-video-incident         «нет видео» + «Запросить архив» (мёртвая ветка)
│   ├── w3-6 fuel-domain               /api/fuel — сверка ЗИС vs карты (снять 501) §9
│   ├── w3-7 sensors-domain            /api/sensors — CAN−GPS разрыв (снять 501) §9
│   ├── w3-8 navigation-list           /api/navigation — список проблем → вход в РЭБ §9
│   └── w3-9 fleet-health-view 🔴      v_fleet_health (объединение 17 ТС) + /api/fleet-health §9
│   └── w3-16 ai-foundation 🆅4        ML-deps + data/ai кэш + ai_metric_events DDL (подготовка В.4)
├── track-f-frontend/  🪟 Окно 2 · feat/web — web/src
│   ├── w3-10 api-layer                types/client/fixtures fleet-health (+fix getReb фикстуры)
│   ├── w3-11 fleet-health-hub         FleetHealth + FuelCard/SensorCard/NavProblemList
│   ├── w3-12 cross-wiring             incident↔trip↔tickets, report→incident, feed→trip
│   ├── w3-13 nav-signposting          роуты + ComingSoon (Волна 4) вместо пустого 404
│   ├── w3-17 ai-api-scaffold 🆅4      AI types/client/fixtures §8.4/8.7/8.8 (подготовка В.4)
│   └── w3-18 ai-routes-nav 🆅4        маршруты /copilot,/metrics + меню (каркас f17/f21)
└── track-t-tests/     🪟 Окно 3 · feat/tests — api/tests, vitest
    ├── w3-3 backend-unit-coverage     unit b1–b13 (дозакрытие t1), гейт api≥85%
    ├── w3-4 frontend-unit-coverage    unit d3–d5/f5–f13 (дозакрытие t3), гейт web≥80%
    ├── w3-14 darkdata-api-tests       API fuel/sensors/navigation/fleet-health (happy+негатив)
    ├── w3-15 fleet-health-frontend    vitest хаб + кросс-врезки + ComingSoon
    └── w3-19 ci-status-scaffold 🆅4   .github/workflows ci.yml скелет + gen_status.py (каркас t5/t6)
```

> **🆅4 = подготовка Волны 4** (`w3-16…w3-19`): снимают блокеры до старта AI-слоя — ML-зависимости,
> `data/ai/`-кэш, `ai_metric_events`, AI-типы/клиент/фикстуры, маршруты `/copilot`+`/metrics`, CI/статус-каркас.
> Реструктуризация Волны 4 → **4.1 smart-context · 4.2 assistant · 4.3 ops & trust** (барьеры x6/x7/**x8**).

## Граф выполнения (как Волна 1)

```text
        ┌─────────────── после Барьера 2 (P1/P2 уже в main) ───────────────┐
        ▼                          ▼                                        ▼
  🪟 ОКНО 1 · backend        🪟 ОКНО 2 · web (feat/web)         🪟 ОКНО 3 · tests
  track-b-backend/           track-f-frontend/                  track-t-tests/
  w3-1 ticket-sync  ┐        w3-10 api-layer ──┐ (база)         w3-3 backend-cov  ┐
  w3-2 diagnostic   │∥       w3-11 fleet-hub   ├ после w3-10    w3-4 frontend-cov │∥
  w3-5 no-video     │        w3-12 cross-wiring│  (∥ между      w3-14 darkdata-api│ (∥; w3-14/15
  w3-6 fuel        ┐│        w3-13 signposting ┘  собой)        w3-15 fleet-front ┘  после доменов)
  w3-7 sensors     ├┘∥
  w3-8 navigation  ┘  (w3-9 после w3-6/7/8)
  w3-9 fleet-view 🔴
        └──────────────────────────────┬──────────────────────────────────┘
                                        ▼
                  🧪 БАРЬЕР 3 · barrier-3-hardening/x5-wave3-hardening
                  merge feat/backend+feat/web+feat/tests → регресс (unit+API+фронт)
                  + гейт покрытия (api≥85% / web≥80%) + сквозная навигация → merge в main (ff-only)
```

## Как выполнять

В окне трека-владельца дай промпт (порядок между пунктами не важен, можно параллельно):

| 🪟 Окно | Промпты (∥) | Команда запуска |
| --- | --- | --- |
| 1 · backend | `w3-1` ∥ `w3-2` ∥ `w3-5` ∥ `w3-6` ∥ `w3-7` ∥ `w3-8` ∥ **`w3-16`** (🆅4); **`w3-9` после `w3-6/7/8`** | `Выполни @prompts/v2-fullstack/wave-3-backlog/track-b-backend/w3-6-fuel-domain.md` |
| 2 · web | **`w3-10` (база) → `w3-11` ∥ `w3-12` ∥ `w3-13`**; **`w3-17` (🆅4) → `w3-18` (🆅4, после `w3-13`)** | `Выполни @prompts/v2-fullstack/wave-3-backlog/track-f-frontend/w3-10-api-layer.md` |
| 3 · tests | `w3-3` ∥ `w3-4` ∥ **`w3-19`** (🆅4); **`w3-14` после доменов, `w3-15` после фронта** | `Выполни @prompts/v2-fullstack/wave-3-backlog/track-t-tests/w3-14-darkdata-api-tests.md` |

> **🆅4 = подготовка Волны 4** (`w3-16…w3-19`) — независимы от блока §9, идут параллельно в своих окнах.
> `w3-18` зависит от `w3-13` (общий `ComingSoon`/`App.tsx`), `w3-17` — от никого (только типы/фикстуры).

**Барьер 3** — в основном окне `skai_7` на ветке `integration`, после завершения пунктов:

```text
Выполни @prompts/v2-fullstack/barrier-3-hardening/x5-wave3-hardening.md
```

## Очередь — детали и приоритеты

| # | Промпт | Трек | Приоритет |
| --- | --- | --- | --- |
| W3-1 | [`track-b-backend/w3-1-b13-ticket-sync.md`](track-b-backend/w3-1-b13-ticket-sync.md) — синхронизация `b13` с contract-change #1 (enum `Status`, `deadline`/`is_overdue`) | b13 / backend | Средний |
| W3-2 | [`track-b-backend/w3-2-diagnostic-source-data.md`](track-b-backend/w3-2-diagnostic-source-data.md) — данные для `Source=DIAGNOSTIC` (бейдж «⚙ Диагностика», макет 07) | b1 / данные | Низкий |
| W3-5 | [`track-b-backend/w3-5-no-video-incident-reachable.md`](track-b-backend/w3-5-no-video-incident-reachable.md) — no-video инцидент достижим (мёртвая UI-ветка «нет видео» + `sensor_active_after_sec` §2); выявлено smoke x3 | b3 / данные (+T) | Средний |
| W3-3 | [`track-t-tests/w3-3-backend-unit-coverage.md`](track-t-tests/w3-3-backend-unit-coverage.md) — backend unit-покрытие `b1–b13` (дозакрытие t1), гейт `api/`≥85% | T / tests | Высокий |
| W3-4 | [`track-t-tests/w3-4-frontend-unit-coverage.md`](track-t-tests/w3-4-frontend-unit-coverage.md) — frontend unit-покрытие `d3–d5`/`f5–f13` (дозакрытие t3), гейт `web/src`≥80% | T / tests | Высокий |
| W3-6 | [`track-b-backend/w3-6-fuel-domain.md`](track-b-backend/w3-6-fuel-domain.md) — домен `fuel` (`v_fuel` + сервис + роутер), снять 501 · §9 | b / данные | Высокий |
| W3-7 | [`track-b-backend/w3-7-sensors-domain.md`](track-b-backend/w3-7-sensors-domain.md) — домен `sensors` (CAN−GPS, спарклайн; без 959k graph_points) · §9 | b / данные | Высокий |
| W3-8 | [`track-b-backend/w3-8-navigation-list.md`](track-b-backend/w3-8-navigation-list.md) — `navigation`-список → вход в существующий `/api/reb` · §9 | b / данные | Высокий |
| W3-9 | [`track-b-backend/w3-9-fleet-health-view.md`](track-b-backend/w3-9-fleet-health-view.md) — 🔴 `v_fleet_health` (объединение 17 ТС) + `/api/fleet-health` · §9 | b / данные | Высокий |
| W3-10 | [`track-f-frontend/w3-10-api-layer.md`](track-f-frontend/w3-10-api-layer.md) — types/client/fixtures fleet-health (+fix `getReb`/`getVehicleReport` фикстуры) · §9 | f2/f3 | Высокий |
| W3-11 | [`track-f-frontend/w3-11-fleet-health-hub.md`](track-f-frontend/w3-11-fleet-health-hub.md) — `FleetHealth` хаб + `FuelCard`/`SensorCard`/`NavProblemList` · §9 | f | Высокий |
| W3-12 | [`track-f-frontend/w3-12-cross-wiring.md`](track-f-frontend/w3-12-cross-wiring.md) — кросс-врезки: incident↔trip↔tickets, report→incident, feed→trip · §9.4 | f | Высокий |
| W3-13 | [`track-f-frontend/w3-13-nav-signposting.md`](track-f-frontend/w3-13-nav-signposting.md) — роуты fleet-health/navigation + `ComingSoon` (Волна 4) вместо пустого 404 · §9.4 | f1 | Средний |
| W3-14 | [`track-t-tests/w3-14-darkdata-api-tests.md`](track-t-tests/w3-14-darkdata-api-tests.md) — API-тесты fuel/sensors/navigation/fleet-health (happy+негатив) | T / tests | Высокий |
| W3-15 | [`track-t-tests/w3-15-fleet-health-frontend-tests.md`](track-t-tests/w3-15-fleet-health-frontend-tests.md) — vitest хаб + кросс-врезки + `ComingSoon` | T / tests | Высокий |
| W3-16 | [`track-b-backend/w3-16-ai-foundation.md`](track-b-backend/w3-16-ai-foundation.md) — 🆅4 ML-deps (sklearn/statsmodels) + `data/ai/` кэш-placeholder + `ai_metric_events` DDL · §8.0/8.1/8.7 | b / данные | Высокий |
| W3-17 | [`track-f-frontend/w3-17-ai-api-scaffold.md`](track-f-frontend/w3-17-ai-api-scaffold.md) — 🆅4 AI types/client/fixtures §8.4/8.7/8.8 (+`narrative`) | f2/f3 | Высокий |
| W3-18 | [`track-f-frontend/w3-18-ai-routes-nav.md`](track-f-frontend/w3-18-ai-routes-nav.md) — 🆅4 маршруты `/copilot`+`/metrics` + меню (каркас f17/f21) · §8.3 | f1 | Средний |
| W3-19 | [`track-t-tests/w3-19-ci-status-scaffold.md`](track-t-tests/w3-19-ci-status-scaffold.md) — 🆅4 `.github/workflows/ci.yml` скелет + `scripts/gen_status.py` (каркас t5/t6) · §8.9 | T / CI | Высокий |

> **Контракт §9** (раскрытие тёмных данных) — аддендум в `../00-CONTRACT.md`, авторская правка
> оркестратора (не FROZEN, contract-change #2). На него ссылаются W3-6…W3-15. Отменяет строку §7.4
> «fuel/sensors/navigation остаются стабами 501» в части этих доменов.
>
> **🆅4 — подготовка Волны 4** (`W3-16…W3-19`, contract-change #2 §8). Снимают блокеры до старта AI-слоя:
> ML-зависимости, `data/ai/`-кэш + `ai_metric_events`, AI-типы/клиент/фикстуры, маршруты `/copilot`+`/metrics`,
> CI/статус-каркас. **data-reality §8.0:** алярмы за 2 дня → `b18` fallback-only (без ARIMA), `b20` sparse.
> Волна 4 реорганизована: **4.1 smart-context · 4.2 assistant · 4.3 ops & trust** (барьеры x6 · x7 · **x8**).

## Куда складывать новые пункты

Новый backend/данные-пункт → `track-b-backend/wN-*.md`; тестовый → `track-t-tests/wN-*.md`
(+ строка в таблицу «Очередь» выше и в таблицу Волны 3 в `../EXECUTION.md`). Так бэклог остаётся executable.

> Закрытый аудитом дефект Волны 1 (b2 `_SPEED_LIMIT_TABLE` на legacy-кодах) исправлен в рамках
> Волны 1 (`feat/backend`, fix(b2)) и в бэклог Волны 3 не выносится.
