import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, RotateCw, Search, Video, VideoOff } from 'lucide-react'
import * as client from '@/api/client'
import type { IncidentSummary, Severity, Source } from '@/api/types'
import { Card, ScoreBar, SeverityBadge } from '@/components'
import { RoleToggle } from '@/components/map'
import type { Role } from '@/components/map'
import { cn } from '@/components/ui/cn'

/**
 * f5 · Лента событий (`/`). Стартовый экран — таблица всех алярмов парка.
 * Данные — `client.listIncidents()` → `IncidentSummary[]` (§3.1). Один ряд = один алярм,
 * клик → карточка `/incidents/:id` (владелец карточки — f4).
 *
 * Таблица собрана локально (не `DataTable` d2): Check требует severity-border строки и
 * клавиатурную активацию ряда (Enter/Space) — примитив d2 этого не даёт, а его файл не наш.
 * UI-атомы переиспользуются: `SeverityBadge`, `ScoreBar`, `Card`; роль — `RoleToggle` d4.
 */

// ── Конфиг ────────────────────────────────────────────────────────────────────

/** Таймзона парка (env, иначе UTC) — `ts` приходит ISO-8601 UTC. */
const PARK_TZ = (import.meta.env.VITE_PARK_TIMEZONE as string | undefined) ?? 'UTC'

/** Порог риск-скора для плашки «В зоне риска». */
const RISK_ZONE_THRESHOLD = 70

/** Дебаунс ввода поиска, мс. */
const SEARCH_DEBOUNCE_MS = 250

// ── Маппинги (контракт §3.1) ──────────────────────────────────────────────────

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: 'Критично',
  high: 'Высокий',
  medium: 'Средний',
  low: 'Низкий',
}

// Левая полоса строки — токены d1 (medium→warning, low→ok). Совпадает с Card.
const SEVERITY_BORDER: Record<Severity, string> = {
  critical: 'border-l-critical',
  high: 'border-l-high',
  medium: 'border-l-warning',
  low: 'border-l-ok',
}

/** Бейдж источника: эмодзи + текстовая подпись (a11y — не только эмодзи). */
const SOURCE_BADGE: Record<Source, { emoji: string; text: string }> = {
  COMBINED: { emoji: '⚡📹', text: 'Оба' },
  ADAS: { emoji: '📹', text: 'ВА' },
  DMS: { emoji: '📹', text: 'ВА' },
  TELEMATICS: { emoji: '⚡', text: 'Тел' },
  DIAGNOSTIC: { emoji: '⚙', text: 'Диагностика' },
}

/** Логист видит только телематику/ADAS (без DMS-алармов и COMBINED по DMS-части). */
const LOGIST_SOURCES: Source[] = ['TELEMATICS', 'ADAS']

// ── Форматтеры ────────────────────────────────────────────────────────────────

function formatTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: PARK_TZ,
  })
}

function SourceBadge({ source }: { source: Source }) {
  const b = SOURCE_BADGE[source]
  return (
    <span
      aria-label={`Источник: ${b.text}`}
      className="inline-flex items-center gap-1 whitespace-nowrap rounded-md bg-bg px-1.5 py-0.5 text-xs font-medium text-muted"
    >
      <span aria-hidden>{b.emoji}</span>
      {b.text}
    </span>
  )
}

// ── Счётчики ──────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  loading,
}: {
  label: string
  value: number
  loading: boolean
}) {
  return (
    <Card className="px-4 py-3">
      <div className="text-xs font-medium text-muted">{label}</div>
      {loading ? (
        <div className="mt-1 h-7 w-10 animate-pulse rounded bg-border" />
      ) : (
        <div className="mt-0.5 text-2xl font-bold tabular-nums text-ink">{value}</div>
      )}
    </Card>
  )
}

// ── Хук дебаунса ──────────────────────────────────────────────────────────────

function useDebounced<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return debounced
}

// ── Toggle «Нет видео» ────────────────────────────────────────────────────────

