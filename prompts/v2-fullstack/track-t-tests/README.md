# Codex-tasks — автотесты и рутина (для Codex desktop)

Промпты для **мелких/рутинных задач**, которые удобно гнать на Codex desktop параллельно основной
разработке в VS Code (Claude Code). Каждый — самодостаточен, кодит против `prompts/v2-fullstack/00-CONTRACT.md`.

> **Принцип владения:** эти задачи владеют **тестами и вспомогательными файлами** — НЕ продуктовым кодом.
> Тесты пишутся после того, как соответствующий трек создал код (или параллельно, на готовых модулях).
> Волны `x3`/`x4` только **запускают** pytest/vitest — авторство тестов здесь.

## Задачи

| Файл | Что делает | Владеет | Когда |
|---|---|---|---|
| `T1-backend-unit-tests.md` | pytest: enrichment, сиды, формулы (gross/risk/confidence/ax) | `api/tests/unit/**`, `api/tests/conftest.py`, `api/requirements-dev.txt` | после b2/b7/b10 |
| `T2-api-integration-tests.md` | pytest TestClient: все эндпоинты, коды, схемы | `api/tests/integration/**` | после b6 (P0) и b11–b13 (P1/P2) |
| `T3-frontend-tests.md` | vitest + RTL: UI-примитивы, api-клиент, экраны | `web/**/*.test.tsx`, `web/vitest.config.ts`, `web/src/test/**` | после d2/f2/f4 |
| `T4-routine-chores.md` | .env.example, OpenAPI-экспорт, lint/format, run-доки, fixtures-sync | мелкие вспом. файлы (см. внутри) | в любой момент |

## Как гнать на Codex desktop
Открыть отдельный git worktree (например `feat/tests`), вставить промпт + держать `00-CONTRACT.md` в контексте.
Тесты не пересекаются по файлам с продуктовыми треками → можно гнать параллельно и мержить чисто.
