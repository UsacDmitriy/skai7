# Волна 00a-A — Техническая архитектура
> 🤖 **Модель: `moonshotai/kimi-k2.6`** | архитектура React-приложения
> 💰 **Контекст: AGENTS.md (секции 1,5,6) + verify-standalone.jpg** (~5K токенов, ~$0.04)
> ❌ НЕ читать: code/clade_design/*.html (1.7–1.9MB = $0.31+ за чтение!)
> ⚠️ Один промпт = одна сессия · результат → `hackathon/context/TECH-DESIGN.md`

## Что передать в сессию

1. **Секции 1, 5, 6 из AGENTS.md** (скопировать текстом — ~2K токенов)
2. **Прикрепить как image** (не текст!):
   `code/clade_design/Интерактивнй отчет/verify-standalone.jpg` (14KB — безопасно)

> Почему jpg, а не html?
> HTML-файлы — 1.7–1.9MB, 425–478K токенов, $0.31 только на чтение.
> JPG-скриншот — 14KB, Kimi видит дизайн визуально, стоит <$0.01.

---

## Промпт

```
Ты — ведущий React-архитектор. Контекст продукта: [секции AGENTS.md].
На изображении — скриншот одного из экранов SKAI (Интерактивный отчёт).

Задача: спроектировать архитектуру React 18 + TypeScript + Tailwind-приложения.
Напиши файл `hackathon/context/TECH-DESIGN.md` со следующими разделами:

## 1. Дерево компонентов

ВАЖНО: используй ТОЛЬКО реальные имена полей из CSV-датасетов, которые были переданы в начале сессии.
НЕ придумывай поля. НЕ используй поля из data/mock/*.json.

Полное дерево для 5 экранов. Для каждого компонента:
- Имя файла и путь
- Props interface с РЕАЛЬНЫМИ именами полей из CSV
- Откуда данные: из какого CSV-файла

Пример формата:
  screens/LiveMonitorScreen.tsx
    components/VideoAlarmCard.tsx  props: { alarm: VideoAlarm }  ← selected_video_alarms.csv
    components/TelemetryChart.tsx  props: { points: TrackPoint[] } ← track_points.csv

## 2. Routing (App.tsx)

Напиши секцию routing:
- / → EventFeedScreen
- /incident/:id → UnifiedIncidentWindow
- /analytics → AnalyticsScreen
- /monitor → LiveMonitorScreen
- /tickets → TicketsScreen

## 3. State management

Только useState + один React Context (AppContext):
- selectedIncidentId: string | null
- queryResult: QueryResult | null
Остальное — локальный стейт в компонентах.

## 4. Tailwind config (тема)

На основе изображения выпиши цвета для tailwind.config.js theme.extend.colors:
- surface, bg, border, text-primary, text-muted
- critical, warning, ok, offline
- Названия должны совпадать с COLORS из constants.ts

Только текст файла TECH-DESIGN.md. Без объяснений вокруг.
```

## Acceptance criteria

- Все компоненты из AGENTS.md раздел 5 присутствуют в дереве
- Props согласованы с именами полей из mock JSON (alarm_type, video_available…)
- Файл создан как `hackathon/context/TECH-DESIGN.md`
- Размер файла: 3–8KB (не нужны длинные объяснения)
- ВСЕ имена полей в props взяты из РЕАЛЬНЫХ заголовков CSV (проверить)
- НИ ОДНО поле не выдумано (не из data/mock/*.json)
- Описана стратегия соединения video_alarms ↔ video_files ↔ track_points
