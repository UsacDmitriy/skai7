import { CheckCircle2, AlertTriangle, OctagonAlert, DatabaseZap } from 'lucide-react'
import { cn } from '@/components/ui/cn'
import { MetricTile, formatRatio } from '@/components/ai/DataQualityPanel'
import type { ConsistencyReport, ConsistencyStatus } from '@/api/types'

/**
 * f25 · Панель консистентности данных (§10.2/§10.4, кейс Маслова). Против §10.
 *
 * Светофор по 7 детерминированным проверкам + сводные `evidence_rate` /
 * `speed_agreement_rate`. НЕ AI-блок (§10.0): без governance-меты. Вставляется в
 * `Metrics.tsx` ниже `DataQualityPanel` (f21). Пустой/ошибочный ответ → заглушка.
 */

interface StatusSpec {
  ring: string
  chip: string
  Icon: React.ElementType
  label: string
}

/** Светофор по `status` (§10.2). Не только цветом — иконка + текст статуса. */
const STATUS: Record<ConsistencyStatus, StatusSpec> = {
  ok: { ring: 'border-ok/40', chip: 'bg-ok-bg text-ok-text', Icon: CheckCircle2, label: 'В норме' },
  warn: {
    ring: 'border-warning/50',
    chip: 'bg-warning-bg text-warning-text',
    Icon: AlertTriangle,
    label: 'Внимание',
  },
  fail: {
    ring: 'border-critical/50',
    chip: 'bg-critical-bg text-critical-text',
    Icon: OctagonAlert,
    label: 'Проблема',
  },
}

export interface ConsistencyPanelProps {
  /** `null` — ошибка/нет ответа → заглушка (панель не падает). */
  data: ConsistencyReport | null
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-border bg-surface py-10 text-center text-muted">
      <DatabaseZap className="h-7 w-7" aria-hidden />
      <p className="text-sm">Нет данных консистентности.</p>
    </div>
  )
}

export function ConsistencyPanel({ data }: ConsistencyPanelProps) {
  if (!data || data.checks.length === 0) return <EmptyState />

  return (
    <div className="space-y-3">
      {/* Сводные доли */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <MetricTile
          label="Доказательная база"
          value={formatRatio(data.evidence_rate)}
          sub="Доля инцидентов с видеодоказательством"
        />
        <MetricTile
          label="Согласие скоростей"
          value={formatRatio(data.speed_agreement_rate)}
          sub="Доля алармов без расхождения событие ↔ GPS-трек"
        />
      </div>

      {/* Проверки (по строке на проверку) */}
      <ul className="space-y-2" aria-label="Проверки консистентности">
        {data.checks.map((c) => {
          const s = STATUS[c.status] ?? STATUS.warn
          const samples = c.sample_ids.slice(0, 5)
          return (
            <li
              key={c.check_id}
              className={cn('rounded-xl border bg-surface p-3', s.ring)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-ink">{c.title_ru}</p>
                  <p className="mt-0.5 text-xs leading-snug text-muted">{c.description_ru}</p>
                </div>
                <span
                  className={cn(
                    'inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium',
                    s.chip,
                  )}
                >
                  <s.Icon size={11} aria-hidden />
                  {s.label}
                </span>
              </div>

              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
                <span className="tabular-nums">
                  Затронуто: <span className="font-medium text-ink">{c.affected_count}</span> из{' '}
                  {c.total}{' '}
                  <span className="text-muted">({formatRatio(c.ratio)})</span>
                </span>
                {samples.length > 0 && (
                  <span className="inline-flex flex-wrap items-center gap-1">
                    <span>Примеры:</span>
                    {samples.map((id) => (
                      <code
                        key={id}
                        className="rounded bg-border/40 px-1 py-0.5 font-mono text-[11px] text-ink"
                      >
                        {id}
                      </code>
                    ))}
                  </span>
                )}
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export default ConsistencyPanel
