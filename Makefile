.PHONY: help install run dev clean lint test

PYTHON := .venv/bin/python
STREAMLIT := .venv/bin/streamlit
PIP := .venv/bin/pip

APP_ENTRY := run.py
APP_PORT := 8501

help: ## Показать справку по командам
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости в .venv
	@echo "==> Установка зависимостей..."
	$(PIP) install -r requirements.txt
	@echo "==> Готово."

run: ## Запустить Streamlit-приложение (production mode)
	@echo "==> Запуск SKAI Единое окно на http://localhost:$(APP_PORT)"
	$(STREAMLIT) run $(APP_ENTRY) --server.port=$(APP_PORT) --server.headless=true

dev: ## Запустить Streamlit-приложение в dev-режиме (auto-reload)
	@echo "==> Запуск SKAI в dev-режиме на http://localhost:$(APP_PORT)"
	$(STREAMLIT) run $(APP_ENTRY) --server.port=$(APP_PORT) --server.runOnSave=true --server.fileWatcherType=poll

clean: ## Очистить кеш Streamlit и __pycache__
	@echo "==> Очистка кеша..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf .streamlit/cache 2>/dev/null || true
	@echo "==> Кеш очищен."

lint: ## Проверить код ruff (если установлен)
	@which .venv/bin/ruff >/dev/null 2>&1 && .venv/bin/ruff check backend/ || echo "ruff не установлен: pip install ruff"

test: ## Запустить тесты (если есть)
	@which .venv/bin/pytest >/dev/null 2>&1 && .venv/bin/pytest || echo "pytest не установлен: pip install pytest"
