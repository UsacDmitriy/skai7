# b4 · FastAPI-скелет, config, DuckDB-подключение

> Трек **Backend/Data**. Против `00-CONTRACT.md` §0/§3. **Владеет:**
> **Модель:** 🟢 Qwen 3.7 max — механическая транскрипция против точной спеки; гейт ловит ошибку.
> `api/main.py`, `api/core/config.py`, `api/core/duckdb_conn.py`, `api/requirements.txt`, `api/__init__.py` (+ `api/core/__init__.py`).
> Параллельно с b1/b2/b3.

## Цель

Базовый каркас FastAPI-приложения: настройки, подключение к DuckDB как зависимость, точка входа с
CORS и lifespan. Роутеры подключает b6/x2 — здесь только app и инфраструктура.

## Задачи

1. **`api/requirements.txt`**:
   ```text
   fastapi
   uvicorn[standard]
   duckdb
   pydantic>=2
   pydantic-settings
   pandas
   pytest
   httpx        # для тестов TestClient
   ```
2. **`api/core/config.py`** — `Settings(BaseSettings)`: `project_root`, `datasets_dir=datasets/ready`,
   `db_path=data/skai.duckdb`, `media_dir=datasets/media`, `output_dir=output`, `cors_origins=["http://localhost:5173"]`.
   Экземпляр `settings = Settings()`.
3. **`api/core/duckdb_conn.py`**:
   - `get_connection() -> duckdb.DuckDBPyConnection` — открывает `settings.db_path` **read-only**; кэш одного соединения на процесс (или пул по запросу). Если файла нет — понятная ошибка «запусти `make db`».
   - FastAPI-зависимость `def get_db()` (yield-зависимость) для роутеров.
4. **`api/main.py`**:
   - `create_app() -> FastAPI`; `app = create_app()`.
   - CORS middleware из `settings.cors_origins`.
   - `lifespan`: проверка наличия `db_path` на старте (warn если нет).
   - `GET /api/health` → `{"status":"ok"}`.
   - Заглушка-коммент `# routers подключаются в x2/b6`.
   - Запуск: `uvicorn api.main:app --reload`.

## Check

- `uvicorn api.main:app` стартует; `GET /api/health` → 200 `{"status":"ok"}`.
- `GET /docs` (OpenAPI) открывается.
- `from api.core.config import settings` и `from api.core.duckdb_conn import get_db` импортируются.
