#!/usr/bin/env bash
# Единая локальная CI-проверка «всё зелёное» перед коммитом (t4).
# Шаги: ruff (api+scripts) → pytest -q (backend) → web typecheck → vitest.
#
#   bash scripts/check.sh
#
# Первый упавший шаг прерывает прогон (exit != 0).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Python: .venv если есть, иначе python3.
if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
else
  PY="python3"
fi

# ruff: предпочитаем модуль текущего интерпретатора, иначе бинарь из PATH.
if "$PY" -m ruff --version >/dev/null 2>&1; then
  RUFF=("$PY" -m ruff)
elif command -v ruff >/dev/null 2>&1; then
  RUFF=(ruff)
else
  echo "✗ ruff не установлен ($PY -m pip install ruff)"; exit 1
fi

step() { printf '\n\033[1;36m==> %s\033[0m\n' "$1"; }

step "1/4 · ruff check api scripts"
"${RUFF[@]}" check api scripts

step "2/4 · pytest -q (api/tests)"
"$PY" -m pytest -q api/tests

step "3/4 · web · typecheck"
if [ ! -d web/node_modules ]; then
  echo "web/node_modules нет — ставлю зависимости (make install-web)…"
  (cd web && npm install)
fi
(cd web && npm run typecheck)

step "4/4 · web · vitest"
(cd web && npx vitest run)

printf '\n\033[1;32m✓ check.sh: всё зелёное\033[0m\n'
