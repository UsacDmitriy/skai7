# SKAI Unified Incident Window

---

## Две ключевые идеи

### Идея #1 (P0) — Единое окно инцидента
→ `init/ideas/01-idea-unified-window.md`

Телематика + видео + CAN в одном экране.
Клик на событие → синхронное видео + график + действия.

**Дизайн:** `design-prompts/claude-design/03-idea1-incident-video.md`
**Код:** `prompts/waves/wave-03-screens/P3-03B-incident-card.md`

### Идея #2 (P0) — Интерактивный аналитический отчёт
→ `init/ideas/02-idea-interactive-report.md`

Голосом или текстом → подтверждение → дашборд.
Режим В-1 (один водитель) + Режим В-2 (парк, toggle По водителям|По ТС).

**Дизайн:** `design-prompts/claude-design/05-idea2-interactive-report.md`
**Код:** `prompts/waves/wave-03-screens/P2-03D-analytics-screen.md`

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
  waves/                      ← промпты разработки (волны 00–05)
    README.md                 ← плейбук запуска
    wave-00/                  ← чтение контекста
    wave-00a-architecture/    ← архитектура
    wave-01-foundation/       ← types, constants, mock JSON
    wave-02-components/       ← React-компоненты
    wave-03-screens/          ← экраны
    wave-04-routing/          ← роутинг App.tsx
    wave-05-polish/           ← tickets, smoke, demo
  init/                       ← discovery-промпт
```

---

## Три экрана продукта

| # | Экран | Идея | Статус |
|---|-------|------|--------|
| 1 | Лента событий + Живой мониторинг | — | Макет готов |
| 2 | **Единое окно инцидента** | **#1 P0** | В разработке |
| 3 | **Интерактивный отчёт** (voice+NL+fleet) | **#2 P0** | Макет готов |
