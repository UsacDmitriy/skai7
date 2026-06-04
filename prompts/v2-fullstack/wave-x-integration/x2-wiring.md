# x2 · Склейка: роутеры, CORS, Vite-proxy, Makefile

> **Барьер-волна.** **Владеет:** `api/main.py` (include routers), `web/vite.config.ts` (proxy), `Makefile`.
> После b6 (роутеры существуют) и f1/f2 (фронт-каркас готов).

## Цель

Соединить треки в рабочий стек: бэкенд отдаёт все роутеры, фронт ходит на `/api` через dev-proxy, единые команды сборки/запуска.

## Задачи

1. **`api/main.py`** — подключить роутеры из `api/routers` (`ALL_ROUTERS` от b6):
   ```python
   from api.routers import ALL_ROUTERS
   for r in ALL_ROUTERS:
       app.include_router(r)
   ```
   Проверить, что CORS уже включает `http://localhost:5173` (из b4 settings).
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
