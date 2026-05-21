# 02D · ActionButtons.tsx
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 2

**Файл:** `code/frontend/src/components/ActionButtons.tsx`

Передать: `code/frontend/src/types.ts` + `code/frontend/src/constants.ts`.

Props: `incident: Incident`, `onAction: (type: ActionType) => void`

Стейт: `actionDone: Partial<Record<ActionType, boolean>>`

**4 кнопки** (стек, full-width, h-9, text-sm, rounded-lg):

| # | Лейбл | Стиль | Условие показа | После клика |
|---|-------|-------|----------------|-------------|
| 1 | 🔧 Создать заявку | bg primary white | всегда | disabled "✓ Заявка создана" + bg-green-700 |
| 2 | 📹 Позвонить через камеру | bg #0369A1 white | всегда | → calling → [🔴● Разговор 00:32] → ended |
| 3 | 📋 Запросить видео | border primary | только если `!video_available` | disabled "✓ Запрос создан" |
| 4 | 📄 Сформировать отчёт | border slate | всегда | disabled после клика |
| 5 | 📞 Вызвать по телефону | border ok | всегда | disabled "✓ Звонок инициирован" |

**Кнопка «Позвонить через камеру» — три состояния:**
```tsx
type CallState = 'idle' | 'calling' | 'active' | 'ended'
const [callState, setCallState] = useState<CallState>('idle')
const [callDuration, setCallDuration] = useState(0)

// idle: «📹 Позвонить через камеру» bg #0369A1
// calling: «⏳ Подключение...» animate-pulse, disabled
// active: «🔴● Разговор · {mm:ss}» bg #DC2626, таймер растёт + кнопка «Завершить»
// ended: «✓ Звонок завершён» disabled bg-slate-400
```
← Маслов (Балтика): «Звонить водителям через регистратор, не по телефону»

**Не делать:** никакого API, никакого стейта кроме `actionDone`.  
Экспорт: `export default ActionButtons`

### Acceptance criteria

```
✅ inc-001 (video_available=true): кнопка «Запросить видео» НЕ показана
✅ inc-003 (video_available=false): кнопка «Запросить видео» показана
✅ Клик «Создать заявку» → кнопка зеленеет + текст «✓ Заявка создана» + disabled
✅ Клик «Вызвать водителя» → «✓ Звонок инициирован» + disabled
✅ Второй клик невозможен (disabled state)
✅ npm run build без ошибок
```

### Компонент ReasonBlock (для блока причины события)

```tsx
// frontend/src/components/ReasonBlock.tsx
type IncidentReason = 'drowsy' | 'distracted' | 'cut_off' | 'technical' | null

const REASONS = [
  { id: 'drowsy',     icon: '😴', label: 'Засыпал',     color: 'text-red-600 bg-red-50 border-red-200' },
  { id: 'distracted', icon: '📱', label: 'Отвлёкся',    color: 'text-amber-600 bg-amber-50 border-amber-200' },
  { id: 'cut_off',    icon: '🚗', label: 'Подрезали',   color: 'text-green-600 bg-green-50 border-green-200' },
  { id: 'technical',  icon: '⚙',  label: 'Техн. сбой',  color: 'text-slate-500 bg-slate-50 border-slate-200' },
]
// Props: incidentId, onReasonSet(reason)
// Сохраняет в localStorage['reason_' + incidentId]
// Показывает AI-версию причины (из incident.evidence_summary) + кнопки выбора
```

Создать: `code/frontend/src/components/ReasonBlock.tsx`
Источник: Фомин (PepsiCo): «Почему он резко повернул — прозевал, отвлёкся, кто-то выбежал?»
