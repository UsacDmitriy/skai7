import { AlertTriangle } from 'lucide-react'
import type { WeatherCrossCheck, DiscrepancyKind } from '../../api/types'

export interface DiscrepancyBadgeProps {
  weather: WeatherCrossCheck
}

const KIND_LABEL: Record<DiscrepancyKind, string> = {
  weather: 'тип осадков',
  daynight: 'день/ночь',
  none: '',
}

export function DiscrepancyBadge({ weather }: DiscrepancyBadgeProps) {
  if (!weather.discrepancy) return null

  const detail =
    weather.discrepancy_kind !== 'none'
      ? `Расхождение: ${KIND_LABEL[weather.discrepancy_kind] ?? weather.discrepancy_kind}`
      : 'Данные камеры не совпадают с внешней погодой'

  return (
    <span
      className="inline-flex items-center gap-1 rounded-xl bg-warning-bg text-warning-text border border-warning px-2 py-0.5 text-xs font-medium"
      title={detail}
      aria-label={`Расхождение данных: ${detail}`}
    >
      <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden />
      Камера ↔ погода
    </span>
  )
}