function NoVideoToggle({
  active,
  onToggle,
}: {
  active: boolean
  onToggle: () => void
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onToggle}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1',
        active
          ? 'border-primary bg-primary-50 text-primary'
          : 'border-border bg-surface text-muted hover:border-primary hover:text-ink',
      )}
    >
      <VideoOff className="h-4 w-4" aria-hidden />
      Нет видео
    </button>
  )
}

// ── Страница ──────────────────────────────────────────────────────────────────

export default function EventsFeed() {
  const navigate = useNavigate()
  const [incidents, setIncidents] = useState<IncidentSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  const [role, setRole] = useState<Role>('dispatcher')
  const [noVideo, setNoVideo] = useState(false)
  const [query, setQuery] = useState('')
  const debouncedQuery = useDebounced(query, SEARCH_DEBOUNCE_MS)

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError(null)
    client
      .listIncidents()
      .then((data) => {
        if (alive) setIncidents(data)
      })
      .catch((e: unknown) => {
        if (alive) setError(e instanceof Error ? e.message : 'Ошибка загрузки')
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [reloadKey])

  // Ролевая + «нет видео» фильтрация — общая база для счётчиков и поиска.
  const filtered = useMemo(() => {
    let rows = incidents
    if (role === 'logist') rows = rows.filter((r) => LOGIST_SOURCES.includes(r.source))
    if (noVideo) rows = rows.filter((r) => r.video_available === false)
    return rows
  }, [incidents, role, noVideo])

  // Счётчики синхронны с фильтрами (роль + «нет видео»), независимо от поиска.
  const stats = useMemo(
    () => ({
      risk: filtered.filter((r) => r.risk_score >= RISK_ZONE_THRESHOLD).length,
      critical: filtered.filter((r) => r.severity === 'critical').length,
      noVideo: filtered.filter((r) => r.video_available === false).length,
      closed: filtered.filter((r) => r.status === 'closed').length,
    }),
    [filtered],
  )

  // Поиск по ТС/водителю поверх отфильтрованного набора (регистронезависимо).
  const visible = useMemo(() => {
    const q = debouncedQuery.trim().toLowerCase()
    if (!q) return filtered
    return filtered.filter(
      (r) =>
        r.vehicle_plate.toLowerCase().includes(q) ||
        (r.driver ?? '').toLowerCase().includes(q),
    )
  }, [filtered, debouncedQuery])

  const isEmpty = !loading && !error && filtered.length === 0
  const isNoMatch = !loading && !error && filtered.length > 0 && visible.length === 0

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      {/* ── Заголовок + роль ───────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-semibold text-ink">
          Лента событий{' '}
          {!loading && !error && (
            <span className="text-sm font-normal text-muted">({visible.length})</span>
          )}
        </h1>
        <RoleToggle value={role} onChange={setRole} />
      </div>

      {/* ── Счётчики ───────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="В зоне риска" value={stats.risk} loading={loading} />
        <StatCard label="Критичных" value={stats.critical} loading={loading} />
        <StatCard label="Без видео" value={stats.noVideo} loading={loading} />
        <StatCard label="Закрыто" value={stats.closed} loading={loading} />
      </div>

      {/* ── Панель: поиск + toggle ─────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-[220px] flex-1">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
            aria-hidden
          />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Поиск по ТС или водителю"
            aria-label="Поиск по госномеру или водителю"
            className="w-full rounded-md border border-border bg-surface py-1.5 pl-9 pr-3 text-sm text-ink placeholder:text-muted focus-visible:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1"
          />
        </div>
        <NoVideoToggle active={noVideo} onToggle={() => setNoVideo((v) => !v)} />
      </div>

      {/* ── Таблица / состояния ────────────────────────────────────────────── */}
      <Card className="min-h-0 flex-1 overflow-auto p-0">
        {loading && <TableSkeleton />}

        {error && (
          <div className="grid place-items-center gap-3 px-4 py-16 text-center">
            <AlertTriangle className="h-10 w-10 text-critical" aria-hidden />
            <div>
              <div className="text-sm font-medium text-ink">Не удалось загрузить ленту</div>
              <p className="mt-1 text-xs text-muted">{error}</p>
            </div>
            <button
              type="button"
              onClick={() => setReloadKey((k) => k + 1)}
              className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-1.5 text-sm font-medium text-ink transition-colors hover:border-primary hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1"
            >
              <RotateCw className="h-4 w-4" aria-hidden />
              Повторить
            </button>
          </div>
        )}

        {isEmpty && (
          <p className="px-4 py-16 text-center text-sm text-muted">Нет алярмов</p>
        )}

        {!loading && !error && !isEmpty && (
          <EventsTable
            rows={visible}
            noMatch={isNoMatch}
            onRowClick={(id) => navigate(`/incidents/${id}`)}
          />
        )}
      </Card>
    </div>
  )
}

