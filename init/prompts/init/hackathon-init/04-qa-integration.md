# Промпт 4 — QA & Integration

Задача: убедиться, что вся инфраструктура работает вместе.

Рабочая директория: /Users/dimausac/Yandex.Disk.localized/SKAI/Хакатон/hackaton

1. Создай `tests/` в корне и добавь `tests/test_health.py`:
   ```python
   from fastapi.testclient import TestClient
   from backend.app.main import app
   client = TestClient(app)
   def test_health():
       r = client.get("/health")
       assert r.status_code == 200
       assert r.json() == {"status": "ok"}
   ```

2. Убедись, что `pytest` запускается из корня (`pytest` или `. .venv/bin/activate && pytest`).

3. Проверь `scripts/smoke.py` и `scripts/demo_flow.py`:
   - Запусти `make start` (бэкенд на :8000)
   - В другом терминале запусти `python scripts/smoke.py`
   - Если падает — залогируй ошибки и сообщи backend-разработчику, что нужно добавить/изменить в API.

4. Проверь `make demo`:
   - Если команда не существует или падает, исправь Makefile или сообщи команде.

5. Добавь в корень `.pre-commit-config.yaml` (опционально, если есть время):
   ```yaml
   repos:
     - repo: https://github.com/astral-sh/ruff-pre-commit
       rev: v0.4.0
       hooks:
         - id: ruff
         - id: ruff-format
   ```

Результат: `pytest` проходит, `make smoke` проходит (или есть четкий список, что нужно добавить в API).
