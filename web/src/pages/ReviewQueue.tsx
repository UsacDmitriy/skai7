import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Check,
  Inbox,
  RotateCw,
  TriangleAlert,
  Video,
  VideoOff,
  X,
} from 'lucide-react'
import { Card, SeverityBadge } from '@/components'
import { cn } from '@/components/ui/cn'
import { getReviewQueue, postReviewDecision } from '@/api/client'
import type { ReviewItem, ReviewQueue as ReviewQueueData, ReviewStatus, Severity } from '@/api/types'

/**
 * f26 · Экран очереди верификации (`/validation`, фича #23). Против
 * `00-CONTRACT.md` §11.2/§11.3/§11.4 (паттерн таблицы — `Tickets.tsx` f8 /
 * `EventsFeed.tsx`). Владелец «сироты» `/validation` (ревизия допущения f22).
 *
 * Диспетчер проходит очередь: видит инцидент (есть ли видео-доказательство),
 * подтверждает/отклоняет с заметкой, фильтрует по статусу. Кейс Фомина
 * «39 → 5 подтверждённых» становится workflow.
 */

const PARK_TZ = (import.meta.env.VITE_PARK_TIMEZONE as string | undefined) ?? 'UTC'

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

// ── Severity-лейблы (§3.1) ─────────────────────────────────────────────────────

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: 'Критично',
  high: 'Высокий',
  medium: 'Средний',
  low: 'Низкий',
}

// ── Статус решения (§11.2): цвет + текст (a11y — не только цветом) ─────────────

const STATUS_LABEL: Record<ReviewStatus, string> = {
  pending: 'На проверке',
  validated: 'Подтверждён',
  dismissed: 'Отклонён',
}

const STATUS_BADGE: Record<ReviewStatus, string> = {
  pending: 'bg-warning-bg text-warning-text',
  validated: 'bg-ok-bg text-ok-text',
  dismissed: 'bg-bg text-muted ring-1 ring-border',
}

function StatusBadge({ status }: { status: ReviewStatus }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-xl px-2 py-0.5 text-xs font-medium',
        STATUS_BADGE[status],
      )}
    >
      {STATUS_LABEL[status]}
    </span>
  )
}

// ── Фильтр статуса (по умолчанию pending) ──────────────────────────────────────

const FILTERS: { value: ReviewStatus; label: string }[] = [
  { value: 'pending', label: 'На проверке' },
  { value: 'validated', label: 'Подтверждённые' },
  { value: 'dismissed', label: 'Отклонённые' },
]

// ── Состояние загрузки ─────────────────────────────────────────────────────────

function TableSkeleton() {
  return (
    <div className="space-y-2 p-4" aria-hidden>
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="h-9 w-full animate-pulse rounded bg-border/60" />
      ))}
    </div>
  )
}

function pct(rate: number): string {
  return `${Math.round(rate * 100)}%`
}

// ── Экран ──────────────────────────────────────────────────────────────────────

