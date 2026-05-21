# Промпт 1 — Git & Infra

Задача: синхронизировать репозиторий и проверить AI-инфраструктуру.

Рабочая директория: /Users/dimausac/Yandex.Disk.localized/SKAI/Хакатон/hackaton

1. Git:
   - Локальный репозиторий был переинициализирован и отстает от origin/main.
   - Выполни `git log origin/main --oneline -5` и `git log main --oneline -5`.
   - Если истории разошлись: сделай `git push --force` (согласовано с командой), либо создай новую ветку `hackathon-day` и push в нее.
   - Убедись, что `.gitignore` покрывает `.venv/`, `node_modules/`, `.DS_Store`, `frontend/dist/`.

2. Проверь `.codex/config.toml`:
   - Поле `model` — если там `gpt-5.3-codex`, замени на реально доступную модель (`o3`, `gpt-4.1`, `claude-sonnet-4-20250514` и т.д., уточни у команды).
   - Проверь путь `skills = [".agents/skills"]` — он должен указывать на существующую директорию.

3. Проверь `.mcp/config.json`:
   - Убедись, что все пути к SQLite/Postgres корректны для новой структуры (без `ml_ideas/`).
   - Удали или закомментируй MCP-серверы, которые не будут использоваться на хакатоне.

4. Проверь `.env.example`:
   - Добавь переменные для frontend (`VITE_API_URL=http://localhost:8000`).
   - Удали устаревшие ключи, если есть.

Результат: чистый `git status`, рабочий `.codex/config.toml`, актуальный `.env.example`.
