# Барьер 2 · P1/P2 (промежуточные smoke + финал)

Основное окно `skai_7`, ветка `integration`, **последовательно**. `x2` (склейка) живёт в
`../barrier-1-integration-p0/` и переиспользуется. Схема — [`../EXECUTION.md`](../EXECUTION.md).

- **2.1 Reports/Voice:** `x2` (rewire) → `x4a-smoke-reports-voice.md` — `main` не трогает.
- **2.2 Прикладные:** `x2` (rewire, роутеры b11–b13 авто-обходом) → `x4b-smoke-applied-screens.md` — `main` не трогает.
- **2 финал:** `x2` → `x3` (P0-регресс) → `x4-e2e-p1p2.md` → `main` (ff).

```text
Выполни @prompts/v2-fullstack/barrier-2-p1p2/x4a-smoke-reports-voice.md
Выполни @prompts/v2-fullstack/barrier-2-p1p2/x4b-smoke-applied-screens.md
Выполни @prompts/v2-fullstack/barrier-2-p1p2/x4-e2e-p1p2.md
```
