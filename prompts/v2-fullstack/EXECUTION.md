# EXECUTION — параллельная разработка через вложенные worktree

> Всё внутри одного проекта `skai_7`. Параллельность — через **git worktree в `.worktrees/`**
> (папка игнорируется git), каждая открывается **отдельным окном VS Code** со своей сессией Claude Code.
> Источник истины — `00-CONTRACT.md`.

## Структура
```
skai_7/
├── api/  web/  prompts/  ...        ← основной чекаут (ветка main)
└── .worktrees/            (gitignored)
    ├── backend  [feat/backend]      ← окно 1: api/, data/seed/
    ├── web      [feat/web]          ← окно 2: web/
    └── tests    [feat/tests]        ← окно 3: Codex desktop (api/tests, web vitest)
```
В каждой `.worktrees/<name>/START.md` — очередь промптов и владение.

## Как открыть в VS Code (каждую — своим окном)
```bash
code /Users/dimausac/projects/skai_7/.worktrees/backend
code /Users/dimausac/projects/skai_7/.worktrees/web
code /Users/dimausac/projects/skai_7/.worktrees/tests
```
Или File → Open Folder → выбрать папку worktree → Open in New Window. В каждом окне открой панель
Claude Code и дай промпт волны (см. START.md). Окна работают **одновременно** — разные ветки, разные файлы.

### Как запускать промпт в Claude Code

**Один промпт = одна задача Claude Code.** В нужном окне открой панель Claude Code и дай команду:

```text
Выполни промпт @prompts/v2-fullstack/track-b-backend/b1-duckdb-etl.md
```

(`@`-ссылка подставит файл; либо просто «выполни b1»). Дождись завершения и проверки, затем следующий
по очереди из `START.md`. Промпты одной под-волны без зависимостей (например `b2`∥`b4`) можно дать сразу.

### Где запускать барьеры

Барьеры (`x1`–`x4`) выполняются **НЕ в worktree, а в основном окне `skai_7`** на ветке `integration`:

```bash
code /Users/dimausac/projects/skai_7        # основное окно (или просто оно уже открыто)
```

Затем в Claude Code этого окна: сначала git-склейка (см. блоки ниже), потом по одному
`@prompts/v2-fullstack/wave-x-integration/x1-remove-streamlit.md` → `x2` → `x3` (→ `x4` на барьере 2).

## Почему без конфликтов
Контракт §5/§7.7 закрепил непересекающиеся папки: `api/` ⟂ `web/` ⟂ `api/tests/`. Каждый worktree —
своя ветка, мерж чистый. Роуты `App.tsx` и корневые файлы (`Makefile`, `requirements*`) трогает только
integration (x1/x2), поэтому в параллельной фазе их никто не делит.

## Порядок волн

- **Волна 1** (backend ∥ web): BACKEND b1→b6 ; WEB d1→d3, f1→f4.
- **Волна 2** (макс. параллельно): BACKEND b7→b10, b8∥b9, b11∥b12∥b13 ; WEB d4∥d5, f5–f13 ; TESTS T1–T3.
- **Волна 3** (integration, основное окно `skai_7` на ветке integration): x1→x2→x3→x4.

## Подробная схема выполнения

Что запускать → в каком окне → где барьеры синхронизации.

```mermaid
flowchart TD
    C0["🔒 БАРЬЕР 0 — КОНТРАКТ<br/>(окно skai_7, main)<br/>заморозить 00-CONTRACT.md"]

    subgraph W1["ВОЛНА 1 · P0 core — окна 1 и 2 параллельно"]
        direction LR
        subgraph B1["🪟 Окно 1 · backend (feat/backend) — api/, data/"]
            direction TB
            b1["b1 duckdb-etl"] --> b3["b3 v-incidents"]
            b1 --> b2["b2 enrichment"]
            b1 --> b4["b4 fastapi-scaffold"]
            b3 --> b5["b5 schemas-repos-services"]
            b2 --> b5
            b4 --> b5
            b5 --> b6["b6 routers"]
        end
        subgraph F1["🪟 Окно 2 · web (feat/web) — web/ + дизайн-система"]
            direction TB
            subgraph D1["Дизайн-система (track-d)"]
                d1["d1 tailwind-theme"] --> d2["d2 ui-primitives"] --> d3["d3 component-lib"]
            end
            subgraph FR1["Фронт (track-f)"]
                f1["f1 vite-scaffold"] --> f2["f2 api-client"] --> f3["f3 mock-fixtures"] --> f4["f4 screens · IncidentCard"]
            end
            D1 --> FR1
        end
        subgraph CD["🌐 Claude Design (браузер) — параллельно, HTML-референсы"]
            cd["prompts/claude-design/** → ui/**"]
        end
    end

    C0 --> W1

    BR1["🚧 БАРЬЕР 1 — ИНТЕГРАЦИЯ P0<br/>(окно skai_7, ветка integration, ПОСЛЕДОВАТЕЛЬНО)<br/>merge feat/backend + feat/web → x1 → x2 → x3"]
    W1 --> BR1

    subgraph W2["ВОЛНА 2 · расширение P1/P2 — макс. параллельно"]
        direction LR
        subgraph B2["🪟 Окно 1 · backend"]
            direction TB
            wb7["b7 driver-reference → b10 reports-views"]
            wb89["b8 stt ∥ b9 nlu"]
            wb11["b11 sabotage ∥ b12 reb ∥ b13 tickets-alerts-trips<br/>⚠ роутеры в ALL_ROUTERS"]
        end
        subgraph F2["🪟 Окно 2 · web"]
            direction TB
            wd["d4 map ∥ d5 voice-timeline"]
            wf["f5…f13 (все параллельно)"]
        end
        subgraph T2["🪟 Окно 3 · tests (feat/tests, Codex)"]
            direction TB
            t4["T4 chores — сразу"]
            t1["T1 unit — после b2/b7/b10"]
            t2["T2 API — после b6 + b11–b13"]
            t3["T3 front — после d2/f2/f4"]
        end
    end

    BR1 --> W2

    BR2["🏁 БАРЬЕР 2 — ФИНАЛЬНЫЙ e2e<br/>(окно skai_7, integration)<br/>merge волны 2 → x2 → x3 → x4-e2e-p1p2 → merge в main"]
    W2 --> BR2
```