export default function ReviewQueue() {
  const navigate = useNavigate()
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [queue, setQueue] = useState<ReviewQueueData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<ReviewStatus>('pending')
  const [busyId, setBusyId] = useState<string | null>(null)

  // reqRef отсекает устаревший ответ (гонка при быстрой смене фильтра) и setState
  // после unmount.
  const reqRef = useRef(0)
  const load = useCallback((status: ReviewStatus) => {
    setState('loading')
    setError(null)
    const my = ++reqRef.current
    getReviewQueue(status)
      .then((data) => {
        if (reqRef.current !== my) return
        setQueue(data)
        setState('ready')
      })
      .catch((e: unknown) => {
        if (reqRef.current !== my) return
        setError(e instanceof Error ? e.message : 'Не удалось загрузить очередь.')
        setState('error')
      })
  }, [])

  useEffect(() => load(filter), [load, filter])

  const decide = useCallback(
    (id: string, decision: 'validated' | 'dismissed') => {
      // Опциональная заметка — пустая валидна (§11.4).
      const note = window.prompt('Заметка к решению (необязательно):') ?? undefined
      setBusyId(id)
      postReviewDecision(id, decision, note)
        .then(() => load(filter)) // refetch: счётчики и фильтр согласованы с журналом
        .catch((e: unknown) => {
          // Локальный алерт вместо setState('error'): неудача одного решения не должна
          // стирать весь список (страница остаётся в ready).
          const msg = e instanceof Error ? e.message : 'Не удалось сохранить решение.'
          window.alert(`Не удалось сохранить решение: ${msg}`)
        })
        .finally(() => setBusyId(null))
    },
    [load, filter],
  )

  const counts = queue?.counts
  const items = queue?.items ?? []

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-bold text-ink">Очередь верификации</h1>
          <p className="text-sm text-muted">
            Подтверждение или отклонение инцидентов с видео-доказательством.
          </p>
        </div>
        {/* Счётчики статусов + доказательность (§10-контекст). */}
        {counts ? (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="inline-flex items-center gap-1 rounded-lg bg-warning-bg px-2 py-1 font-medium text-warning-text">
              На проверке: <span className="tabular-nums">{counts.pending}</span>
            </span>
            <span className="inline-flex items-center gap-1 rounded-lg bg-ok-bg px-2 py-1 font-medium text-ok-text">
              Подтверждено: <span className="tabular-nums">{counts.validated}</span>
            </span>
            <span className="inline-flex items-center gap-1 rounded-lg bg-bg px-2 py-1 font-medium text-muted ring-1 ring-border">
              Отклонено: <span className="tabular-nums">{counts.dismissed}</span>
            </span>
            <span className="inline-flex items-center gap-1 rounded-lg bg-primary-50 px-2 py-1 font-medium text-primary">
              Доказательность: <span className="tabular-nums">{pct(queue!.evidence_rate)}</span>
            </span>
          </div>
        ) : null}
      </header>

      {/* Фильтр-переключатель статуса */}
      <div className="flex flex-wrap gap-1" role="tablist" aria-label="Фильтр по статусу">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            role="tab"
            aria-selected={filter === f.value}
            onClick={() => setFilter(f.value)}
            className={cn(
              'rounded-lg px-3 py-1.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
              filter === f.value
                ? 'bg-primary text-white'
                : 'bg-surface text-muted ring-1 ring-border hover:text-ink',
            )}
          >
            {f.label}
            {counts ? (
              <span className="ml-1.5 tabular-nums opacity-80">
                {f.value === 'pending'
                  ? counts.pending
                  : f.value === 'validated'
                    ? counts.validated
                    : counts.dismissed}
              </span>
            ) : null}
          </button>
        ))}
      </div>

      {/* Контент */}
      <Card className="p-0">
        {state === 'loading' ? (
          <TableSkeleton />
        ) : state === 'error' ? (
          <div className="flex flex-col items-center gap-3 py-12 text-center">
            <TriangleAlert className="h-8 w-8 text-high-text" aria-hidden />
            <p className="max-w-sm text-sm text-muted">{error ?? 'Не удалось загрузить очередь.'}</p>
            <button
              type="button"
              onClick={() => load(filter)}
              className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-1.5 text-sm font-medium text-ink transition-colors hover:border-primary hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            >
              <RotateCw className="h-4 w-4" aria-hidden />
              Повторить
            </button>
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-16 text-center text-muted">
            <Inbox className="h-8 w-8" aria-hidden />
            <p className="text-sm">Нет событий в этом статусе</p>
          </div>
        ) : (
          <ReviewTable
            items={items}
            busyId={busyId}
            onRowClick={(id) => navigate(`/incidents/${id}`)}
            onDecide={decide}
          />
        )}
      </Card>
    </div>
  )
}

// ── Таблица ──────────────────────────────────────────────────────────────────

