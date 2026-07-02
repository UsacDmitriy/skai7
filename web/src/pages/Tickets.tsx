import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Clock, FilterX, Inbox, RotateCcw, TriangleAlert } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button, Card, DataTable, type Column } from '@/components'
import { getTickets } from '@/api/client'
import type { ActionType, Status, Ticket } from '@/api/types'

/**
 * f8 · Экран «Заявки» (`/tickets`, идея #6). Против `00-CONTRACT.md`
 * §3.4 (actions) + §7.4 (`GET /api/tickets`) + §7.5 (`Ticket`) + §7.8 (AC «Tickets»).
 *
 * Реестр заявок из журнала действий (`output/actions.csv`). Один ряд = один `Ticket`.
 * «Просрочена» — НЕ статус (enum §3.1), а оверлей по производному полю `is_overdue`.
 * Фильтрация (тип/статус/дата) — клиентская по загруженному списку.
 */

const PARK_TZ = (import.meta.env.VITE_PARK_TIMEZONE as string | undefined) ?? 'UTC'

// ── Форматтеры локали/таймзоны парка (не сырой ISO, не Date.now() в рендере) ───

function formatDateTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: PARK_TZ,
  })
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    timeZone: PARK_TZ,
  })
}

/** Календарный день (YYYY-MM-DD) в зоне парка — для фильтра по диапазону дат. */
function dayKey(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  // en-CA даёт ISO-подобный YYYY-MM-DD, сравнимый лексикографически.
  return d.toLocaleDateString('en-CA', { timeZone: PARK_TZ })
}

// ── Человекочитаемые типы действий (§3.4) ─────────────────────────────────────

const ACTION_LABEL: Record<ActionType, string> = {
  validate: 'Подтверждено',
  false_positive: 'Ложное срабатывание',
  create_task: 'Создание задачи',
  export_report: 'Экспорт отчёта',
  request_archive: 'Запрос архива',
  call_driver: 'Звонок водителю',
  notify_hr: 'Уведомление HR',
  stop_vehicle: 'Остановка ТС',
}

function actionLabel(action: string): string {
  return ACTION_LABEL[action as ActionType] ?? action
}

// ── Статус-бейдж (токены d1; цвет дублируется текстом) ─────────────────────────

const STATUS_LABEL: Record<Status, string> = {
  active: 'Активна',
  in_progress: 'В работе',
  validated: 'Подтверждена',
  false_positive: 'Ложное срабатывание',
  closed: 'Закрыта',
}

const STATUS_BADGE: Record<Status, string> = {
  active: 'bg-primary-50 text-primary',
  in_progress: 'bg-warning-bg text-warning-text',
  validated: 'bg-ok-bg text-ok-text',
  false_positive: 'bg-bg text-muted ring-1 ring-border',
  closed: 'bg-bg text-muted ring-1 ring-border',
}

function StatusBadge({ status }: { status: Status }) {
  return (
    <span
      className={`inline-flex items-center rounded-xl px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[status]}`}
    >
      {STATUS_LABEL[status]}
    </span>
  )
}

const STATUS_ORDER: Status[] = ['active', 'in_progress', 'validated', 'closed']

// ── Фильтры ───────────────────────────────────────────────────────────────────

type Filters = {
  action: string // '' = все
  status: string // '' = все
  from: string // YYYY-MM-DD | ''
  to: string // YYYY-MM-DD | ''
}

const EMPTY_FILTERS: Filters = { action: '', status: '', from: '', to: '' }

// ── Колонки таблицы (форма Ticket §7.5) ───────────────────────────────────────

const COLUMNS: Column<Ticket>[] = [
  {
    id: 'created_at',
    header: 'Дата',
    sortable: true,
    sortValue: (t) => t.created_at,
    cell: (t) => <span className="whitespace-nowrap tabular-nums">{formatDateTime(t.created_at)}</span>,
  },
  {
    id: 'action',
    header: 'Тип',
    sortable: true,
    sortValue: (t) => actionLabel(t.action),
    cell: (t) => actionLabel(t.action),
  },
  {
    id: 'incident_id',
    header: 'Инцидент',
    cell: (t) => (
      <Link
        to={`/incidents/${t.incident_id}`}
        className="rounded text-primary underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        {t.incident_id}
      </Link>
    ),
  },
  {
    id: 'deadline',
    header: 'Срок',
    sortable: true,
    // null-дедлайны вниз при сортировке asc.
    sortValue: (t) => t.deadline ?? '￿',
    cell: (t) => (
      <span className="inline-flex items-center gap-2 whitespace-nowrap">
        <span className="tabular-nums">{formatDate(t.deadline)}</span>
        {t.is_overdue ? (
          <span className="inline-flex items-center gap-1 rounded-xl bg-critical-bg px-2 py-0.5 text-xs font-medium text-critical-text">
            <Clock size={12} aria-hidden />
            Просрочено
          </span>
        ) : null}
      </span>
    ),
  },
  {
    id: 'comment',
    header: 'Комментарий',
    cell: (t) => <span className="text-muted">{t.comment || '—'}</span>,
  },
  {
    id: 'status',
    header: 'Статус',
    sortable: true,
    sortValue: (t) => STATUS_ORDER.indexOf(t.status),
    cell: (t) => <StatusBadge status={t.status} />,
  },
]

