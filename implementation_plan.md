# Implementation Plan

[Overview]
Оптимизация производительности бэкенда (FastAPI + DuckDB) и фронтенда (Vite/React) под Apple Silicon M4 Pro (12 ядер, 24 GB) и Windows x86 с кросс-платформенными настройками.

Задача — поднять утилизацию CPU с текущих 5-10% до 60-80% при нагрузке, ускорить инференс Whisper в 2-3x (Mac), ускорить параллельные SQL-запросы DuckDB на 30-50%, сократить время холодного старта фронтенда.

[Types]
Без изменений типов. Новые поля конфигурации уже добавлены в `api/core/config.py` (whisper_compute_type, whisper_cpu_threads, whisper_num_workers). Добавляются поля: `duckdb_threads`, `duckdb_memory_limit_mb`, `api_workers`.

[Files]
Создаются: `implementation_plan.md` (этот файл). Модифицируются: `Makefile` (uvicorn workers + prod-цель), `api/core/duckdb_conn.py` (PRAGMA threads/memory_limit), `web/vite.config.ts` (pre-bundling deps), `api/core/config.py` (новые поля duckdb_threads/api_workers), `.env.example` и `.env` (новые переменные).

[Functions]
- `duckdb_conn.py::get_connection()` — добавить `PRAGMA threads=N; PRAGMA memory_limit='XGB'` после connect
- `Makefile::api` — заменить `uvicorn --reload` на `uvicorn --workers $(API_WORKERS) --reload`
- `Makefile` — добавить цель `api-prod` без `--reload`, с воркерами
- `vite.config.ts` — добавить `optimizeDeps.include` для recharts, leaflet, lucide-react

[Classes]
Без изменений классов.

[Dependencies]
Без новых зависимостей. Для Apple Accelerate (опционально): переустановка numpy через `pip install numpy --config-settings=setup-args="-Daccelerate=blas"`. Для faster-whisper CoreML (опционально): установка `ctranslate2` с CoreML-бэкендом.

[Testing]
- Валидация: `make api` запускается без ошибок
- Проверка DuckDB PRAGMAs: `python -c "from api.core.duckdb_conn import get_connection; c=get_connection(); print(c.execute('SELECT current_setting(\"threads\")').fetchone())"`
- Проверка uvicorn workers: `ps aux | grep uvicorn` должен показать N процессов
- Vite build: `make web` должен собраться без ошибок

[Implementation Order]
1. `api/core/config.py` — добавить поля `api_workers`, `duckdb_threads`, `duckdb_memory_limit_mb`
2. `api/core/duckdb_conn.py` — добавить PRAGMA threads/memory_limit
3. `Makefile` — uvicorn workers + api-prod цель
4. `.env.example` + `.env` — новые переменные с кросс-платформенными значениями
5. `web/vite.config.ts` — optimizeDeps для production build
6. Валидация всех изменений
7. Git commit + push