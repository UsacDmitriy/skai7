# W3-3 · Backend unit-покрытие всего решения (дозакрытие t1)

> Волна 3 · хардненинг. Track **T** (Claude Code, `feat/tests`). Против `00-CONTRACT.md`
> **Модель:** 🔵 Sonnet — детерминированная логика/вёрстка против контракта; гейт = секция Check.
> §1–§3, §7.5. **Владеет:** `api/tests/unit/**` (новые файлы), `api/tests/conftest.py` (расширение фикстур).
> **Дополняет, а не дублирует** `track-t-tests/t1` (b2/b7/b10 уже покрыты — их не переписывать).
> **НЕ редактирует продуктовый код** — баг → дефект треку-владельцу. Гейт покрытия проверяется на Барьере 3 (x5).

## Цель

Довести unit-покрытие бэкенда до **всего набора модулей по промптам `b1–b13`** — детерминированно,
без сети и поднятого uvicorn. Каждый файл тестов привязан к промпту-источнику.

## Состав — по одному `test_*.py` на непокрытый модуль

`api/tests/unit/test_etl.py` (b1):
- ETL грузит ожидаемое число таблиц из `datasets/ready/**` (как в `b1`: ~41 таблица/6 папок).
- идемпотентность пересборки (`make db` дважды → одинаковая схема, без дублей строк).
- ключевые таблицы непусты: `alarms`>0, `alarm_type_catalog`=14, видеофайлы смаплены.

`api/tests/unit/test_v_incidents.py` (b3):
- `v_incidents` отдаёт 54 инцидента (§1.3); каждая строка несёт обязательные поля контракта §3.1.
- джойн с `alarm_type_catalog` не теряет строк (нет NULL в `source`/`severity` для известных кодов).

`api/tests/unit/test_conn_config.py` (b4):
- DuckDB-коннект read-only; `health` отдаёт ok; CORS/конфиг читаются из env с дефолтами.

`api/tests/unit/test_schemas.py` (b5):
- Pydantic-схемы §7.5 валидируют корректный объект и **отвергают** нарушающий enum
  (`Status`/`Source`/`Severity` вне допустимого → ValidationError).
- `Ticket` принимает `deadline:null` и `is_overdue:bool` (синхронно с W3-1).

`api/tests/unit/test_repos_services.py` (b5):
- `incidents_service.list/get/get_telemetry` на сэмпле: форма `IncidentDetail`, `TelemetryPoint[]`.
- `actions_service` пишет `output/actions.csv` с колонками `created_at,incident_id,action,comment`.

`api/tests/unit/test_stt.py` (b8):
- транскрипция: без `GROQ_API_KEY`/модели — корректный fallback-объект `{text,lang,confidence}`,
  детерминированный по входу; пустой/битый вход не роняет (graceful).

`api/tests/unit/test_nlu.py` (b9):
- regex-fallback парсит ФИО/госномер/период из «Нарушения Иванова за 3 дня» → `kind="driver"`;
  «отчёт по парку» → `kind="fleet"`; мусор → безопасный дефолт, не исключение.

`api/tests/unit/test_sabotage.py` (b11):
- правило саботажа: `dms_dark=true` И `speed_kmh>0` → событие; иначе нет (граничные значения).

`api/tests/unit/test_reb.py` (b12):
- детекция `gap_periods[]` из `navigation`: разрыв трека → период с началом/концом; непрерывный трек → пусто.

`api/tests/unit/test_tickets_alerts_trips.py` (b13 + W3-1):
- `list_tickets` без CSV → `[]`; дефолт `status="active"` (не `"new"`);
  `is_overdue=true` при `deadline<now И status∉{closed}`, иначе false.
- `get_alert` → `DispatchAlert{video_window_sec=15}`; неизвестный id → None.
- `get_trip` → `TripDossier{track,timeline}`; `has_video:bool` в timeline.

## Check

- `pytest api/tests/unit -q` зелёный; suite детерминирован (повторный прогон — тот же результат).
- Покрытие пакета `api/` ≥ **85%** (`pytest --cov=api api/tests/unit`), `api/core/enrichment.py` ≥ 90% (держим из t1).
- Ни один тест не требует сети/поднятого API; всё работает после `make db`.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**; незакоммиченная
работа в worktree на барьер не попадёт:

```bash
git add -A && git commit -m "w3-3: <что сделано>"
```
