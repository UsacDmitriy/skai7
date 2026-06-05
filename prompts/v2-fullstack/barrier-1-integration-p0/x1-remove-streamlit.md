# x1 · Выпил Streamlit

> **Барьер-волна** (после D/B/F). **Владеет:** удалением Streamlit-артефактов + `requirements.txt`, `.gitignore`, `.streamlit/`.
> Запускать ПОСЛЕ того как `api/` (трек B) и `web/` (трек F) готовы и проходят свои check.

## Перед стартом — склейка веток (main держим стабильным)

Барьеры идут в основном окне `skai_7` на ветке `integration`. **`main` не трогаем**, пока сквозной
smoke не станет зелёным (продвижение `main` — в x3 для P0 и x4 для P1/P2).

```bash
cd /Users/dimausac/projects/skai_7
git checkout integration
git merge --no-ff main -m "merge main (docs/мокапы/f2) → integration"   # вариант «а»: main разошёлся во время волн
git merge feat/backend feat/web   # подтянуть готовые треки волны 1 (B и F)
```

> **Вариант «а» (почему сначала `main`):** во время волн в `main` попали прямые коммиты
> (docs, ui-мокапы, протёкший f2 `web/src/api/*`) → `main` и `integration` разошлись. Вливаем `main`
> в `integration` обычным merge-коммитом — после этого `main` становится предком `integration`,
> и финальный `git merge --ff-only integration` (x3) снова проходит fast-forward.
> Конфликт по `web/src/api/*` разрешаем в пользу `feat/web` (там канон f2/f3).

Слияние должно пройти без конфликтов (`git status` чисто). Конфликт → разрулить в `integration`, `main` не затрагивая.

## Проверка предыдущего шага (волна 1: треки B + F)

До выпила Streamlit убедись, что новые треки здоровы на свежесклеенной `integration`:

- backend: `make db` (54 аларма / 14 типов + `v_incidents`), `make api` → `GET /api/incidents` 200 с обогащением.
- frontend: `cd web && npm install && npm run typecheck` без ошибок; `npm run dev` поднимает :5173.

Если что-то падает — **стоп**: заведи дефект соответствующему треку, Streamlit не удаляй, пока B/F не зелёные.

## Цель

Убрать ранний Streamlit-прототип, не задев новые `api/` и `web/` и реальные данные.

## Удалить

- `backend/` (весь Streamlit-пакет: app.py, screens/, components/, charts.py, metrics.py, risk_table.py, data_loader.py, …).
- `run.py`, корневой Streamlit-`main.py` (если импортирует `backend.app`).
- `.streamlit/` (Streamlit-конфиг).
- **`ui/` НЕ удалять** — это актуальные HTML-мокапы Claude Design (10 экранов), визуальный референс для Волны 2 (`f5–f13`). Трогать только Streamlit-артефакты.
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
