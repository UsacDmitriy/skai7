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

## Граф выполнения — 3 параллельных трека (P0) + расширение (P1/P2)

```text
               ┌──────────── 00-CONTRACT.md ────────────┐
               │  поля инцидента · таблицы DuckDB ·       │
               │  v_incidents · enrichment · REST+схемы · │
               │  дизайн-токены · §7 full-scope (P1/P2)   │
               └────────────────────┬─────────────────────┘
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
   TRACK D (Design)           TRACK B (Backend/Data)        TRACK F (Frontend)
   d1 tailwind-theme          b1 duckdb-etl                 f1 vite-scaffold
   d2 ui-primitives           b2 enrichment                 f2 api-client
   d3 component-lib           b3 v-incidents                f3 mock-fixtures
   ── расширение (§7) ──       b4 fastapi-scaffold           f4 screens (IncidentCard)
   d4 map-primitives          b5 schemas-repos-services     ── расширение (§7) ──
   d5 voice-timeline          b6 routers                    f5 events-feed
                              ── расширение (§7) ──           f6 monitor-map *
                              b7 driver-reference            f7 analytics-voice *
                              b8 stt-service                 f8 tickets
                              b9 nlu-service                 f9 dispatch-alert
                              b10 reports-views              f10 trip-dossier
                              b11 sabotage                   f11 reb-recovery
                              b12 reb                        f12 sabotage
                              b13 tickets-alerts-trips       f13 role-toggle
        └───────────────────────────┼───────────────────────────┘
                                     ▼
                      wave-x-integration (барьер)
                      x1 remove-streamlit · x2 wiring · x3 e2e-smoke
```

> `*` f6/f7 заменяют scaffold-версии `Monitor.tsx`/`Report.tsx` из f4 (см. контракт §7.7).
> **Волна 1 — P0** = d1–d3 ‖ b1–b6 ‖ f1–f4 → x1–x3 (рабочее демо идей #1/#3).
> **Волна 2 — расширение (§7)** = d4–d5 ‖ b7–b13 ‖ f5–f13 — стартует после Барьера 1,
> сходится на x4 (повтор x2/x3 + P1/P2-smoke; идеи #2,#4–#10). Максимальный параллелизм — граница только по контракту.

## Порядок запуска

Единая схема: **Барьер 0 → Волна 1 → Барьер 1 → Волна 2 → Барьер 2** (подробности и команды — в `EXECUTION.md`).

1. **Барьер 0 — контракт.** Зафиксировать `00-CONTRACT.md` (его пишет/проверяет ведущий, остальные читают). Без него треки не стартуют.
2. **Волна 1 — параллельная фаза P0.** Треки D, B, F запускаются одновременно (b1→b6 ‖ d1→d3 ‖ f1→f4). Внутри трека под-волны идут по нумерации, но файлы внутри одной под-волны не пересекаются и могут гнаться параллельно.
   - Зависимость только по контракту: фронт кодит против JSON-схем из контракта (+ фикстуры f3), дизайн — против токенов, бэк — против таблиц/схем. Никто не ждёт чужой рантайм.
3. **Барьер 1 — интеграция P0.** После завершения D/B/F запускается `wave-x-integration`: x1 выпил Streamlit → x2 склейка React↔FastAPI → x3 сквозной smoke.
4. **Волна 2 — расширение P1/P2.** Параллельно: b7–b13 ‖ d4–d5 ‖ f5–f13 ‖ тесты T1–T3.
5. **Барьер 2 — финал.** x4 (P1/P2-smoke, повтор x2/x3) → merge в `main`.

## Что переиспользуется

| Источник | Что берём |
|---|---|
| `init/context/DESIGN.md` | Дизайн-токены, компоненты, severity-палитра → Tailwind-тема |
| HTML-мокапы `ui/**` (Карточка инцидента, Живой мониторинг, Интерактивный отчёт) | Референсы вёрстки P0/P1 экранов |
| `data/analysis/alarm_types.json` | Справочник 14 типов алярмов (raw→code→label_ru, severity, source) |
| `data/mock/incidents.py` | Эталонная форма объекта инцидента для API/фронта |
| `datasets/ready/**` | Реальные CSV (54 аларма, 94 MP4, треки, топливо, навигация) |

> ⚠️ **Архив:** ранняя Streamlit-`backend/`-реализация и старая wave-структура (`prompts/waves/`) удалены.
> Единственный действующий план разработки — этот каталог (`prompts/v2-fullstack/`). Legacy init-setup
> промпты Streamlit-эры лежат в `prompts/legacy/`. Отличие от старого подхода: недостающие поля
> **обогащаются** (driver/model/risk_score), а не остаются NULL.

## Объём (scope) — полный продукт P0+P1+P2

- **P0 — домен `incidents` / `video_events`** end-to-end (d1–d3 ‖ b1–b6 ‖ f1–f4): ETL → enrichment → v_incidents → repo → service → router → API-client → «Карточка инцидента» → тест.
- **Расширение (§7) — идеи #2,#4–#10**: реальные Voice/NLU (faster-whisper + Groq), справочник водителей `driver_reference`, отчёты В-1/В-2, лента/карта по ролям, заявки, диспетчерский алерт, видеодосье, РЭБ-восстановление, детекция саботажа. Промпты d4–d5 ‖ b7–b13 ‖ f5–f13.
- **fuel / sensors** — таблицы в DuckDB, в API скелет + `501`. `navigation` — теперь реализован как `/api/reb` (b12).
