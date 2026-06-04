.PHONY: help install clean lint test

PYTHON := .venv/bin/python
PIP := .venv/bin/pip

help: ## Показать список команд
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install: ## Установить зависимости
	$(PIP) install -r requirements.txt

clean: ## Очистить кеш и __pycache__
	@echo "==> Очистка кеша..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "==> Кеш очищен."

lint: ## Проверить код ruff (если установлен)
	@which .venv/bin/ruff >/dev/null 2>&1 && .venv/bin/ruff check backend/ || echo "ruff не установлен: pip install ruff"

test: ## Запустить тесты (если есть)
	@which .venv/bin/pytest >/dev/null 2>&1 && .venv/bin/pytest || echo "pytest не установлен: pip install pytest"
