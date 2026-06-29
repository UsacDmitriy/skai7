# SmartQueryInput Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Единый умный ввод (текст + голос + транскрипт + подсказки) на `/report` (NL→бэкенд) и `/monitor` (локальный фильтр алярмов).

**Architecture:** Presentation-примитив `SmartQueryInput` без бизнес-логики эмитит `onChange`/`onSubmit`; потребители подключают свой обработчик. Чистая функция `alarmSearch` фильтрует список инцидентов для Monitor.

**Tech Stack:** React 18 + TypeScript (strict) + Tailwind (токены d1) + Vitest + Testing-Library.

## Global Constraints

- Язык UI — русский; код/имена — английский (двойные кавычки в SQL не применимо — фронт).
- TypeScript strict, без `any`. Детерминизм в тестах (без `Date.now()`/random).
- Барьер задачи: `cd web && npx vitest run <файл>` зелёный + `npx tsc --noEmit` чист.
- **Маршрутизация исполнения (методология §3.5):** оркестратор — Sonnet 🔵; генерация кода — `ask_deepseek` (Task 5 — `ask_deepseek_flash`). GLM не используем.
- Существующие типы: `IncidentSummary` из `@/api/types` (поля: `vehicle_plate`, `driver`, `alarm_label_ru`, `source`, `severity`, `risk_score`, …). `VoiceButton` из `@/components/ui/VoiceButton` (props: `state`, `onRecorded`, `disabled`, `onStart`, `onStop`).

---

### Task 1: `alarmSearch` — чистая функция фильтра алярмов

**Files:**
- Create: `web/src/state/alarmSearch.ts`
- Test: `web/src/state/alarmSearch.test.ts`

**Interfaces:**
- Consumes: `IncidentSummary` из `@/api/types`.
- Produces: `alarmSearch(query: string, list: IncidentSummary[]): IncidentSummary[]`.

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from 'vitest'
import { alarmSearch } from './alarmSearch'
import type { IncidentSummary } from '@/api/types'

const base: IncidentSummary = {
  id: '1', alarm_type: 'Smoking', alarm_code: 'DMS_SMOKING', alarm_label_ru: 'Курение',
  source: 'DMS', severity: 'medium', risk_level: 'medium', risk_score: 58,
  ts: '2026-05-19 02:59:00+04', vehicle_plate: 'С643УР799', driver: 'Волков Андрей',
  vehicle_model: 'Volvo FH', speed_kmh: 0, lat: null, lon: null, address: null,
  video_available: true, status: 'new',
}
const list: IncidentSummary[] = [
  base,
  { ...base, id: '2', alarm_label_ru: 'Засыпание за рулём', severity: 'critical', risk_score: 80, driver: 'Захаров Тимур', vehicle_plate: 'М078ОО154' },
  { ...base, id: '3', alarm_label_ru: 'Курение', driver: 'Козлов Иван', vehicle_plate: 'К776ВС977', risk_score: 54 },
]

