# TRACK T — тесты и рутина (Claude Code, worktree `feat/tests`)

Промпты для **тестов и вспомогательных файлов**, которые гонятся параллельно продуктовым трекам
(B/D/F) в отдельном окне Claude Code (worktree `.worktrees/tests` / ветка `feat/tests`).
Каждый промпт самодостаточен и кодит против `prompts/v2-fullstack/00-CONTRACT.md`.

> **Принцип владения:** трек владеет **тестами и вспомогательными файлами** — НЕ продуктовым кодом.
> Тесты пишутся после того, как соответствующий трек создал код (или параллельно, на готовых модулях).
> Барьеры `x3`/`x4` только **запускают** pytest/vitest — авторство тестов здесь.
> При найденном баге трек заводит дефект соответствующему треку (B/D/F), а не правит продуктовый код.

## Задачи

| Файл | Что делает | Владеет | Когда |
|---|---|---|---|
| `t1-backend-unit-tests.md` | pytest: enrichment, сиды, формулы (gross/risk/confidence/ax) | `api/tests/unit/**`, `api/tests/conftest.py`, `api/requirements-dev.txt` | после b2/b7/b10 |
| `t2-api-integration-tests.md` | pytest TestClient: все эндпоинты, коды, схемы | `api/tests/integration/**` | после b6 (P0) и b11–b13 (P1/P2) |
| `t3-frontend-tests.md` | vitest + RTL: UI-примитивы, api-клиент, экраны | `web/**/*.test.tsx`, `web/vitest.config.ts`, `web/src/test/**` | после d2/f2/f4 |
| `t4-routine-chores.md` | .env.example, OpenAPI-экспорт, lint/format, run-доки, fixtures-sync | мелкие вспом. файлы (см. внутри) | в любой момент |

## Как запускать в Claude Code

Открыть worktree `feat/tests` отдельным окном VS Code (`code .worktrees/tests`), в панели Claude Code
дать промпт (`Выполни @prompts/v2-fullstack/wave-2-3-tests/track-t-tests/t1-backend-unit-tests.md`) и держать
`00-CONTRACT.md` в контексте. Перед прогоном подтянуть готовый код:
`git fetch && git merge origin/integration`.

Тесты не пересекаются по файлам с продуктовыми треками → можно гнать параллельно и мержить чисто.
