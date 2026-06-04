# Prompts v2 — SKAI Full-Stack (DuckDB + FastAPI + React)

Промпты по волнам для пересборки SKAI как полноценного продукта: **DuckDB**-данные + **FastAPI**-бэкенд + **React/Vite/Tailwind**-фронт. Заменяет ранний Streamlit-прототип.

> **Правило:** один промпт = один файл. Каждый агент трогает только свои файлы.
> **Кодим против `00-CONTRACT.md`, а не против рантайма соседа** — поэтому треки идут параллельно.

## Стек

| Слой | Технологии |
|---|---|
| Данные | DuckDB (`data/skai.duckdb`) над CSV из `datasets/ready/` |
| Бэкенд | FastAPI + Pydantic v2 + uvicorn, пакет `api/` |
| Фронт | React + Vite + TypeScript + Tailwind, пакет `web/` |
| Тесты | pytest (бэк), vitest (фронт, по возможности) |

## Граф выполнения — 3 параллельных трека

```text
               ┌──────────── 00-CONTRACT.md ────────────┐
               │  поля инцидента · таблицы DuckDB ·       │
               │  v_incidents · enrichment · REST+схемы · │
               │  дизайн-токены  (источник истины)        │
               └────────────────────┬─────────────────────┘
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
   TRACK D (Design)           TRACK B (Backend/Data)        TRACK F (Frontend)
   d1 tailwind-theme          b1 duckdb-etl                 f1 vite-scaffold
   d2 ui-primitives           b2 enrichment                 f2 api-client
   d3 component-lib           b3 v-incidents                f3 mock-fixtures
                              b4 fastapi-scaffold           f4 screens
                              b5 schemas-repos-services
                              b6 routers
        └───────────────────────────┼───────────────────────────┘
                                     ▼
                      wave-x-integration (барьер)
                      x1 remove-streamlit · x2 wiring · x3 e2e-smoke
```

## Порядок запуска

1. **Барьер 1 — контракт.** Сначала зафиксировать `00-CONTRACT.md` (его пишет/проверяет ведущий, остальные читают). Без него треки не стартуют.
2. **Параллельная фаза.** Треки D, B, F запускаются одновременно. Внутри трека под-волны идут по нумерации (b1→b2→…), но файлы внутри одной под-волны не пересекаются и могут гнаться параллельно.
   - Зависимость только по контракту: фронт кодит против JSON-схем из контракта (+ фикстуры f3), дизайн — против токенов, бэк — против таблиц/схем. Никто не ждёт чужой рантайм.
3. **Барьер 2 — интеграция.** После завершения D/B/F запускается `wave-x-integration`: выпил Streamlit, склейка React↔FastAPI, сквозной smoke.

## Что переиспользуется из старых волн

| Источник | Что берём |
|---|---|
| `prompts/waves/wave-06-sqlite-backend/00-CONTRACT.md` | Имена таблиц `{prefix}__{csv}`, `alarm_type_catalog`, колонки `v_incidents` (портируем на DuckDB) |
| `init/context/DESIGN.md` | Дизайн-токены, компоненты, severity-палитра → Tailwind-тема |
| HTML-мокапы `ui/**`, `prompts/waves/wave-03-screens/**` | Референсы 3 P0-экранов: Карточка инцидента, Живой мониторинг, Интерактивный отчёт |
| `data/analysis/alarm_types.json` | Справочник 14 типов алярмов (raw→code→label_ru, severity, source) |
| `data/mock/incidents.py` | Эталонная форма объекта инцидента для API/фронта |

> ⚠️ **Deprecated:** `prompts/waves/wave-00a…wave-06` и Streamlit-`backend/` считаются архивом. Новый стек строится здесь. Отличие от wave-06: недостающие поля **обогащаются** (driver/model/risk_score), а не остаются NULL.

## Объём (scope)

- **Сквозной P0-домен `incidents` / `video_events`** — реализуется end-to-end через все треки (ETL → enrichment → v_incidents → repo → service → router → API-client → экран «Карточка инцидента» → тест).
- **fuel / sensors / navigation** — таблицы грузятся в DuckDB, но в API только скелет + `501 Not Implemented`; на фронте — заглушки.
- **Экраны Монитор / Отчёт** — scaffold (вёрстка из мокапов + заглушечные данные), без полного wiring.
