# TRACK T — тесты и рутина (Claude Code, worktree `feat/tests`)

Промпты для **тестов и вспомогательных файлов**, которые гонятся параллельно продуктовым трекам
(B/D/F) в отдельном окне Claude Code (worktree `.worktrees/tests` / ветка `feat/tests`).
Каждый промпт самодостаточен и кодит против `prompts/v2-fullstack/00-CONTRACT.md`.

> **Принцип владения:** трек владеет **тестами и вспомогательными файлами** — НЕ продуктовым кодом.
> Тесты пишутся после того, как соответствующий трек создал код (или параллельно, на готовых модулях).
> Барьеры `x3`/`x4` только **запускают** pytest/vitest — авторство тестов здесь.
> При найденном баге трек заводит дефект соответствующему треку (B/D/F), а не правит продуктовый код.

## Задачи

> Колонка **Исполнение** задаёт bounded ClinePass package: role `worker`, route category `code`.
> Exact route alias и model slug разрешаются только из `tools/clinepass-mcp/models.env`.
> Двойной красный `Check` эскалирует пакет к owner-only Claude/Codex по `EXECUTION.md`.

| Файл | Что делает | Владеет | Когда | Исполнение |
|---|---|---|---|---|
| `t1-backend-unit-tests.md` | **инфраструктура** unit: `conftest`, `requirements-dev`, раскладка | `api/tests/conftest.py`, `api/requirements-dev.txt`, `api/tests/unit/__init__.py` | до `tu-*` | bounded ClinePass · worker · `code` |
| `per-feature/tu-*.md` (6 шт.) | **per-feature unit-авторство**: enrichment/driver/nlu/reports/sabotage/reb — каждый владеет своим `test_*.py` | `api/tests/unit/test_*.py` (по модулю) | каждый — как его фича (b2/b7/b9/b10/b11/b12) легла на `integration` | bounded ClinePass · worker · `code` |
| `t2-api-integration-tests.md` | pytest TestClient: все эндпоинты, коды, схемы | `api/tests/integration/**` | после b6 (P0) и b11–b13 (P1/P2) | bounded ClinePass · worker · `code` |
| `t3-frontend-tests.md` | vitest + RTL: UI-примитивы, api-клиент, экраны | `web/**/*.test.tsx`, `web/vitest.config.ts`, `web/src/test/**` | после d2/f2/f4 | bounded ClinePass · worker · `code` |
| `t4-routine-chores.md` | .env.example, OpenAPI-экспорт, lint/format, run-доки, fixtures-sync | мелкие вспом. файлы (см. внутри) | в любой момент | bounded ClinePass · worker · `code` |

> **Шифт-влево:** монолитный `t1` (раньше — 3 модуля в одном файле «после b2/b7/b10») разнесён на
> инфраструктуру (`t1`) + per-feature `tu-*`. Каждый `tu-*` гонится сразу за своей backend-фичей,
> а не батчем в конце. Дозакрытие покрытия по **всем** `b1–b13` — пасс `w3-3` (Волна 3).

## Как запускать в Claude Code

Открыть worktree `feat/tests` отдельным окном VS Code (`code .worktrees/tests`), в панели Claude Code
дать промпт (`Выполни @prompts/v2-fullstack/wave-2-3-tests/track-t-tests/t1-backend-unit-tests.md`) и держать
`00-CONTRACT.md` в контексте. Перед прогоном подтянуть готовый код — **сначала закоммить свой результат**
(`git add -A && git commit`, секция `## Коммит`), затем `git fetch && git merge origin/integration`.

Тесты не пересекаются по файлам с продуктовыми треками → можно гнать параллельно и мержить чисто.
Барьер (`x4`/`x5`) перед `git merge feat/tests` проверяет, что worktree `tests` чист (GUARD) — незакоммиченные
тесты на барьер не попадут.