function ReviewTable({
  items,
  busyId,
  onRowClick,
  onDecide,
}: {
  items: ReviewItem[]
  busyId: string | null
  onRowClick: (id: string) => void
  onDecide: (id: string, decision: 'validated' | 'dismissed') => void
}) {
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b-2 border-border bg-bg text-left">
          <Th>Код аларма</Th>
          <Th>Severity</Th>
          <Th>ТС</Th>
          <Th>Время</Th>
          <Th align="center">Видео</Th>
          <Th>Статус</Th>
          <Th>Заметка</Th>
          <Th align="right">Решение</Th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <ReviewRow
            key={item.incident_id}
            item={item}
            busy={busyId === item.incident_id}
            onClick={() => onRowClick(item.incident_id)}
            onDecide={onDecide}
          />
        ))}
      </tbody>
    </table>
  )
}

function ReviewRow({
  item,
  busy,
  onClick,
  onDecide,
}: {
  item: ReviewItem
  busy: boolean
  onClick: () => void
  onDecide: (id: string, decision: 'validated' | 'dismissed') => void
}) {
  return (
    <tr
      role="button"
      tabIndex={0}
      aria-label={`Инцидент ${item.incident_id}, ${item.alarm_label_ru}, ${item.vehicle_plate}`}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick()
        }
      }}
      className="cursor-pointer border-b border-border transition-colors hover:bg-bg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary"
    >
      <td className="px-3 py-2 font-medium text-ink">{item.alarm_label_ru}</td>
      <td className="px-3 py-2">
        <SeverityBadge severity={item.severity} label={SEVERITY_LABEL[item.severity]} />
      </td>
      <td className="px-3 py-2 text-ink">{item.vehicle_plate}</td>
      <td className="whitespace-nowrap px-3 py-2 tabular-nums text-muted">
        {formatDateTime(item.ts)}
      </td>
      <td className="px-3 py-2 text-center">
        {item.video_available ? (
          <span className="inline-flex items-center gap-1 rounded-lg bg-ok-bg px-2 py-0.5 text-xs font-medium text-ok-text">
            <Video className="h-3.5 w-3.5" aria-hidden />
            видео ✓
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 rounded-lg bg-bg px-2 py-0.5 text-xs font-medium text-muted ring-1 ring-border">
            <VideoOff className="h-3.5 w-3.5" aria-hidden />
            видео —
          </span>
        )}
      </td>
      <td className="px-3 py-2">
        <StatusBadge status={item.status} />
      </td>
      <td className="max-w-[220px] px-3 py-2 text-muted">
        <span className="line-clamp-2" title={item.note ?? undefined}>
          {item.note || '—'}
        </span>
      </td>
      {/* Действия: для pending и перезапись для решённых (§11). stopPropagation —
          чтобы кнопки не триггерили навигацию строки (как врезка /trip в EventsFeed). */}
      <td className="px-3 py-2 text-right">
        <div className="inline-flex items-center gap-1.5">
          <button
            type="button"
            disabled={busy}
            onClick={(e) => {
              e.stopPropagation()
              onDecide(item.incident_id, 'validated')
            }}
            onKeyDown={(e) => e.stopPropagation()}
            aria-label={`Подтвердить инцидент ${item.incident_id}`}
            className="inline-flex items-center gap-1 rounded-md bg-ok-bg px-2 py-1 text-xs font-semibold text-ok-text transition-colors hover:brightness-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50"
          >
            <Check className="h-3.5 w-3.5" aria-hidden />
            Подтвердить
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={(e) => {
              e.stopPropagation()
              onDecide(item.incident_id, 'dismissed')
            }}
            onKeyDown={(e) => e.stopPropagation()}
            aria-label={`Отклонить инцидент ${item.incident_id}`}
            className="inline-flex items-center gap-1 rounded-md bg-bg px-2 py-1 text-xs font-semibold text-muted ring-1 ring-border transition-colors hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50"
          >
            <X className="h-3.5 w-3.5" aria-hidden />
            Отклонить
          </button>
        </div>
      </td>
    </tr>
  )
}

function Th({
  children,
  align = 'left',
}: {
  children: React.ReactNode
  align?: 'left' | 'right' | 'center'
}) {
  return (
    <th
      className={cn(
        'px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted',
        align === 'right' && 'text-right',
        align === 'center' && 'text-center',
      )}
    >
      {children}
    </th>
  )
}
