# Барьер 5.2 · Coaching Loop → main

Барьер под-волны 5.2 (после x10). Выполняется в основном окне `skai_7` на ветке `integration`.
GUARD чистоты worktree; при зелёном e2e цикла обучения + **полном регрессе** — **продвигает `main`**
(ff-only, паттерн x9/x10).

- `x11-coaching.md` — merge `feat/*` (GUARD) → e2e #24 (датасет → `/api/coaching` → секция отчёта,
  бейдж синтетики) + негативы §12.4 + полный регресс (`scripts/check.sh`) → `main`.

Схема — [`../EXECUTION.md`](../EXECUTION.md). Универсальный гейт — [`../barrier-CHECKLIST.md`](../barrier-CHECKLIST.md).
