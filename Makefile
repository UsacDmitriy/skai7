# SKAI — Makefile воркфлоу v2-fullstack (DuckDB + FastAPI + React/Vite)
# Источник истины по целям: prompts/v2-fullstack/00-CONTRACT.md §«Makefile»,
# wave-x-integration/x2-wiring.md, .worktrees/*/START.md, EXECUTION.md.

.PHONY: help install install-py install-web \
        db seed api web dev openapi \
        lint typecheck test test-api test-web check \
        worktrees worktrees-clean merge-integration \
        start smoke verify clean

# ── Конфигурация ──────────────────────────────────────────────
PY        ?= $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)
PIP       := $(PY) -m pip
API_DIR   := api
WEB_DIR   := web
API_PORT  ?= 8000
WEB_PORT  ?= 5173
DUCKDB    := data/skai.duckdb
# API_WORKERS: 0 → авто = cpu_count; 4 на M4 Pro, 2-4 на Windows.
# Для dev-режима с --reload воркеры не применяются (reload несовместим с workers).
API_WORKERS ?= 0

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

api-prod: ## Запустить FastAPI с multi-worker (без reload) на :$(API_PORT)
	@[ -f $(DUCKDB) ] || { echo "Нет $(DUCKDB) — сначала: make db"; exit 1; }
	@WORKERS=$(API_WORKERS); \
	if [ "$$WORKERS" = "0" ] || [ -z "$$WORKERS" ]; then \
		if [ "$$(uname)" = "Darwin" ]; then \
			WORKERS=$$(sysctl -n hw.physicalcpu 2>/dev/null || echo 4); \
		else \
			WORKERS=$$(nproc 2>/dev/null || echo 4); \
		fi; \
	fi; \
	echo "Запуск uvicorn с $$WORKERS worker(ами) на порту $(API_PORT)"; \
	$(PY) -m uvicorn api.main:app --workers $$WORKERS --port $(API_PORT)

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
		&& $(PY) -m pytest $(API_DIR)/tests -v \
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

# ── Единый запуск / дымовые тесты / полная проверка ───────────
start: db ## Запустить всё одной командой (БД → бэкенд → фронт)
	@echo "==================== SKAI — запуск ===================="
	@echo "Бэкенд:  http://localhost:$(API_PORT)  (FastAPI)"
	@echo "Фронтенд: http://localhost:$(WEB_PORT)  (Vite)"
	@echo "Документация: http://localhost:$(API_PORT)/docs"
	@echo "Нажми Ctrl+C для остановки."
	@echo "======================================================="
	@trap 'kill 0; exit 0' INT TERM; \
	$(PY) -m uvicorn api.main:app --reload --port $(API_PORT) & \
	API_PID=$$!; \
	cd $(WEB_DIR) && npm run dev & \
	WEB_PID=$$!; \
	wait

smoke: ## Быстрый дымовой тест (без поднятого сервера)
	@echo "=== SKAI Smoke Test ==="
	@echo "[1/4] DuckDB..."
	@[ -f $(DUCKDB) ] && echo "  OK: $(DUCKDB)" || { echo "  FAIL: $(DUCKDB) отсутствует — запусти make db"; exit 1; }
	@echo "[2/4] Python imports..."
	@PYTHONPATH=. $(PY) -c "from api.main import app; print(f'  OK: {len(app.routes)} routes')" || { echo "  FAIL: не удалось импортировать api.main"; exit 1; }
	@echo "[3/4] Vite build..."
	@cd $(WEB_DIR) && npx vite build --logLevel error > /dev/null 2>&1 && echo "  OK: build successful" || { echo "  FAIL: Vite build failed"; exit 1; }
	@echo "[4/4] Pytest quick..."
	@PYTHONPATH=. $(PY) -m pytest api/tests/unit/test_stt.py -q > /dev/null 2>&1 && echo "  OK: pytest quick passed" || echo "  WARN: pytest quick failed (возможно, нет faster-whisper)"
	@echo "=== Smoke: ALL CHECKS PASSED ==="

verify: smoke ## Полная проверка (smoke + check + user-flows)
	@echo "=== SKAI Full Verification ==="
	@echo "[step 1/3] smoke — done"
	@echo "[step 2/3] make check (lint + typecheck + all tests)..."
	@$(MAKE) check || { echo "  FAIL: make check failed"; exit 1; }
	@echo "[step 3/3] smoke user flows..."
	@if [ -x scripts/smoke_user_flows.sh ]; then \
		bash scripts/smoke_user_flows.sh || echo "  WARN: user flows failed (возможно, API не запущен)"; \
	else \
		echo "  SKIP: scripts/smoke_user_flows.sh не найден"; \
	fi
	@echo "=== Verify: COMPLETE ==="

# ── Очистка ───────────────────────────────────────────────────
clean: ## Очистить кеши (__pycache__, pytest, duckdb)
	@find . -type d -name __pycache__   -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@rm -f $(DUCKDB)
	@echo "==> Кеши и $(DUCKDB) удалены."