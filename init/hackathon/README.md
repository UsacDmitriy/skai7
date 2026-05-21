# Хакатон — SKAI Unified Incident Window

**Дата:** 21 мая 2026 · 8 часов · Команда 7, Тема 5

---

## Две ключевые идеи

### Идея #1 (P0) — Единое окно инцидента
→ `hackathon/ideas/01-idea-unified-window.md`

Телематика + видео + CAN в одном экране.
Клик на событие → синхронное видео + график + действия.

**Дизайн:** `design-prompts/claude-design/03-idea1-incident-video.md`
**Код:** `prompts/hackathon/wave-03-screens/P3-03B-incident-card--kimi-k2.6.md`

### Идея #2 (P0) — Интерактивный аналитический отчёт
→ `hackathon/ideas/02-idea-interactive-report.md`

Голосом или текстом → подтверждение → дашборд.
Режим В-1 (один водитель) + Режим В-2 (парк, toggle По водителям|По ТС).

**Дизайн:** `design-prompts/claude-design/05-idea2-interactive-report.md`
**Код:** `prompts/hackathon/wave-03-screens/P2-03D-analytics-screen--kimi-k2.6.md`

---

## Структура папок

> ⚠️ data/mock/ — примеры старой структуры. Реальные данные: datasets/ready/*.csv

```
hackathon/
  ideas/
    00-product-concept.md      ← общий концепт продукта
    01-idea-unified-window.md  ← Идея #1 подробно
    02-idea-interactive-report.md ← Идея #2 подробно
    03-customer-voice.md       ← голос клиента (интервью)
    04-competitors-analysis.md ← конкуренты
  context/
    product-context.md         ← продуктовый контекст для людей
    design-prompts.md          ← D-промпты для Claude Design
    hackathon/playbook/00-day-plan.md         ← задачи и mock-данные
    hackathon/playbook/00-day-plan.md                ← план разработки
  PITCH.md                     ← питч для жюри
  playbook/                    ← чеклисты, шаблоны, скрипт демо

prompts/
  hackathon/                  ← промпты хакатона (волны 00–05)
    README.md                 ← плейбук запуска
    wave-00/                  ← чтение контекста (nemotron)
    wave-00a-architecture/    ← архитектура (kimi + qwen3)
    wave-01-foundation/       ← types, constants, mock JSON (qwen3)
    wave-02-components/       ← React-компоненты (qwen3)
    wave-03-screens/          ← экраны (kimi P1-P3, qwen3 P4-P5)
    wave-04-routing/          ← роутинг App.tsx (qwen3)
    wave-05-polish/           ← tickets, smoke, demo (qwen3/nemotron/gpt-oss)
  init/                       ← discovery-промпт (не кодинг)
```

---

## Три экрана продукта

| # | Экран | Идея | Статус |
|---|-------|------|--------|
| 1 | Лента событий + Живой мониторинг | — | Макет готов |
| 2 | **Единое окно инцидента** | **#1 P0** | В разработке |
| 3 | **Интерактивный отчёт** (voice+NL+fleet) | **#2 P0** | Макет готов |
