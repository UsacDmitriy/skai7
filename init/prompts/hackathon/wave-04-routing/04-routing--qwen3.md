# 04 · Роутинг — заменить заглушки в App.tsx
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия. Не запускать параллельно.**
# Модель: qwen/qwen3-coder:free · $0 · Волна 4
> ✅ Передать: текущий code/frontend/src/App.tsx (только этот файл)
> ❌ НЕ читать AGENTS.md, не читать все экраны целиком

## Задача

Открыть `code/frontend/src/App.tsx`.

Заменить 5 inline-заглушек на реальные импорты из `./screens/`:

```tsx
import EventFeedScreen       from './screens/EventFeedScreen'
import LiveMonitorScreen     from './screens/LiveMonitorScreen'
import UnifiedIncidentWindow from './screens/UnifiedIncidentWindow'
import AnalyticsScreen       from './screens/AnalyticsScreen'
import TicketsScreen         from './screens/TicketsScreen'
```

Убрать строки `const EventFeedScreen = () => ...` и другие inline-заглушки.

Маршруты в `<Routes>` оставить без изменений:
```tsx
<Route path="/"             element={<EventFeedScreen />} />
<Route path="/monitor"      element={<LiveMonitorScreen />} />
<Route path="/incident/:id" element={<UnifiedIncidentWindow />} />
<Route path="/analytics"    element={<AnalyticsScreen />} />
<Route path="/tickets"      element={<TicketsScreen />} />
```

Всё остальное (sidebar, стили, NavLink) — не трогать.

## Перед заменой убедиться что файлы существуют

```
code/frontend/src/screens/EventFeedScreen.tsx       ← wave-03A
code/frontend/src/screens/LiveMonitorScreen.tsx     ← wave-03E
code/frontend/src/screens/UnifiedIncidentWindow.tsx ← wave-03B
code/frontend/src/screens/AnalyticsScreen.tsx       ← wave-03D
code/frontend/src/screens/TicketsScreen.tsx         ← wave-05B
```

Если какой-то файл ещё не создан — подождать пока завершится его волна.

## Acceptance criteria

- В App.tsx нет inline-заглушек (`const X = () => <div>...`)
- Есть 5 import строк из `./screens/`
- `npm run build` → нет ошибок TypeScript
- `npm run dev` → все 5 маршрутов открываются
