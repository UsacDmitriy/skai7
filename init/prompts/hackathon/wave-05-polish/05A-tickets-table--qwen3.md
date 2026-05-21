# 05A · TicketsTable.tsx
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 5

**Файл:** `code/frontend/src/components/TicketsTable.tsx`

Передать: `code/frontend/src/types.ts` + `code/frontend/src/constants.ts`.

Props: `incidents: Incident[]`, `onOpen: (id: string) => void`

HTML `<table>` 100% width.

**Thead** (bg-skai-bg, text-xs uppercase muted):
`# | ТС / Водитель | Событие | Источник | Видео | Статус | Действие`

**Tbody** — одна строка на инцидент:
- `border-l-4` цвет по riskLevel (critical→red, high→orange, medium→blue, low→green)
- Ячейки 14px, py-3 px-4
- **ТС / Водитель**: plate bold + driverName xs muted
- **Событие**: EVENT_LABELS[eventType]
- **Источник**: eventSource (бейдж slate)
- **Видео**: hasVideo → кнопка "▶ Смотреть" (border primary xs) : "—"
- **Статус**: STATUS_BADGE[status]
- **Действие**: кнопка "Открыть →" onClick={() => onOpen(incident.id)}

Hover row: `bg-slate-50`.
