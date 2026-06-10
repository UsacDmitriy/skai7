# Барьер 5.1 · Review Queue → main

Барьер под-волны 5.1 (после x9). Выполняется в основном окне `skai_7` на ветке `integration`.
GUARD чистоты worktree; при зелёном e2e очереди верификации + **полном регрессе** — **продвигает
`main`** (ff-only, паттерн x9: каждая под-волна Волны 5 — самостоятельный стабильный инкремент).

- `x10-review-queue.md` — merge `feat/*` (GUARD) → e2e #23 (`/api/review-queue`, экран `/validation`,
  журнал, перезапись статуса) + негативы §11.4 + полный регресс (`scripts/check.sh`) → `main`.

Схема — [`../EXECUTION.md`](../EXECUTION.md). Универсальный гейт — [`../barrier-CHECKLIST.md`](../barrier-CHECKLIST.md).