describe('alarmSearch', () => {
  it('пустой запрос → исходный список', () => {
    expect(alarmSearch('', list)).toHaveLength(3)
    expect(alarmSearch('   ', list)).toHaveLength(3)
  })
  it('матч по госномеру (регистронезависимо)', () => {
    expect(alarmSearch('м078', list).map((a) => a.id)).toEqual(['2'])
  })
  it('матч по водителю', () => {
    expect(alarmSearch('козлов', list).map((a) => a.id)).toEqual(['3'])
  })
  it('матч по типу алярма', () => {
    expect(alarmSearch('засыпание', list).map((a) => a.id)).toEqual(['2'])
  })
  it('«критичные» → только critical', () => {
    expect(alarmSearch('критичные', list).map((a) => a.id)).toEqual(['2'])
  })
  it('«риск>70» → risk_score > 70', () => {
    expect(alarmSearch('риск>70', list).map((a) => a.id)).toEqual(['2'])
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/state/alarmSearch.test.ts`
Expected: FAIL — `alarmSearch is not a function` / module not found.

- [ ] **Step 3: Write minimal implementation**

```ts
import type { IncidentSummary } from '@/api/types'

/**
 * Локальный умный поиск по активным алярмам (Monitor).
 * Чистая детерминированная функция: пустой запрос → список без изменений.
 * Спецсинтаксис: «критичные» → severity==='critical'; «риск>N» → risk_score>N.
 * Иначе — подстрочный матч по плашке/водителю/типу/источнику (регистронезависимо).
 */
export function alarmSearch(query: string, list: IncidentSummary[]): IncidentSummary[] {
  const q = query.trim().toLowerCase()
  if (!q) return list

  const riskGt = q.match(/риск\s*>\s*(\d{1,3})/)
  if (riskGt) {
    const n = Number(riskGt[1])
    return list.filter((a) => a.risk_score > n)
  }
  if (/критичн/.test(q)) return list.filter((a) => a.severity === 'critical')

  return list.filter(
    (a) =>
      a.vehicle_plate.toLowerCase().includes(q) ||
      a.driver.toLowerCase().includes(q) ||
      a.alarm_label_ru.toLowerCase().includes(q) ||
      a.source.toLowerCase().includes(q),
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/state/alarmSearch.test.ts`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add web/src/state/alarmSearch.ts web/src/state/alarmSearch.test.ts
git commit -m "feat(monitor): alarmSearch — чистый локальный фильтр алярмов"
```

---

### Task 2: `SmartQueryInput` — переиспользуемый примитив ввода

**Files:**
- Create: `web/src/components/ui/SmartQueryInput.tsx`
- Test: `web/src/components/ui/SmartQueryInput.test.tsx`

**Interfaces:**
- Consumes: `VoiceButton`, `VoiceButtonState` из `@/components/ui/VoiceButton`.
- Produces: `SmartQueryInput` (props ниже), `SmartQueryInputProps`.

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { SmartQueryInput } from './SmartQueryInput'

describe('SmartQueryInput', () => {
  it('печать эмитит onChange', () => {
    const onChange = vi.fn()
    render(<SmartQueryInput value="" onChange={onChange} />)
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'гусев' } })
    expect(onChange).toHaveBeenCalledWith('гусев')
  })
  it('Enter эмитит onSubmit с текущим текстом', () => {
    const onSubmit = vi.fn()
    render(<SmartQueryInput value="курение" onChange={vi.fn()} onSubmit={onSubmit} />)
    fireEvent.keyDown(screen.getByRole('searchbox'), { key: 'Enter' })
    expect(onSubmit).toHaveBeenCalledWith('курение')
  })
  it('клик по чипу-подсказке эмитит onChange и onSubmit', () => {
    const onChange = vi.fn()
    const onSubmit = vi.fn()
    render(
      <SmartQueryInput value="" onChange={onChange} onSubmit={onSubmit} suggestions={['рейтинг водителей']} />,
    )
    fireEvent.click(screen.getByRole('button', { name: 'рейтинг водителей' }))
    expect(onChange).toHaveBeenCalledWith('рейтинг водителей')
    expect(onSubmit).toHaveBeenCalledWith('рейтинг водителей')
  })
  it('voice=false → нет кнопки записи', () => {
    render(<SmartQueryInput value="" onChange={vi.fn()} />)
    expect(screen.queryByLabelText(/Записать голосовой запрос/)).toBeNull()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/ui/SmartQueryInput.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```tsx
import { Loader2, Search } from 'lucide-react'
import { VoiceButton, type VoiceButtonState } from './VoiceButton'
import { cn } from './cn'

export interface SmartQueryInputProps {
  value: string
  onChange: (text: string) => void
  onSubmit?: (text: string) => void
  placeholder?: string
  suggestions?: string[]
  voice?: boolean
  voiceState?: VoiceButtonState
  onRecorded?: (blob: Blob) => void
  busy?: boolean
  className?: string
}

/**
 * SmartQueryInput — единый ввод запроса: текст (первичный) + опц. голос + подсказки.
 * Чистая презентация: эмитит onChange (каждое изменение) и onSubmit (Enter/чип).
 */
export function SmartQueryInput({
  value, onChange, onSubmit, placeholder = 'Сформулируйте запрос…',
  suggestions = [], voice = false, voiceState = 'idle', onRecorded, busy, className,
}: SmartQueryInputProps) {
  const pickSuggestion = (s: string) => {
    onChange(s)
    onSubmit?.(s)
  }
  return (
    <div className={cn('flex flex-col gap-2', className)} role="search">
      <div className="flex items-center gap-2">
        {voice && onRecorded && (
          <VoiceButton state={voiceState} onRecorded={onRecorded} disabled={busy} />
        )}
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
          <input
            type="search"
            value={value}
            placeholder={placeholder}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onSubmit?.(value)
            }}
            className="w-full rounded-lg border border-border bg-surface py-2 pl-9 pr-3 text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          />
          {busy && (
            <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-primary" aria-hidden />
          )}
        </div>
      </div>
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {suggestions.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => pickSuggestion(s)}
              className="rounded-full border border-border bg-bg px-2.5 py-1 text-xs text-muted hover:bg-primary-50 hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            >
              {s}
            </button>
          ))}
        </div>
      )}
      <span role="status" aria-live="polite" className="sr-only">
        {voiceState === 'recording' ? 'Идёт запись' : voiceState === 'processing' ? 'Распознавание' : ''}
      </span>
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/ui/SmartQueryInput.test.tsx`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add web/src/components/ui/SmartQueryInput.tsx web/src/components/ui/SmartQueryInput.test.tsx
git commit -m "feat(ui): SmartQueryInput — единый ввод (текст+голос+подсказки)"
```

---

### Task 3: Интеграция поиска в `/monitor`

**Files:**
- Modify: `web/src/pages/Monitor.tsx` (состояние `search`, рендер `SmartQueryInput`, шаг в `visible` useMemo)
- Test: `web/src/pages/Monitor.search.test.tsx`

**Interfaces:**
- Consumes: `SmartQueryInput` (Task 2), `alarmSearch` (Task 1).
- Produces: визуальный поиск над списком «Активные алярмы»; карта и список рисуют общий `visible`.

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Monitor from './Monitor'
import * as client from '@/api/client'

vi.mock('@/api/client', async (orig) => ({ ...(await orig()), getIncidents: vi.fn(), getZones: vi.fn(), getRebAnomalyZones: vi.fn() }))

const inc = (over: Partial<any>) => ({
  id: '1', alarm_type: 'Smoking', alarm_code: 'DMS_SMOKING', alarm_label_ru: 'Курение',
  source: 'DMS', severity: 'medium', risk_level: 'medium', risk_score: 58, ts: '2026-05-19 02:59:00+04',
  vehicle_plate: 'С643УР799', driver: 'Волков Андрей', vehicle_model: 'Volvo FH', speed_kmh: 0,
  lat: 55.7, lon: 37.6, address: null, video_available: true, status: 'new', ...over,
})

beforeEach(() => {
  vi.mocked(client.getZones).mockResolvedValue([])
  vi.mocked(client.getRebAnomalyZones).mockResolvedValue([])
  vi.mocked(client.getIncidents).mockResolvedValue([
    inc({}), inc({ id: '2', driver: 'Гусев Вячеслав', vehicle_plate: 'М477УМ790' }),
  ])
})

describe('Monitor · умный поиск', () => {
  it('ввод «гусев» сужает список алярмов', async () => {
    render(<MemoryRouter><Monitor /></MemoryRouter>)
    await waitFor(() => expect(screen.getByRole('searchbox')).toBeInTheDocument())
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'гусев' } })
    await waitFor(() => {
      expect(screen.getByText(/Гусев/)).toBeInTheDocument()
      expect(screen.queryByText(/Волков/)).toBeNull()
    })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/pages/Monitor.search.test.tsx`
Expected: FAIL — нет `searchbox` (поиск ещё не добавлен).

- [ ] **Step 3: Implement — три точечных правки в `Monitor.tsx`**

3a. Импорты (рядом с прочими):
```tsx
import { SmartQueryInput } from '@/components/ui/SmartQueryInput'
import { alarmSearch } from '@/state/alarmSearch'
```

3b. Состояние (рядом с `const [filter, setFilter] = useState<FilterKey>('all')`):
```tsx
const [search, setSearch] = useState('')
```

3c. Встроить `alarmSearch` в конвейер `visible` useMemo — поиск ПОСЛЕ роли, ДО chip-фильтра и сортировки:
```tsx
const visible = useMemo(() => {
  const searched = alarmSearch(search, roleVisible)
  const filtered = searched.filter((i) => passesFilter(i, filter))
  return [...filtered].sort(/* существующий компаратор sortKey */)
}, [roleVisible, search, filter, sortKey])
```
> Сохранить существующий компаратор сортировки as-is; добавлены только шаг `alarmSearch` и зависимость `search`.

3d. Рендер `SmartQueryInput` над секцией «Активные алярмы»:
```tsx
<SmartQueryInput
  value={search}
  onChange={setSearch}
  placeholder="Поиск: госномер, водитель, тип, «критичные», «риск>70»"
  className="mb-3"
/>
```

- [ ] **Step 4: Run test + typecheck**

Run: `cd web && npx vitest run src/pages/Monitor.search.test.tsx && npx tsc --noEmit`
Expected: PASS + 0 type errors.

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/Monitor.tsx web/src/pages/Monitor.search.test.tsx
git commit -m "feat(monitor): умный поиск по активным алярмам (текст → фильтр)"
```

---

### Task 4: Интеграция `SmartQueryInput` в `/report`

**Files:**
- Modify: `web/src/pages/Report.tsx` (заменить связку VoiceButton+поле на `SmartQueryInput`, добавить подсказки)
- Test: `web/src/pages/Report.smartinput.test.tsx`

**Interfaces:**
- Consumes: `SmartQueryInput` (Task 2). Использует существующие в Report: состояние текста, `runQuery(text)`, состояние записи/`onRecorded` (d5).
- Produces: ввод с подсказками; транскрипт попадает в редактируемое поле перед отправкой.

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Report from './Report'
import * as client from '@/api/client'

vi.mock('@/api/client', async (orig) => ({ ...(await orig()), getSabotage: vi.fn(), queryReport: vi.fn() }))

beforeEach(() => {
  vi.mocked(client.getSabotage).mockResolvedValue([])
  vi.mocked(client.queryReport).mockResolvedValue({ query: { kind: 'driver', period_days: 7 } as any, report: {} as any })
})

describe('Report · SmartQueryInput', () => {
  it('клик по чипу-подсказке строит отчёт через queryReport', () => {
    render(<MemoryRouter><Report /></MemoryRouter>)
    fireEvent.click(screen.getByRole('button', { name: 'рейтинг водителей' }))
    expect(client.queryReport).toHaveBeenCalledWith('рейтинг водителей')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/pages/Report.smartinput.test.tsx`
Expected: FAIL — чипа-подсказки нет.

- [ ] **Step 3: Implement — заменить блок ввода в `Report.tsx`**

3a. Импорт:
```tsx
import { SmartQueryInput } from '@/components/ui/SmartQueryInput'
```

3b. В Card «Голосовая аналитика» заменить текущую связку `<VoiceButton/> + <input/>` на:
```tsx
<SmartQueryInput
  value={text}
  onChange={setText}
  onSubmit={runQuery}
  voice
  voiceState={voiceState}
  onRecorded={handleRecorded}
  busy={queryLoading}
  suggestions={[
    'дисциплина Иванова за неделю',
    'грубые нарушения по парку',
    'рейтинг водителей',
    'засыпания за ночь',
  ]}
/>
```
> Использовать существующие в Report идентификаторы: `text`/`setText` (текст запроса), `runQuery` (NL→бэкенд), `voiceState`, `handleRecorded` (обработчик blob d5), `queryLoading`. Если их имена в файле отличаются — подставить фактические (НЕ создавать новые состояния).

- [ ] **Step 4: Run full Report tests + typecheck**

Run: `cd web && npx vitest run src/pages/Report && npx tsc --noEmit`
Expected: PASS (все Report-тесты) + 0 type errors.

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/Report.tsx web/src/pages/Report.smartinput.test.tsx
git commit -m "feat(report): SmartQueryInput — подсказки + редактируемый транскрипт"
```

---

### Task 5: Усиление demo-NLU (`mockNlu`)

**Files:**
- Modify: `web/src/api/voice.ts:36-49` (функция `mockNlu`)
- Test: `web/src/api/voice.test.ts`

**Interfaces:**
- Consumes: существующий `ReportQuery` тип, `DRIVER_REPORT`/`FLEET_REPORT` фикстуры.
- Produces: расширенный офлайн-разбор (только под `VITE_USE_FIXTURES`).

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from 'vitest'
import { queryReport } from './voice'

// Под фикстурами queryReport использует mockNlu синхронно-детерминированно.
describe('mockNlu (demo)', () => {
  it('«рейтинг водителей» → fleet/drivers', async () => {
    const { query } = await queryReport('рейтинг водителей')
    expect(query.kind).toBe('fleet')
  })
  it('«нарушения по парку» → fleet', async () => {
    const { query } = await queryReport('грубые нарушения по парку')
    expect(query.kind).toBe('fleet')
  })
  it('«дисциплина Иванова за неделю» → driver, period 7', async () => {
    const { query } = await queryReport('дисциплина Иванова за неделю')
    expect(query.kind).toBe('driver')
    if (query.kind === 'driver') expect(query.period_days).toBe(7)
  })
})
```
> Запуск с `VITE_USE_FIXTURES=true` (см. vitest env). Если в setup иначе — выставить env в тесте через `vi.stubEnv('VITE_USE_FIXTURES', 'true')` в `beforeEach`.

- [ ] **Step 2: Run test to verify current behavior**

Run: `cd web && npx vitest run src/api/voice.test.ts`
Expected: часть кейсов FAIL (период «за сутки/ночь», доп. паттерны не распознаются).

- [ ] **Step 3: Расширить `mockNlu`**

```ts
function mockNlu(text: string): ReportQuery {
  const t = text.toLowerCase()
  const isFleet = /парк|флот|всем|по тс|по машин|по водител[яеи]м|рейтинг/.test(t)
  const period_days = /за сутки|за день|за ночь/.test(t) ? 1 : /за месяц/.test(t) ? 30 : 7
  if (isFleet) {
    const view = /тс|машин/.test(t) ? 'vehicles' : 'drivers'
    return { kind: 'fleet', view, period_days }
  }
  return {
    kind: 'driver',
    driver_name: DRIVER_REPORT.driver.driver_name,
    plate: DRIVER_REPORT.vehicle_plate,
    period_days,
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/api/voice.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/api/voice.ts web/src/api/voice.test.ts
git commit -m "feat(report): расширенный demo-NLU (периоды + паттерны)"
```

---

## Финальный барьер (Opus 🔴)

```bash
cd web && npx vitest run && npx tsc --noEmit
```
Ожидание: все тесты зелёные (≥238 + новые), типы чисты.

## Self-Review (выполнено при написании)
- Покрытие спеки: §3.1→Task2, §3.2→Task1, §3.3→Task4, §3.4→Task3, §3.5→Task5, §5→тесты в каждой задаче. ✅
- Плейсхолдеров нет; типы согласованы (`alarmSearch(query,list)`, `SmartQueryInput` props едины между задачами). ✅
- Скоуп: один план, фронт, файлы непересекающиеся (1+2 фундамент → 3,4,5 веер). ✅
- Известный риск: Task 4 опирается на фактические имена состояний в `Report.tsx` — исполнитель подставляет реальные, новых не создаёт (явно указано).