// ── Таблица ───────────────────────────────────────────────────────────────────

function EventsTable({
  rows,
  noMatch,
  onRowClick,
}: {
  rows: IncidentSummary[]
  noMatch: boolean
  onRowClick: (id: string) => void
}) {
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b-2 border-border bg-bg text-left">
          <Th>Тип</Th>
          <Th>Источник</Th>
          <Th>Severity</Th>
          <Th>Риск</Th>
          <Th>ТС · водитель</Th>
          <Th align="right">Скорость</Th>
          <Th>Время</Th>
          <Th>Адрес</Th>
          <Th align="center">Видео</Th>
        </tr>
      </thead>
      <tbody>
        {noMatch ? (
          <tr>
            <td colSpan={9} className="px-3 py-12 text-center text-sm text-muted">
              Ничего не найдено
            </td>
          </tr>
        ) : (
          rows.map((r) => <EventRow key={r.id} row={r} onClick={() => onRowClick(r.id)} />)
        )}
      </tbody>
    </table>
  )
}

function EventRow({ row, onClick }: { row: IncidentSummary; onClick: () => void }) {
  return (
    <tr
      role="button"
      tabIndex={0}
      aria-label={`${row.alarm_label_ru}, ${row.vehicle_plate}`}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick()
        }
      }}
      className="cursor-pointer border-b border-border transition-colors hover:bg-bg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary"
    >
      <td
        className={cn(
          'border-l-4 px-3 py-2 font-medium text-ink',
          SEVERITY_BORDER[row.severity],
        )}
      >
        {row.alarm_label_ru}
      </td>
      <td className="px-3 py-2">
        <SourceBadge source={row.source} />
      </td>
      <td className="px-3 py-2">
        <SeverityBadge severity={row.severity} label={SEVERITY_LABEL[row.severity]} />
      </td>
      <td className="px-3 py-2">
        <ScoreBar score={row.risk_score} className="min-w-[120px]" />
      </td>
      <td className="px-3 py-2 text-ink">
        <div className="font-medium">{row.vehicle_plate}</div>
        <div className="text-xs text-muted">{row.driver || '—'}</div>
      </td>
      <td className="px-3 py-2 text-right tabular-nums text-ink">{row.speed_kmh}</td>
      <td className="whitespace-nowrap px-3 py-2 tabular-nums text-muted">
        {formatTime(row.ts)}
      </td>
      <td className="max-w-[200px] truncate px-3 py-2 text-muted" title={row.address ?? undefined}>
        {row.address ?? '—'}
      </td>
      <td className="px-3 py-2 text-center">
        {row.video_available ? (
          <Video className="mx-auto h-4 w-4 text-ok" aria-label="Видео доступно" />
        ) : (
          <VideoOff className="mx-auto h-4 w-4 text-muted" aria-label="Видео недоступно" />
        )}
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

// ── Скелет загрузки ───────────────────────────────────────────────────────────

function TableSkeleton() {
  return (
    <div className="divide-y divide-border">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 px-3 py-3">
          <div className="h-4 w-1 rounded bg-border" />
          <div className="h-4 flex-1 animate-pulse rounded bg-border" />
          <div className="h-4 w-16 animate-pulse rounded bg-border" />
          <div className="h-4 w-24 animate-pulse rounded bg-border" />
          <div className="h-4 w-20 animate-pulse rounded bg-border" />
        </div>
      ))}
    </div>
  )
}
