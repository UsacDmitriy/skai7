import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Clock, MapPin, SlidersHorizontal } from 'lucide-react'
import * as client from '@/api/client'
import type { IncidentSummary, Severity, Source } from '@/api/types'
import { Card, ScoreBar, SeverityBadge } from '@/components'
import { cn } from '@/components/ui/cn'

/**
 * f4 · Монитор (scaffold). Маршрут `/monitor` · референс `ui/02 Живой мониторинг/`.
 * Лента инцидентов из `client.listIncidents()` — `Card(variant=incident)` с
 * severity-border, сортировкой и фильтрами. Карта/таймлайн — плейсхолдер (# TODO).
 * Полный wiring карты/трека — за рамками P0 (см. f6).
 */

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: 'Критично',
  high: 'Высокий',
  medium: 'Средний',
  low: 'Низкий',
}

const SOURCE_LABEL: Record<Source, string> = {
  DMS: 'DMS',
  ADAS: 'ADAS',
  TELEMATICS: 'Телематика',
  COMBINED: 'Оба',
  DIAGNOSTIC: 'Диагностика',
}

type SortKey = 'ts' | 'risk_score'

const SEVERITY_FILTERS: { value: Severity | 'all'; label: string }[] = [
  { value: 'all', label: 'Все' },
  { value: 'critical', label: 'Критич.' },
  { value: 'high', label: 'Высокий' },
  { value: 'medium', label: 'Средний' },
  { value: 'low', label: 'Низкий' },
]

const SOURCE_FILTERS: { value: Source | 'all'; label: string }[] = [
  { value: 'all', label: 'Все источники' },
  { value: 'DMS', label: 'DMS' },
  { value: 'ADAS', label: 'ADAS' },
  { value: 'TELEMATICS', label: 'Телематика' },
  { value: 'COMBINED', label: 'Оба' },
  { value: 'DIAGNOSTIC', label: 'Диагностика' },
]

function formatTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'rounded-md border px-2.5 py-1 text-xs font-medium transition-colors',
        active
          ? 'border-primary bg-primary-50 text-primary'
          : 'border-border bg-surface text-muted hover:border-primary hover:text-ink',
      )}
    >
      {children}
    </button>
  )
}

export default function Monitor() {
  const navigate = useNavigate()
  const [incidents, setIncidents] = useState<IncidentSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [severity, setSeverity] = useState<Severity | 'all'>('all')
  const [source, setSource] = useState<Source | 'all'>('all')
  const [sortKey, setSortKey] = useState<SortKey>('ts')

  useEffect(() => {
    let alive = true
    setLoading(true)
    client
      .listIncidents()
      .then((data) => alive && setIncidents(data))
      .catch((e: unknown) => alive && setError(e instanceof Error ? e.message : 'Ошибка загрузки'))
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
  }, [])

  const visible = useMemo(() => {
    let rows = incidents
    if (severity !== 'all') rows = rows.filter((r) => r.severity === severity)
    if (source !== 'all') rows = rows.filter((r) => r.source === source)
    return [...rows].sort((a, b) =>
      sortKey === 'risk_score'
        ? b.risk_score - a.risk_score
        : b.ts.localeCompare(a.ts),
    )
  }, [incidents, severity, source, sortKey])

  return (
    <div className="grid h-full grid-cols-1 gap-4 lg:grid-cols-[minmax(380px,440px)_1fr]">
      {/* ── Лента инцидентов ────────────────────────────────────────────────── */}
      <div className="flex min-h-0 flex-col">
        <div className="mb-3 flex items-center justify-between">
          <h1 className="text-lg font-semibold text-ink">
            Лента инцидентов{' '}
            <span className="text-sm font-normal text-muted">({visible.length})</span>
          </h1>
          <div className="flex items-center gap-1 text-xs text-muted">
            <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden />
            Сортировка:
            <button
              type="button"
              onClick={() => setSortKey('ts')}
              className={cn('px-1', sortKey === 'ts' ? 'font-semibold text-ink' : 'hover:text-ink')}
            >
              время
            </button>
            <span>·</span>
            <button
              type="button"
              onClick={() => setSortKey('risk_score')}
              className={cn(
                'px-1',
                sortKey === 'risk_score' ? 'font-semibold text-ink' : 'hover:text-ink',
              )}
            >
              риск
            </button>
          </div>
        </div>

        <div className="mb-3 space-y-2">
          <div className="flex flex-wrap gap-1.5">
            {SEVERITY_FILTERS.map((f) => (
              <Chip key={f.value} active={severity === f.value} onClick={() => setSeverity(f.value)}>
                {f.label}
              </Chip>
            ))}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {SOURCE_FILTERS.map((f) => (
              <Chip key={f.value} active={source === f.value} onClick={() => setSource(f.value)}>
                {f.label}
              </Chip>
            ))}
          </div>
        </div>

        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
          {loading && <p className="py-8 text-center text-sm text-muted">Загрузка…</p>}
          {error && <p className="py-8 text-center text-sm text-critical-text">{error}</p>}
          {!loading && !error && visible.length === 0 && (
            <p className="py-8 text-center text-sm text-muted">Нет инцидентов по фильтрам.</p>
          )}
          {visible.map((inc) => (
            <Card
              key={inc.id}
              variant="incident"
              severity={inc.severity}
              onClick={() => navigate(`/incidents/${inc.id}`)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-ink">{inc.alarm_label_ru}</div>
                  <div className="mt-0.5 truncate text-xs text-muted">
                    {inc.vehicle_model} · {inc.vehicle_plate} · {inc.driver}
                  </div>
                </div>
                <SeverityBadge severity={inc.severity} label={SEVERITY_LABEL[inc.severity]} />
              </div>
              <div className="mt-2 flex items-center justify-between gap-3">
                <ScoreBar score={inc.risk_score} className="max-w-[160px] flex-1" />
                <div className="flex shrink-0 items-center gap-3 text-xs text-muted">
                  <span className="inline-flex items-center gap-1">
                    <Clock className="h-3 w-3" aria-hidden />
                    {formatTime(inc.ts)}
                  </span>
                  <span className="rounded bg-bg px-1.5 py-0.5">{SOURCE_LABEL[inc.source]}</span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* ── Карта / таймлайн — плейсхолдер ──────────────────────────────────── */}
      <Card className="hidden min-h-[400px] place-items-center lg:grid">
        {/* TODO (f6): интерактивная карта инцидентов + таймлайн поездки. */}
        <div className="text-center">
          <MapPin className="mx-auto h-10 w-10 text-border" aria-hidden />
          <div className="mt-2 text-sm font-medium text-muted">Карта инцидентов</div>
          <p className="mt-1 text-xs text-muted"># TODO (f6): карта + таймлайн поездки</p>
        </div>
      </Card>
    </div>
  )
}
