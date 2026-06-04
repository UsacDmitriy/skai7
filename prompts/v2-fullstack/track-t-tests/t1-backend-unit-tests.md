# T1 · Backend unit-тесты (pytest)

> Track T (Claude Code, `feat/tests`). Против `00-CONTRACT.md` §2 (enrichment), §7.1 (сиды), §7.5 (gross/disciplinary).
> **Владеет:** `api/tests/unit/**`, `api/tests/conftest.py`, `api/requirements-dev.txt`.
> Запускается после b2/b7/b10. НЕ редактирует продуктовый код — при найденном баге заводит дефект треку.

## Цель
Покрыть детерминированную бизнес-логику unit-тестами (быстрые, без сети, без поднятого API).

## Состав

`api/requirements-dev.txt`: `pytest`, `pytest-cov`.
`api/tests/conftest.py`: фикстуры (in-memory/temp DuckDB на сэмпле, общие builder'ы строк).

`api/tests/unit/test_enrichment.py` (модуль b2):
- `risk_score` ∈ [0,100], монотонность по severity (critical>high>medium>low при прочих равных).
- `is_night` истинно для часов [22,06) UTC, ложно иначе.
- `ax` = производная скорости: на росте скорости `ax>0`, на падении `ax<0`, не тождественный ноль.
- `speed_limit_for(code)` по таблице (DMS/городские → 60, иначе 90).
- `confidence` детерминирован по `id` (один вход → один выход) и на `requires_video=false`/нет видео ниже на 10.
- `cameras[]`: статусы online/warning/offline по `download_status`; длина 3 канонических.
- `evidence_summary`/`event_version` непусты для известных `alarm_code`.

`api/tests/unit/test_seed_drivers.py` (модуль b7):
- `seed_drivers` идемпотентен (два запуска → идентичный CSV).
- `driver_reference`: ровно 1 строка на `vehicle_plate`; `safety_score` ∈ [0,100]; пул ФИО ≥20, регионов ≥5.
- `driver_trips`: 1–2 водителя на ТС, ровно один `role="main"`.

`api/tests/unit/test_reports_rules.py` (модуль b10):
- `is_gross`: true для `severity=critical` и для `alarm_code ∈ {OVERSPEED, DMS_SMOKING}`, иначе false.
- `disciplinary_warning`: true при `gross>=3` ИЛИ `safety_score<60`, иначе false.
- `ReportKPI` суммы согласованы (`total >= video_da`, `total >= telematics`).

## Check
- `pytest api/tests/unit -q` зелёный; покрытие `api/core/enrichment.py` ≥ 90% (`--cov`).
- Тесты не требуют сети/поднятого uvicorn и проходят после `make db`.
