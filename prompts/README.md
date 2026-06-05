# Prompts — SKAI: Единое окно видео и телематики

**Стек (v2):** DuckDB (данные) + FastAPI (бэкенд) + React / Vite / Tailwind (фронт)
**Правило:** один промпт = один файл

```
prompts/
│
├── v2-fullstack/           ← актуальный план: пересборка SKAI как полноценного продукта
│   ├── 00-CONTRACT.md          общий контракт данных и API между треками
│   ├── README.md               обзор волн и порядок запуска
│   ├── wave-1-p0/              P0 core: track-b (b1–b6) ‖ track-d (d1–d3) ‖ track-f (f1–f4)
│   ├── wave-2-1-reports-voice/ P1 Reports&Voice: track-b (b7–b10) ‖ track-d (d5) ‖ track-f (f7)
│   ├── wave-2-2-applied/       P1/P2 экраны: track-b (b11–b13) ‖ track-d (d4) ‖ track-f (f5,f6,f8–f13)
│   ├── wave-2-3-tests/         track-t (t1–t4, worktree feat/tests)
│   ├── wave-3-backlog/         бэклог доработок + тест-хардненинг (w3-*)
│   ├── barrier-1-p0/              ⟵ волна 1: выпил Streamlit, связка, e2e-smoke (x1–x3)
│   ├── barrier-2-1-reports-voice/ ⟵ волна 2.1: smoke отчёты/voice (x4a)
│   ├── barrier-2-2-applied/       ⟵ волна 2.2: smoke прикладных (x4b)
│   ├── barrier-2-3-tests/         ⟵ волна 2.3: финал P1/P2 (x4)
│   └── barrier-3-hardening/       ⟵ волна 3: регресс + гейт покрытия (x5)
│
└── init/                   ← инициализационные промпты (запускаются на старте)
    ├── discovery-prompt.md       дискавери: 12 вопросов системного аналитика → черновик AGENTS.md
    ├── orchestration-prompt.md   оркестрация: multi-agent координация
    └── setup/                    инициализация репозитория и инфраструктуры
        ├── 01-git-infra.md       Git + окружение
        ├── 02-backend.md         бэкенд-база
        ├── 03-frontend.md        UI-структура
        └── 04-qa-integration.md  QA и интеграция
```

## Правила запуска

- **Трек/волна = параллельный запуск.** Промпты внутри одного трека/волны можно запускать одновременно.
- **Зависимости между треками** описаны в `v2-fullstack/00-CONTRACT.md` и `v2-fullstack/README.md`.
- **Один промпт = один файл.** Каждый агент трогает только свой выходной файл.
- **Модели не ограничены** — используйте наиболее способные доступные модели (например, Claude Opus). Параллельный запуск агентов разрешён.

## Последовательность выполнения

Четыре волны. Внутри волны треки идут параллельно, между волнами — барьеры синхронизации.

### Барьер 0 — контракт

Сначала зафиксировать `v2-fullstack/00-CONTRACT.md` (пишет/проверяет ведущий, остальные читают).
Без замороженного контракта треки не стартуют — все кодят против JSON-схем и токенов, а не против чужого рантайма.

### Волна 1 — P0 core (3 трека параллельно)

Цель: «Карточка инцидента» end-to-end на живом API.

- **Backend:** `b1-duckdb-etl` → ( `b2-enrichment` ∥ `b4-fastapi-scaffold` ) + `b3-v-incidents` → `b5-schemas-repos-services` → `b6-routers`
  - `b1` блокирует `b3`; `b2` и `b4` независимы и идут параллельно; `b5` владеет всеми доменными схемами §7.5 и предшествует `b6`.
  - Проверка: `make db` (54 аларма / 14 типов + `v_incidents`), `make api`, `GET /api/incidents`.
- **Design:** `d1-tailwind-theme` → `d2-ui-primitives` (VideoPlayer/TelemetryChart с sync-пропсами) → `d3-component-lib`
- **Frontend:** `f1-vite-scaffold` → `f2-api-client` (владеет всеми типами/методами §3.1+§7.5) → `f3-mock-fixtures` → `f4-screens` (IncidentCard P0, видео↔телеметрия sync)
  - Фронт работает на `VITE_USE_FIXTURES=true` — бэкенд для разработки не нужен.

### Барьер 1 — интеграция (`barrier-1-p0`, последовательно)

`x1-remove-streamlit` → `x2-wiring` (склейка React↔FastAPI, авто-сбор `ALL_ROUTERS`) → `x3-e2e-smoke`.

### Волна 2 — расширение P1/P2 (максимальный параллелизм)

Стартует после прохождения Барьера 1. Граница только по контракту.

- **Backend:** `b7-b10` (driver-reference/STT/NLU/reports-views) ∥ `b11-b12` (sabotage/reb) ∥ `b13` (tickets-alerts-trips)
- **Design:** `d4-map-primitives` ∥ `d5-voice-timeline`
- **Frontend:** `f5-events-feed`, `f6-monitor-map`, `f7-analytics-voice`, `f8-tickets`, `f9-dispatch-alert`, `f10-trip-dossier`, `f11-reb-recovery`, `f12-sabotage`, `f13-role-toggle`
  - ⚠️ Новые роутеры `b11`/`b13` должны попасть в `api/routers/__init__.py` (`ALL_ROUTERS`), иначе `x2` молча отдаёт 404.

### Барьер 2 — финальный e2e

Повтор `x2`/`x3` на полном наборе фич + `x4` smoke (voice/NLU/reports/tickets/alerts/trips/REB/sabotage).

### Тесты — `track-t-tests` (worktree `feat/tests`, Claude Code, параллельно, по готовности кода)

Тест-трек владеет только тестами и chores; баги в продукт-коде эскалируются, а не правятся в тестах.

- **t4** (chores: `.env.example`, lint, RUNBOOK, `check.sh`) — сразу, без зависимостей.
- **t1** (backend unit) — после мержа `b2/b7/b10` в `integration`.
- **t2** (API integration) — после `b6` (P0) + `b11–b13` (P1/P2).
- **t3** (frontend) — после `d2/f2/f4`, далее по мере `f5–f13`.
- Перед прогоном: `git fetch && git merge origin/integration`. Проверка: `pytest api/tests -q` / `cd web && npx vitest run`.

## Где что лежит

| Папка | Назначение | Когда запускать |
|---|---|---|
| `init/discovery-prompt.md` | Системный аналитик задаёт 12 вопросов команде, выдаёт черновик AGENTS.md | На старте, после определения темы |
| `init/orchestration-prompt.md` | Главный архитектор проверяет согласованность кусков от разных агентов | Периодически во время работы |
| `init/setup/` | Параллельный запуск Git-инфраструктуры, бэкенда, фронтенда и QA | Один раз в начале проекта |
| `v2-fullstack/` | Пошаговая пересборка продукта (DuckDB + FastAPI + React) по трекам и волнам | Основная работа |
