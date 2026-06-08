# Барьер 4.3 · ФИНАЛ AI-слоя (Ops & Trust) → main

Финальный барьер Волны 4 (после под-волны 4.3). Выполняется в основном окне `skai_7` на ветке
`integration`. Содержит GUARD чистоты worktree; при зелёном e2e + полном регрессе Волны 4 +
**nightly live-smoke** — **продвигает `main`** (ff-only). x6/x7 `main` не трогали — это делает x8.

- `x8-ops-trust.md` — merge `feat/*` (GUARD) → e2e ops/trust (#18–#20: метрики/data-quality,
  risk-waterfall, security/CI/статус) + полный регресс Волны 4 (`scripts/check.sh`) + live-API smoke → `main`.

Схема — [`../EXECUTION.md`](../EXECUTION.md). Универсальный гейт — [`../barrier-CHECKLIST.md`](../barrier-CHECKLIST.md).
