# Промпт 2 — Backend

Задача: превратить backend-заглушку в рабочий API для хакатона.

Рабочая директория: /Users/dimausac/Yandex.Disk.localized/SKAI/Хакатон/hackaton

1. Добавь в `backend/app/main.py` эндпоинты, которые читают мок-данные:
   - `GET /api/v1/incidents` → читать из `data/mock/incidents.json`
   - `GET /api/v1/fleet` → читать из `data/mock/fleet.json`
   - `GET /api/v1/incidents/{incident_id}` → возвращать конкретный инцидент или 404
   - `GET /api/v1/incidents/{incident_id}/report` → рендерить `templates/dtp_report.html` через WeasyPrint и отдавать PDF (Response с media_type="application/pdf")

2. Убедись, что `make start` из корня проекта запускает uvicorn:
   - Если в Makefile нет команды `start` или она устарела, добавь:
     ```makefile
     start:
         . .venv/bin/activate && uvicorn backend.app.main:app --reload --port 8000
     ```
   - Убедись, что `backend/__init__.py` существует (пустой файл), чтобы Python видел пакет.

3. Добавь CORS для фронтенда:
   ```python
   from fastapi.middleware.cors import CORSMiddleware
   app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"])
   ```

4. Запусти `make start` и проверь:
   - `curl http://localhost:8000/health`
   - `curl http://localhost:8000/api/v1/incidents`

Результат: работающий FastAPI на :8000, `make start` запускает его, фронтенд сможет стучаться.
