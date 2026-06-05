# d3 · Сборка библиотеки + витрина (Style Guide)

> Трек **Design**. **Владеет:** `web/src/components/index.ts`, `web/src/pages/_StyleGuide.tsx`.
> Зависит от контракта компонентов d2 (имена/props), но кодит против него, не против рантайма.

## Цель

Собрать публичный API библиотеки и страницу-витрину, где видно все примитивы во всех состояниях — это и приёмка дизайна, и справочник для f4.

## Задачи

1. **`web/src/components/index.ts`** — реэкспорт всех UI-примитивов d2 (`Button`, `SeverityBadge`, `ScoreBar`, `Card`, `VideoPlayer`, `DataTable`, `TelemetryChart`) + их типов.
2. **`web/src/pages/_StyleGuide.tsx`** — страница `/_styleguide`:
   - Палитра (все токены d1 цветными плашками).
   - Все варианты `Button`, все 4 `SeverityBadge`, `ScoreBar` для score 20/55/84/97.
   - `Card` обычная и `incident`-вариант (selected/hover) для каждой severity.
   - `VideoPlayer` с демо-src и с пустым состоянием.
   - `DataTable` на 5 фейковых строк.
   - `TelemetryChart` на демо-данных формы `TelemetryPoint` (взять кейс «датчик удара»: скорость 54→0, ax пик).
3. Зарегистрировать роут `/_styleguide` (f1 владеет роутером — здесь только добавить ленивый импорт страницы через экспорт, договорённость: f1 импортирует `_StyleGuide` если файл есть).

## Check

- `import { Button, SeverityBadge, ScoreBar, Card, VideoPlayer, DataTable, TelemetryChart } from '@/components'` работает.
- Страница `_StyleGuide` рендерит все примитивы без ошибок консоли.
- Витрина визуально соответствует `init/context/DESIGN.md` (цвета, радиусы, типографика).
