# Барьер 1 · интеграция P0

Основное окно `skai_7`, ветка `integration`, **последовательно**. Git-склейка — внутри промптов
(x1 сам вливает `main`+`feat/backend`+`feat/web`, x3 продвигает `main`). Схема — [`../EXECUTION.md`](../EXECUTION.md).

```text
Выполни @prompts/v2-fullstack/barrier-1-integration-p0/x1-remove-streamlit.md
Выполни @prompts/v2-fullstack/barrier-1-integration-p0/x2-wiring.md
Выполни @prompts/v2-fullstack/barrier-1-integration-p0/x3-e2e-smoke.md
```

- `x1` — выпил Streamlit + склейка веток (вариант «а»: `--no-ff main`).
- `x2` — связка React↔FastAPI: авто-обход роутеров, vite-proxy, Makefile (переиспользуется и в Барьере 2).
- `x3` — сквозной e2e-smoke P0 → `main` (ff). Красный → стоп, дефект трека.
