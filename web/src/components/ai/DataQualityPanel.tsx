import type { ReactNode } from 'react'
import { CheckCircle2, AlertTriangle, OctagonAlert } from 'lucide-react'
import { cn } from '@/components/ui/cn'
import type { DataQuality } from '@/api/types'

/**
 * f21 · Панель качества данных (§8.7). Против `00-CONTRACT.md` §8.7.
 *
 * Плитки `*_ratio` со «светофором»: качество данных хуже порога → жёлтое
 * предупреждение, заметно хуже → красный. Метрики чисто детерминированные
 * (приходят из `GET /api/metrics/data-quality` либо фикстур), без `Date.now()`.
 *
 * `MetricTile` переиспользуется страницей `Metrics.tsx` для KPI AI-слоя.
 */

// ── Светофор: тон плитки ───────────────────────────────────────────────────────

export type MetricTone = 'ok' | 'warn' | 'bad' | 'neutral'

const TONE: Record<
  Exclude<MetricTone, 'neutral'>,
  { ring: string; chip: string; Icon: typeof CheckCircle2; label: string }
> = {
  ok: { ring: 'border-ok/40', chip: 'bg-ok-bg text-ok-text', Icon: CheckCircle2, label: 'В норме' },
  warn: {
    ring: 'border-warning/50',
    chip: 'bg-warning-bg text-warning-text',
    Icon: AlertTriangle,
    label: 'Внимание',
  },
  bad: {
    ring: 'border-critical/50',
    chip: 'bg-critical-bg text-critical-text',
    Icon: OctagonAlert,
    label: 'Низкое качество',
  },
}

// ── Переиспользуемая плитка метрики ────────────────────────────────────────────

export interface MetricTileProps {
  label: string
  /** Уже отформатированное значение (доля → проценты, время → «N мин»). */
  value: ReactNode
  /** Подпись под значением: что измеряем / ориентир. */
  sub?: string
  tone?: MetricTone
}

export function MetricTile({ label, value, sub, tone = 'neutral' }: MetricTileProps) {
  const t = tone === 'neutral' ? null : TONE[tone]
  return (
    <div
      className={cn(
        'rounded-xl border bg-surface p-4',
        t ? t.ring : 'border-border',
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-muted">{label}</span>
        {t ? (
          <span
            className={cn(
              'inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium',
              t.chip,
            )}
          >
            <t.Icon size={11} aria-hidden />
            {t.label}
          </span>
        ) : null}
      </div>
      <div className="mt-2 text-2xl font-bold tabular-nums text-ink">{value}</div>
      {sub ? <p className="mt-1 text-xs leading-snug text-muted">{sub}</p> : null}
    </div>
  )
}

// ── Доля → проценты (ru-RU, до 1 знака) ────────────────────────────────────────

/** `0.06 → «6 %»`. Доли вне [0,1] всё равно рендерятся (бэкенд — источник истины). */
export function formatRatio(value: number): string {
  return `${(value * 100).toLocaleString('ru-RU', { maximumFractionDigits: 1 })} %`
}

// ── Конфигурация плиток качества (направление + пороги светофора) ──────────────

type Direction = 'low' | 'high' // 'low' — меньше лучше; 'high' — больше лучше

interface DqMetric {
  key: keyof DataQuality
  label: string
  dir: Direction
  /** Порог «ещё норма». */
  warn: number
  /** Порог «уже плохо». */
  bad: number
  sub: string
}

/** §8.7: 4 метрики «меньше — лучше» + покрытие видео «больше — лучше». */
const DQ_METRICS: DqMetric[] = [
  {
    key: 'camera_offline_ratio',
    label: 'Камеры офлайн',
    dir: 'low',
    warn: 0.05,
    bad: 0.15,
    sub: 'Доля ТС без видеопотока',
  },
  {
    key: 'missing_gps_ratio',
    label: 'Пропуски GPS',
    dir: 'low',
    warn: 0.1,
    bad: 0.25,
    sub: 'Доля инцидентов без координат',
  },
  {
    key: 'missing_media_ratio',
    label: 'Пропуски медиа',
    dir: 'low',
    warn: 0.05,
    bad: 0.15,
    sub: 'Доля инцидентов без видео/фото',
  },
  {
    key: 'weather_mismatch_rate',
    label: 'Рассогласование погоды',
    dir: 'low',
    warn: 0.1,
    bad: 0.25,
    sub: 'Сцена ↔ метеоданные расходятся',
  },
  {
    key: 'incidents_with_video_ratio',
    label: 'Инциденты с видео',
    dir: 'high',
    warn: 0.9,
    bad: 0.7,
    sub: 'Доля инцидентов, подкреплённых видео',
  },
]

/** Тон плитки по значению и направлению порогов (§8.7 «светофор»). */
export function qualityTone(value: number, m: Pick<DqMetric, 'dir' | 'warn' | 'bad'>): MetricTone {
  if (m.dir === 'low') {
    if (value <= m.warn) return 'ok'
    if (value <= m.bad) return 'warn'
    return 'bad'
  }
  // dir === 'high' (warn > bad)
  if (value >= m.warn) return 'ok'
  if (value >= m.bad) return 'warn'
  return 'bad'
}

// ── Панель ─────────────────────────────────────────────────────────────────────

export interface DataQualityPanelProps {
  data: DataQuality
}

export function DataQualityPanel({ data }: DataQualityPanelProps) {
  return (
    <div
      className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
      role="list"
      aria-label="Качество данных"
    >
      {DQ_METRICS.map((m) => {
        const value = data[m.key]
        return (
          <div key={m.key} role="listitem">
            <MetricTile
              label={m.label}
              value={formatRatio(value)}
              sub={m.sub}
              tone={qualityTone(value, m)}
            />
          </div>
        )
      })}
    </div>
  )
}

export default DataQualityPanel
