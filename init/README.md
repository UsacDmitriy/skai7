# SKAI Unified Incident Window

---

## Две ключевые идеи

### Идея #1 (P0) — Единое окно инцидента
→ `init/ideas/01-idea-unified-window.md`

Телематика + видео + CAN в одном экране.
Клик на событие → синхронное видео + график + действия.

**Реализация:** `prompts/v2-fullstack/` — контракт §3/§6, `track-f-frontend/f4-screens` (IncidentCard)

### Идея #2 (P0) — Интерактивный аналитический отчёт
→ `init/ideas/02-idea-interactive-report.md`

Голосом или текстом → подтверждение → дашборд.
Режим В-1 (один водитель) + Режим В-2 (парк, toggle По водителям|По ТС).

**Реализация:** `prompts/v2-fullstack/` — контракт §7.1–§7.4, `track-f-frontend/f7-analytics-voice`

---

## Структура папок

> ⚠️ data/mock/ — примеры старой структуры. Реальные данные: datasets/ready/*.csv

```
init/
  ideas/
    00-product-concept.md      ← общий концепт продукта
    01-idea-unified-window.md  ← Идея #1 подробно
    02-idea-interactive-report.md ← Идея #2 подробно
    03-customer-voice.md       ← голос клиента (интервью)
    04-competitors-analysis.md ← конкуренты
  context/
    product-context.md         ← продуктовый контекст для людей
    design-prompts.md          ← D-промпты для Claude Design
  playbook/00-day-plan.md      ← план разработки
  PITCH.md                     ← питч
  playbook/                    ← чеклисты, шаблоны, скрипт демо

prompts/
  v2-fullstack/               ← ДЕЙСТВУЮЩИЙ план (DuckDB+FastAPI+React)
    00-CONTRACT.md            ← источник истины (данные/API/токены/§7 full-scope)
    README.md                 ← граф волн и порядок запуска
    track-b-backend/          ← b1–b13 (ETL, enrichment, views, API, voice/NLU, driver)
    track-d-design/           ← d1–d5 (токены, UI-примитивы, карта, voice/timeline)
    track-f-frontend/         ← f1–f13 (клиент, экраны, лента/карта/отчёт/заявки/…)
    wave-x-integration/       ← x1–x3 (выпил Streamlit, склейка, e2e-smoke)
  init/                       ← discovery-промпт
  legacy/                     ← архив Streamlit-эры (setup 01–04, orchestration)
```

---

## Три экрана продукта

| # | Экран | Идея | Статус |
|---|-------|------|--------|
| 1 | Лента событий + Живой мониторинг | — | Макет готов |
| 2 | **Единое окно инцидента** | **#1 P0** | В разработке |
| 3 | **Интерактивный отчёт** (voice+NL+fleet) | **#2 P0** | Макет готов |
