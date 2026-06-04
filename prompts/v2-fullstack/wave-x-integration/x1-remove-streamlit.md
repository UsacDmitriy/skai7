# x1 · Выпил Streamlit

> **Барьер-волна** (после D/B/F). **Владеет:** удалением Streamlit-артефактов + `requirements.txt`, `.gitignore`, `.streamlit/`.
> Запускать ПОСЛЕ того как `api/` (трек B) и `web/` (трек F) готовы и проходят свои check.

## Цель

Убрать ранний Streamlit-прототип, не задев новые `api/` и `web/` и реальные данные.

## Удалить

- `backend/` (весь Streamlit-пакет: app.py, screens/, components/, charts.py, metrics.py, risk_table.py, data_loader.py, …).
- `run.py`, корневой Streamlit-`main.py` (если импортирует `backend.app`).
- `.streamlit/`, `ui/` (HTML-мокапы — перенести нужные в `prompts/v2-fullstack/_refs/` ДО удаления, если ещё нужны как референс; иначе оставить в git-истории).
- `output/` сохранить (туда пишет actions), `data/`, `datasets/`, `sample_data/` — **НЕ трогать**.

## Изменить

- **`requirements.txt`** (корневой): убрать `streamlit`, `altair`, `faster-whisper`; оставить ссылку на `api/requirements.txt` или продублировать fastapi/uvicorn/duckdb/pydantic. (faster-whisper вернётся позже для NLU — пометить `# TODO`.)
- **`.gitignore`**: убрать `data/skai.db*`, добавить `data/skai.duckdb`, `web/node_modules`, `web/dist`, `.venv` (если ещё нет).

## Осторожно

- Перед удалением проверить, что ничто в `api/`/`web/` не импортирует `backend.*`.
- Не удалять `data/mock/` и `data/analysis/` — на них опираются фикстуры/каталог.

## Check

- `grep -r "import streamlit" .` (вне .venv/архивных prompts) — пусто.
- `grep -rn "from backend" api/ web/` — пусто.
- Реальные данные (`datasets/`, `data/analysis/`, `output/`) на месте.
