# T1 · Backend unit — инфраструктура (pytest)

> Track T (Claude Code, `feat/tests`). Против `00-CONTRACT.md` §2/§7.1/§7.5.
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — детерминированная логика/вёрстка против контракта; гейт = секция Check.
> **Владеет:** `api/tests/conftest.py`, `api/requirements-dev.txt`, `api/tests/unit/__init__.py`.
> НЕ авторит сами `test_*.py` модулей — это делает per-feature слой `tu-*` (см. ниже).
> НЕ редактирует продуктовый код — при найденном баге заводит дефект треку.

## Цель

Заложить **общую инфраструктуру** backend-unit тестов, на которой стоят per-feature промпты `tu-*`:
быстрые тесты без сети и без поднятого API. Авторство тестов конкретных модулей вынесено в `tu-*`
(шифт-влево: каждый тест-промпт гонится сразу, как его backend-фича легла на `integration`).

## Состав

- `api/requirements-dev.txt`: `pytest`, `pytest-cov`.
- `api/tests/conftest.py`: общие фикстуры (in-memory/temp DuckDB на сэмпле, builder'ы строк),
  переиспользуемые всеми `tu-*` и `t2`.
- `api/tests/unit/__init__.py` + базовая раскладка `api/tests/unit/`.

## Per-feature unit-промпты (папка `per-feature/`)

Каждый владеет своим `test_*.py` и кодит против своего модуля:

| Промпт | Файл | Модуль | После |
|---|---|---|---|
| [`tu-enrichment`](per-feature/tu-enrichment.md) | `test_enrichment.py` | b2/b14 | b2/b14 на `integration` |
| [`tu-driver`](per-feature/tu-driver.md) | `test_seed_drivers.py` | b7 | b7 |
| [`tu-nlu`](per-feature/tu-nlu.md) | `test_nlu_fallback.py` | b9 | b9 |
| [`tu-reports`](per-feature/tu-reports.md) | `test_reports_rules.py` | b10 | b10 |
| [`tu-sabotage`](per-feature/tu-sabotage.md) | `test_sabotage.py` | b11 | b11 |
| [`tu-reb`](per-feature/tu-reb.md) | `test_reb.py` | b12 | b12 |

> Дозакрытие покрытия по **всем** модулям `b1–b13` (включая не охваченные `tu-*`) — пасс `w3-3`.

## Check

- `api/tests/conftest.py` импортируется; `pytest api/tests/unit -q` собирается (даже на пустом наборе).
- `pip install -r api/requirements-dev.txt` ставит `pytest`/`pytest-cov`.
- После прогона `tu-*`: `pytest api/tests/unit -q` зелёный, покрытие `api/core/enrichment.py` ≥ 90% (`--cov`).
- Тесты не требуют сети/поднятого uvicorn и проходят после `make db`.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**; незакоммиченная
работа в worktree на барьер не попадёт:

```bash
git add -A && git commit -m "t1: <что сделано>"
```
