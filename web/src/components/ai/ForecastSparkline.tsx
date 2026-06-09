import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import type { RiskForecastPoint } from '../../api/types'

export interface ForecastSparklineProps {
  trend: RiskForecastPoint[]
  /** Подсветить точку аномалии (обычно последняя или пиковая). */
  anomaly?: boolean
  className?: string
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  if (Number.isNaN(d.getTime())) return dateStr
  return new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short' }).format(d)
}

/** Индекс точки с максимальным predicted_events (для аномалии). */
function findAnomalyPoint(
  trend: RiskForecastPoint[],
): RiskForecastPoint | undefined {
  if (!trend.length) return undefined
  return trend.reduce((max, p) => (p.predicted_events > max.predicted_events ? p : max))
}

export function ForecastSparkline({ trend, anomaly, className }: ForecastSparklineProps) {
  if (!trend.length) {
    return (
      <div className={`flex items-center justify-center text-xs text-muted h-12 ${className ?? ''}`}>
        Нет данных
      </div>
    )
  }

  const anomalyPoint = anomaly ? findAnomalyPoint(trend) : undefined

  const data = trend.map((p) => ({
    date: p.date,
    label: formatDate(p.date),
    value: p.predicted_events,
    ci_low: p.ci_low,
    ci_high: p.ci_high,
  }))

  return (
    <div className={`tabular-nums ${className ?? ''}`} style={{ height: 56 }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 4, right: 2, bottom: 0, left: 2 }}>
          <XAxis dataKey="label" hide />
          <YAxis hide domain={['auto', 'auto']} />
          <Tooltip
            contentStyle={{ fontSize: 11, padding: '4px 8px' }}
            formatter={(v: number) => [v.toFixed(1), 'событий']}
            labelFormatter={(l) => String(l)}
          />
          {/* Доверительный коридор */}
          <Area
            dataKey="ci_high"
            stroke="none"
            fill="var(--color-primary-50)"
            isAnimationActive={false}
          />
          <Area
            dataKey="ci_low"
            stroke="none"
            fill="var(--color-surface)"
            isAnimationActive={false}
          />
          {/* Линия прогноза */}
          <Line
            type="monotone"
            dataKey="value"
            stroke="var(--color-primary)"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
          {/* Точка аномалии */}
          {anomalyPoint && (
            <ReferenceDot
              x={formatDate(anomalyPoint.date)}
              y={anomalyPoint.predicted_events}
              r={4}
              fill="var(--sev-critical)"
              stroke="var(--color-surface)"
              strokeWidth={1.5}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
