# d2 · UI-примитивы (React + Tailwind)

> Трек **Design**. Против `00-CONTRACT.md` §4 + `init/context/DESIGN.md` (раздел Components).
> **Владеет:** `web/src/components/ui/*`. Использует токены d1, но НЕ редактирует tailwind.config.
> Референс вёрстки — HTML-мокапы `ui/**` и дизайн-промпты `prompts/claude-design/**` (читать как образец
> стиля, не копировать React-через-Babel — писать чистые TSX-компоненты).

## Цель

Библиотека переиспользуемых презентационных компонентов SKAI. Без бизнес-логики и fetch — только props → разметка. На них собираются экраны f4.

## Компоненты (один файл на компонент)

1. **`Button.tsx`** — варианты `primary | secondary | danger | ghost`, размер h36, `icon?` (Lucide), `loading?`. Стили из DESIGN.md §Кнопки.
2. **`SeverityBadge.tsx`** — props `severity: 'critical'|'high'|'medium'|'low'`, `label: string`. Цветной кружок 6px + текст. Палитра через маппинг d1 (medium→warning, low→ok).
3. **`ScoreBar.tsx`** — props `score: 0..100`. Трек 4px + градиентная заливка (`.score-bar-fill`), числовое значение справа (700, tabular-nums).
4. **`Card.tsx`** — surface-карточка; вариант `incident` с `border-left: 4px` по severity, состояния `hover`/`selected` (props `selected?`, `onClick?`).
5. **`VideoPlayer.tsx`** — 16:9, фон #0F172A, нативный `<video controls>` + проп `eventMarkerPct?` (жёлтая вертикаль на таймлайне). Принимает `src: string`, `poster?`. Пустое состояние «Видео недоступно» если `src` пуст.
6. **`DataTable.tsx`** — generic таблица: `columns`, `rows`, sort-иконки, hover/selected строки (DESIGN.md §Таблица). Без пагинации (или простая).
7. **`TelemetryChart.tsx`** — Recharts: линия скорости (#1E3A8A) + линия акселерометра (#EA580C), `ReferenceLine` события (#EAB308, x=0). Props `data: {ts_offset, speed, ax, ay}[]`. Стиль из DESIGN.md §График телеметрии.

## Требования

- TypeScript, строгие props-интерфейсы, экспорт именованный.
- Иконки — `lucide-react` (см. DESIGN.md §Иконки).
- Никаких прямых hex — только Tailwind-классы/CSS-переменные из d1.
- Каждый компонент самодостаточен и рендерится из Storybook-подобной витрины (соберёт d3).

## Check

- Все 7 файлов компилируются (`tsc --noEmit`) без ошибок типов.
- `SeverityBadge` корректно мапит `medium→warning`, `low→ok`.
- `TelemetryChart` принимает форму `TelemetryPoint` из контракта §3.1.
