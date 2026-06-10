# Барьер 5.3 · Driver Value → main (финал Волны 5)

Финальный барьер Волны 5 (после x11). Выполняется в основном окне `skai_7` на ветке `integration`.
GUARD чистоты worktree; при зелёном e2e скоринга + **полном регрессе** — **продвигает `main`**
(ff-only, паттерн x9/x10/x11).

- `x12-driver-value.md` — merge `feat/*` (GUARD) → e2e #25/#26 (`/api/positive-score`,
  `/api/driver-score`, `/leaderboard`, блок позитива в отчёте) + инвариант бленда §13.2 +
  полный регресс (`scripts/check.sh`) → `main`.

Схема — [`../EXECUTION.md`](../EXECUTION.md). Универсальный гейт — [`../barrier-CHECKLIST.md`](../barrier-CHECKLIST.md).
