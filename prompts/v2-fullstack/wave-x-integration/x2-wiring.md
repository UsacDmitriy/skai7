# x2 · Склейка: роутеры, CORS, Vite-proxy, Makefile

> **Барьер-волна.** **Владеет:** `api/main.py` (include routers), `web/vite.config.ts` (proxy), `Makefile`.
> После b6 (роутеры существуют) и f1/f2 (фронт-каркас готов).

## Цель

Соединить треки в рабочий стек: бэкенд отдаёт все роутеры, фронт ходит на `/api` через dev-proxy, единые команды сборки/запуска.

## Задачи

1. **`api/main.py`** — подключить **ВСЕ** роутеры из пакета `api/routers` (P0 от b6 + P1/P2 от b11–b13:
   `sabotage`, `reb`, `tickets`, `alerts`, `trips`). Чтобы не редактировать общий список из разных волн —
   **авто-обход пакета** (каждый модуль экспортирует объект `router`):
   ```python
   import pkgutil, importlib
   import api.routers as routers_pkg
   for _, name, _ in pkgutil.iter_modules(routers_pkg.__path__):
       mod = importlib.import_module(f"api.routers.{name}")
       if hasattr(mod, "router"):
           app.include_router(mod.router)
   ```
   (Либо `ALL_ROUTERS` от b6, дополненный новыми — но авто-обход исключает конфликт владения
   `__init__.py` между b6 и b11–b13.) Проверить CORS на `http://localhost:5173` (из b4 settings).
2. **`web/vite.config.ts`** — `server.proxy`: `'/api' → http://localhost:8000` (target из env `VITE_API_TARGET`, дефолт 8000). Убрать TODO от f1.
3. **`Makefile`** — цели:
   - `db:` → `python -m api.etl.build_duckdb`
   - `api:` → `uvicorn api.main:app --reload --port 8000`
   - `web:` → `cd web && npm run dev`
   - `install:` → `pip install -r api/requirements.txt && cd web && npm install`
   - `dev:` → подсказка запустить `make api` и `make web` в двух терминалах (или `&`).

## Check

- `make db && make api` → `GET /api/incidents` отдаёт данные; `GET /api/health` ok.
- `make web`: фронт на :5173, запросы к `/api/...` проксируются на :8000 (нет CORS-ошибок).
- Карточка инцидента на :5173 грузит данные с живого бэка (без фикстур).
