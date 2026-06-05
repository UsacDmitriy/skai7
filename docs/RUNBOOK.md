# RUNBOOK — запуск и проверка SKAI (DuckDB + FastAPI + React/Vite)

Пошаговый прогон проекта от чистого клона до зелёных тестов. Источник истины по
целям — корневой [`Makefile`](../Makefile) и [`00-CONTRACT.md`](../prompts/v2-fullstack/00-CONTRACT.md).

## 0. Предпосылки

| Инструмент | Версия | Зачем |
|---|---|---|
| Python | 3.12 | backend (FastAPI, DuckDB, pydantic v2) |
| Node.js | ≥ 18 | frontend (Vite 5) |
| make | — | единая точка входа по целям |

## 1. Установка зависимостей

```bash
make install            # = install-py (api/requirements.txt) + install-web (npm install в web/)
```

Раздельно при необходимости:

```bash
make install-py         # pip install -r api/requirements.txt
make install-web        # cd web && npm install
```

> Рекомендуется venv: `python3.12 -m venv .venv && source .venv/bin/activate`.
> `Makefile` сам подхватит `.venv/bin/python`, если он есть (переменная `PY`).

## 2. Переменные окружения

```bash
cp .env.example .env     # затем заполни значения
```

| Переменная | Дефолт | Назначение |
|---|---|---|
| `GROQ_API_KEY` | пусто | NLU через Groq; пусто → локальный regex-fallback (без сети) |
| `WHISPER_MODEL` | `large-v3` | STT-модель faster-whisper |
| `WHISPER_DEVICE` | `cpu` | устройство STT |
| `VITE_API_BASE` | `/api` | префикс API-клиента фронта |
| `VITE_API_TARGET` | `http://localhost:8000` | цель Vite-proxy для `/api` в dev |
| `VITE_USE_FIXTURES` | `false` | `true` → фронт на статичных фикстурах f3, без бэка |

Backend читает настройки через `api/core/config.py` (pydantic-settings, префикс `SKAI_`).

## 3. Сборка базы данных

```bash
make db                 # python -m api.etl.build_duckdb → data/skai.duckdb
make seed               # python -m api.etl.seed_drivers → таблица driver_reference
```

- Артефакт БД: `data/skai.duckdb` (в `.gitignore`, пересобирается из CSV).
- Источник CSV: `datasets/ready/**` + справочник `data/analysis/alarm_types.json`.
- Сиды водителей (в git): `data/seed/driver_reference.csv`, `data/seed/driver_trips.csv`.

## 4. Запуск (два терминала)

```bash
make api                # FastAPI на http://localhost:8000 (uvicorn --reload)
make web                # Vite dev на http://localhost:5173
```

`make dev` печатает эту подсказку. Фронт ходит на `/api` через Vite-proxy (CORS не нужен).

- Health-check: `curl http://localhost:8000/api/health` → `{"status":"ok"}`.
- Swagger UI: <http://localhost:8000/docs>. OpenAPI-схема: `make openapi` → `docs/openapi.json`.

## 5. Где какие данные

| Путь | Содержимое |
|---|---|
| `datasets/ready/**` | канонические CSV (video_events, fuel, sensors, navigation…) |
| `data/analysis/alarm_types.json` | справочник типов алярмов (14 строк) |
| `data/seed/*.csv` | детерминированные сиды водителей |
| `data/mock/incidents.py` | эталон формы инцидентов (для фикстур f3) |
| `data/skai.duckdb` | собранная БД (генерируется, не в git) |
| `output/actions.csv` | журнал действий (создаётся при `POST /api/actions`) |
| `datasets/media/**` | MP4 (тяжёлые, не в git) |

## 6. Тесты (T1–T3)

```bash
make test               # всё: test-api + test-web
make test-api           # pytest api/tests        (T1/T2 — backend unit/integration)
make test-web           # cd web && npm run test   (T3 — vitest)
make typecheck          # cd web && tsc --noEmit
make lint               # ruff check api
```

Единый «всё зелёное» перед коммитом:

```bash
bash scripts/check.sh   # ruff + pytest -q + typecheck + vitest
```

## 7. Типичные ошибки

| Симптом | Причина / решение |
|---|---|
| `Нет data/skai.duckdb — сначала: make db` | БД не собрана → `make db` |
| `ruff не установлен` / `pytest: command not found` | не активирован venv или `make install-py` не выполнен |
| `npm run typecheck`/`vitest` падает с «cannot find module» | не выполнен `make install-web` (нет `web/node_modules`) |
| Фронт показывает пустые экраны без бэка | подними `make api` **или** выставь `VITE_USE_FIXTURES=true` |
| `502/404` на `/api/...` в dev | не запущен backend, либо неверный `VITE_API_TARGET` |
| STT/NLU не отвечают онлайн | нет `GROQ_API_KEY` → работает regex/локальный fallback (это норма для демо) |
| Видео не проигрывается | `<video src>` биндить нельзя на `cam_*_url`; источник — `GET /api/incidents/{id}/video/{channel}` (00-CONTRACT §6) |