### Барьеры синхронизации — где и какой промпт

Все барьеры выполняются в **основном окне `skai_7`** (не в worktree), последовательно.

| Барьер | Ветка | Промпты / артефакт | Что делает |
| --- | --- | --- | --- |
| 🔒 0 · Контракт | `main` | `00-CONTRACT.md` (артефакт, замораживается вручную) | фиксирует поля, схемы §7.5, токены — источник истины; до заморозки треки не стартуют |
| 🚧 1 · Интеграция P0 | `integration` | `x1-remove-streamlit.md` → `x2-wiring.md` → `x3-e2e-smoke.md` | выпил Streamlit, склейка React↔FastAPI (`ALL_ROUTERS`, `App.tsx`), сквозной smoke |
| 🏁 2 · Финальный e2e | `integration` → `main` | повтор `x2`/`x3` → `x4-e2e-p1p2.md` | smoke на полном наборе P1/P2 (voice/NLU/reports/tickets/alerts/trips/REB/sabotage) |

> Файлы барьеров: `prompts/v2-fullstack/wave-x-integration/`.

### Окна и владение

| Окно | Worktree / ветка | Владеет папками | Открыть |
| --- | --- | --- | --- |
| 1 · Backend | `.worktrees/backend` / `feat/backend` | `api/`, `data/seed/`, `data/skai.duckdb` | `code .worktrees/backend` |
| 2 · Web | `.worktrees/web` / `feat/web` | `web/` | `code .worktrees/web` |
| 3 · Tests | `.worktrees/tests` / `feat/tests` (Codex) | `api/tests/`, vitest | `code .worktrees/tests` |
| Интеграция | `skai_7` / `integration` | корневые: `App.tsx`, `Makefile`, `requirements*` | основное окно |

### Волна 1 — P0 core (окна 1 и 2 одновременно)

| Окно | Промпты (порядок) | Проверка |
| --- | --- | --- |
| 1 Backend | `b1` → (`b2` ∥ `b4`) + `b3` → `b5` → `b6` | `make db` (54 аларма / 14 типов + `v_incidents`), `make api`, `GET /api/incidents` |
| 2 Web | `d1` → `d2` → `d3` → `f1` → `f2` → `f3` → `f4` | `VITE_USE_FIXTURES=true`, `npm run dev`, `npm run typecheck` |

> Коммит после волны: `git add -A && git commit -m "feat(backend): wave 1"` (аналогично для web).

### Барьер 1 — интеграция P0 (основное окно `skai_7`, последовательно)

**Шаг 1 — склейка веток:**

```bash
cd /Users/dimausac/projects/skai_7
git checkout integration && git merge feat/backend && git merge feat/web
```

**Шаг 2 — в Claude Code основного окна по одному промпту, дожидаясь проверки каждого:**

```text
Выполни @prompts/v2-fullstack/wave-x-integration/x1-remove-streamlit.md
Выполни @prompts/v2-fullstack/wave-x-integration/x2-wiring.md
Выполни @prompts/v2-fullstack/wave-x-integration/x3-e2e-smoke.md
```

### Волна 2 — расширение P1/P2 (макс. параллельно)

| Окно | Промпты | Примечание |
| --- | --- | --- |
| 1 Backend | `b7`→`b10` ; `b8` ∥ `b9` ; `b11` ∥ `b12` ∥ `b13` | ⚠ `b11`/`b13` добавляют свои роутеры в `api/routers/__init__.py` (`ALL_ROUTERS`), иначе `x2` отдаёт 404 |
| 2 Web | `d4` ∥ `d5` ; `f5`…`f13` (все параллельно) | — |
| 3 Tests | `T4` сразу · `T1` после `b2/b7/b10` · `T2` после `b6`+`b11–b13` · `T3` после `d2/f2/f4` | перед прогоном `git fetch && git merge integration`; баги эскалируются, в тестах не правятся |

### Барьер 2 — финальный e2e (основное окно `skai_7`)

**Шаг 1 — подтянуть волну 2:**

```bash
cd /Users/dimausac/projects/skai_7 && git checkout integration
git merge feat/backend && git merge feat/web
```

**Шаг 2 — в Claude Code основного окна:**

```text
Выполни @prompts/v2-fullstack/wave-x-integration/x2-wiring.md
Выполни @prompts/v2-fullstack/wave-x-integration/x3-e2e-smoke.md
Выполни @prompts/v2-fullstack/wave-x-integration/x4-e2e-p1p2.md
```

**Шаг 3 — финал в main:**

```bash
git checkout main && git merge integration
```

## Слияние
```bash
# в worktree после волны:
git add -A && git commit -m "feat(backend): wave 1"
# в основном репо:
cd /Users/dimausac/projects/skai_7
git checkout integration && git merge feat/backend && git merge feat/web
# Codex перед тестами: в .worktrees/tests → git merge integration
```
Финал: `integration` → `main`.

## Очистка по завершении
```bash
git worktree remove .worktrees/backend   # и т.д.
git branch -d feat/backend feat/web feat/tests
```
