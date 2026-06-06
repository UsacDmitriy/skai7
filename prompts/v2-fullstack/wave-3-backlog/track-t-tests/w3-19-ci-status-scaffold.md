# W3-19 · CI + статус-каркас: `.github/workflows/` + `gen_status.py` (подготовка Волны 4)

> Волна 3 · бэклог (**подготовка под Волну 4**). Трек **T (tests/CI/chores)**. Против `00-CONTRACT.md` §8.9.
> **Модель:** 🔵 Sonnet — пайплайн/скрипт против существующих make-целей; гейт = зелёный прогон.
> **Владеет:** `.github/workflows/ci.yml` (скелет), `scripts/gen_status.py` (скелет). Зеркалит `scripts/check.sh`.
> Разблокирует **t5** (CURRENT_STATUS) и **t6** (remote CI + nightly live-smoke) — они **дополняют** каркас. **Не блокирует** P0/P1/P2.

## Контекст (подтверждённые блокеры)

Нет каталога `.github/workflows/`, нет `scripts/gen_status.py`. t5/t6 (Волна 4.3) предполагают их наличие.
`scripts/check.sh` (единый локальный гейт ruff+pytest+typecheck+vitest) уже существует — CI обязан его зеркалить
(анти-дрейф локального и remote гейта).

## Что сделать

1. **`.github/workflows/ci.yml`** — рабочий **скелет** на PR/push: checkout → setup (python+node, кэш зависимостей)
   → `make install` (или эквивалент) → запуск **`scripts/check.sh`** (ruff + pytest + typecheck + vitest).
   Минимально-зелёный на чистом checkout. t6 расширяет (матрица/кэш/`make db`).
2. **`scripts/gen_status.py`** — **скелет** генератора `CURRENT_STATUS.md`: собирает список роутеров
   (`api/routers/*.py`) и SQL-вью/таблиц (`api/sql/*.sql`), пишет секции P0/P1/P2/Волна 3/Волна 4 с
   ✅/🟡/⬜. Детерминированный вывод (сорт по id), идемпотентно. t5 доводит до сверки с прогоном тестов.
   В шапке `CURRENT_STATUS.md` — «не редактировать вручную, источник — `gen_status.py`».
3. **Плейсхолдер `.github/workflows/.gitkeep`** не нужен (есть `ci.yml`). `nightly-smoke.yml` **не создаём** —
   это t6 (живой API). Скелеты помечены комментарием «расширяется t5/t6».

## Check

- `ci.yml` валиден (YAML парсится); прогон на чистом checkout зелёный (зеркало `scripts/check.sh`).
- `python scripts/gen_status.py` детерминированно создаёт `CURRENT_STATUS.md`; перечень роутеров/таблиц —
  из факта (`api/routers`/`api/sql`), не из README; повтор → идентично.
- Каталог `.github/workflows/` существует; `nightly-smoke.yml` отсутствует (создаёт t6).

## Коммит (обязательно)

```bash
git add -A && git commit -m "w3-19: CI + статус-каркас (ci.yml скелет + gen_status.py)"
```
