# SKAI — Makefile воркфлоу v2-fullstack (DuckDB + FastAPI + React/Vite)
# Источник истины по целям: prompts/v2-fullstack/00-CONTRACT.md §«Makefile»,
# wave-x-integration/x2-wiring.md, .worktrees/*/START.md, EXECUTION.md.

.PHONY: help install install-py install-web \
        db seed api web dev openapi \
        lint typecheck test test-api test-web check \
        worktrees worktrees-clean merge-integration clean

# ── Конфигурация ──────────────────────────────────────────────
PY        ?= $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)
PIP       := $(PY) -m pip
API_DIR   := api
WEB_DIR   := web
API_PORT  ?= 8000
WEB_PORT  ?= 5173
DUCKDB    := data/skai.duckdb

# ── Справка (по умолчанию) ────────────────────────────────────
help: ## Показать список команд
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Установка зависимостей ────────────────────────────────────
install: install-py install-web ## Установить всё (бэкенд + фронт)

install-py: ## Python-зависимости (api/requirements.txt)
	@[ -f $(API_DIR)/requirements.txt ] \
		&& $(PIP) install -r $(API_DIR)/requirements.txt \
		|| echo "Нет $(API_DIR)/requirements.txt — запусти промпт b4"

install-web: ## npm-зависимости (web/)
	@[ -f $(WEB_DIR)/package.json ] \
		&& (cd $(WEB_DIR) && npm install) \
		|| echo "Нет $(WEB_DIR)/package.json — запусти промпт f1"

# ── Данные / бэкенд (Track B) ─────────────────────────────────
db: ## Собрать DuckDB из datasets/ready (b1)
	$(PY) -m api.etl.build_duckdb

seed: ## Сгенерировать справочник водителей data/seed/ (b7) + датасет обучения (b31)
	$(PY) -m api.etl.seed_drivers
	$(PY) -m api.etl.seed_coaching

api: ## Запустить FastAPI на :$(API_PORT) (b4)
	@[ -f $(DUCKDB) ] || { echo "Нет $(DUCKDB) — сначала: make db"; exit 1; }
	$(PY) -m uvicorn api.main:app --reload --port $(API_PORT)

# ── Фронт (Track D/F) ─────────────────────────────────────────
web: ## Запустить Vite dev-сервер на :$(WEB_PORT) (f1)
	cd $(WEB_DIR) && npm run dev

dev: ## Подсказка: бэк + фронт в двух терминалах
	@echo "Запусти параллельно в двух терминалах:"
	@echo "  make api   → http://localhost:$(API_PORT)  (FastAPI)"
	@echo "  make web   → http://localhost:$(WEB_PORT)  (Vite)"

openapi: ## Выгрузить OpenAPI-схему в docs/openapi.json (t4)
	$(PY) scripts/export_openapi.py

# ── Качество / тесты (Codex T1–T3) ────────────────────────────
lint: ## ruff-проверка api/
	@$(PY) -m ruff check $(API_DIR) 2>/dev/null || echo "ruff не установлен: $(PIP) install ruff"

typecheck: ## tsc-проверка типов web/
	cd $(WEB_DIR) && npm run typecheck

test: test-api test-web ## Все тесты (pytest + vitest)

test-api: ## pytest бэкенда — api/tests (T1/T2)
	@[ -d $(API_DIR)/tests ] \
		&& $(PY) -m pytest $(API_DIR)/tests \
		|| echo "Нет $(API_DIR)/tests — запусти промпты T1/T2"

test-web: ## vitest фронта — web/**/*.test.tsx (T3)
	@[ -f $(WEB_DIR)/package.json ] \
		&& (cd $(WEB_DIR) && npm run test) \
		|| echo "Нет $(WEB_DIR)/package.json — запусти промпт f1"

check: lint typecheck test ## Полная проверка перед мержем

# ── Worktree / волны (EXECUTION.md) ───────────────────────────
worktrees: ## Создать .worktrees/{backend,web,tests} от integration
	@git show-ref --verify --quiet refs/heads/integration || git branch integration
	@for w in backend web tests; do \
		[ -d .worktrees/$$w ] && echo "уже есть: .worktrees/$$w" \
		|| git worktree add -b feat/$$w .worktrees/$$w integration; \
	done
	@echo "Открой каждую своим окном VS Code: code .worktrees/backend (и web, tests)"

merge-integration: ## Слить feat/* в integration (после волны)
	git checkout integration
	-git merge feat/backend
	-git merge feat/web
	-git merge feat/tests

worktrees-clean: ## Удалить .worktrees/* и ветки feat/*
	-@for w in backend web tests; do git worktree remove .worktrees/$$w 2>/dev/null; done
	-@git branch -d feat/backend feat/web feat/tests 2>/dev/null || true

# ── Очистка ───────────────────────────────────────────────────
clean: ## Очистить кеши (__pycache__, pytest, duckdb)
	@find . -type d -name __pycache__   -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@rm -f $(DUCKDB)
	@echo "==> Кеши и $(DUCKDB) удалены."