// ── Состояния загрузки ────────────────────────────────────────────────────────

function TableSkeleton() {
  return (
    <div className="space-y-2 p-4" aria-hidden>
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="h-9 w-full animate-pulse rounded bg-border/60" />
      ))}
    </div>
  )
}

// ── Экран ─────────────────────────────────────────────────────────────────────

export default function Tickets() {
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS)

  // reqRef отсекает устаревший ответ (повторный ретрай) и setState после unmount.
  const reqRef = useRef(0)
  const load = useCallback(() => {
    setState('loading')
    setError(null)
    const my = ++reqRef.current
    getTickets()
      .then((data) => {
        if (reqRef.current !== my) return
        setTickets(data)
        setState('ready')
      })
      .catch((e: unknown) => {
        if (reqRef.current !== my) return
        setError(e instanceof Error ? e.message : 'Не удалось загрузить заявки.')
        setState('error')
      })
  }, [])

  useEffect(load, [load])

  // Опции фильтра по типу — только реально встречающиеся действия.
  const actionOptions = useMemo(() => {
    const set = new Set(tickets.map((t) => t.action))
    return [...set].sort((a, b) => actionLabel(a).localeCompare(actionLabel(b), 'ru'))
  }, [tickets])

  const filtered = useMemo(() => {
    return tickets.filter((t) => {
      if (filters.action && t.action !== filters.action) return false
      if (filters.status && t.status !== filters.status) return false
      if (filters.from || filters.to) {
        const day = dayKey(t.created_at)
        if (filters.from && day < filters.from) return false
        if (filters.to && day > filters.to) return false
      }
      return true
    })
  }, [tickets, filters])

  const filtersActive =
    filters.action !== '' || filters.status !== '' || filters.from !== '' || filters.to !== ''

  const resetFilters = () => setFilters(EMPTY_FILTERS)

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-lg font-bold text-ink">Заявки</h1>
        <p className="text-sm text-muted">
          Реестр заявок, порождённых действиями над инцидентами.
        </p>
      </header>

      {/* Фильтры */}
      <Card className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-xs font-medium text-muted">
          Тип
          <select
            value={filters.action}
            onChange={(e) => setFilters((f) => ({ ...f, action: e.target.value }))}
            className="h-9 rounded-md border border-border bg-surface px-2 text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <option value="">Все типы</option>
            {actionOptions.map((a) => (
              <option key={a} value={a}>
                {actionLabel(a)}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs font-medium text-muted">
          Статус
          <select
            value={filters.status}
            onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
            className="h-9 rounded-md border border-border bg-surface px-2 text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <option value="">Все статусы</option>
            {STATUS_ORDER.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABEL[s]}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs font-medium text-muted">
          С даты
          <input
            type="date"
            value={filters.from}
            max={filters.to || undefined}
            onChange={(e) => setFilters((f) => ({ ...f, from: e.target.value }))}
            className="h-9 rounded-md border border-border bg-surface px-2 text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          />
        </label>

        <label className="flex flex-col gap-1 text-xs font-medium text-muted">
          По дату
          <input
            type="date"
            value={filters.to}
            min={filters.from || undefined}
            onChange={(e) => setFilters((f) => ({ ...f, to: e.target.value }))}
            className="h-9 rounded-md border border-border bg-surface px-2 text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          />
        </label>

        {filtersActive ? (
          <Button variant="ghost" icon={FilterX} onClick={resetFilters}>
            Сбросить
          </Button>
        ) : null}
      </Card>

      {/* Контент */}
      <Card className="p-0">
        {state === 'loading' ? (
          <TableSkeleton />
        ) : state === 'error' ? (
          <div className="flex flex-col items-center gap-3 py-12 text-center">
            <TriangleAlert className="h-8 w-8 text-high-text" aria-hidden />
            <p className="max-w-sm text-sm text-muted">
              {error ?? 'Не удалось загрузить заявки.'}
            </p>
            <Button variant="secondary" icon={RotateCcw} onClick={load}>
              Повторить
            </Button>
          </div>
        ) : tickets.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-16 text-center text-muted">
            <Inbox className="h-8 w-8" aria-hidden />
            <p className="text-sm">Заявок пока нет</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center gap-3 py-16 text-center text-muted">
            <FilterX className="h-8 w-8" aria-hidden />
            <p className="text-sm">Ничего не найдено</p>
            <Button variant="secondary" icon={FilterX} onClick={resetFilters}>
              Сбросить фильтры
            </Button>
          </div>
        ) : (
          <DataTable columns={COLUMNS} rows={filtered} rowKey={(t) => t.id} />
        )}
      </Card>
    </div>
  )
}
