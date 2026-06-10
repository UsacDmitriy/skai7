# Барьер 4.4 · Data Trust → main

Барьер Волны 4.4 (после финала Волны 4 — x8 уже продвинул `main`). Выполняется в основном окне `skai_7`
на ветке `integration`. Содержит GUARD чистоты worktree; при зелёном e2e Data Trust + **полном регрессе**
(P0–P2 + Волны 3/4.1/4.2/4.3) — **повторно продвигает `main`** (ff-only, тот же паттерн финализации, что x8).

- `x9-data-trust.md` — merge `feat/*` (GUARD) → e2e фич #21/#22 (`/api/consistency`, `/speed-check`,
  бейдж + панель) + негативы §10.5 + полный регресс (`scripts/check.sh`) → `main`.

Схема — [`../EXECUTION.md`](../EXECUTION.md). Универсальный гейт — [`../barrier-CHECKLIST.md`](../barrier-CHECKLIST.md).
