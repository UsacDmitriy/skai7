import { CheckCircle2, AlertTriangle, OctagonAlert, HelpCircle } from 'lucide-react'
import { cn } from '../ui/cn'
import type { SpeedCheck, SpeedAgreement } from '../../api/types'

/**
 * f25 · Бейдж сверки скоростей (§10.2/§10.4, кейс Фомина). Против `00-CONTRACT.md` §10.
 *
 * Сравнивает скорость события аларма с GPS-треком (источник истины — GPS, CAN-данных
 * в датасете нет, ASSUMPTION §10.2). НЕ AI-блок (§10.0): без governance-меты.
 * Вставляется в `IncidentCard.tsx` рядом с `SceneContextChip` (f15).
 */

export interface SpeedCheckBadgeProps {
  speed: SpeedCheck
  className?: string
}

interface ToneSpec {
  cls: string
  Icon: React.ElementType
  /** Текст статуса для a11y (светофор не только цветом). */
  label: string
}

/** Тон по согласию скоростей (§10.2): ok→успех · minor→warning · major→danger · no_data→muted. */
const TONE: Record<SpeedAgreement, ToneSpec> = {
  ok: { cls: 'bg-ok-bg text-ok-text border-ok', Icon: CheckCircle2, label: 'совпадает' },
  minor: { cls: 'bg-warning-bg text-warning-text border-warning', Icon: AlertTriangle, label: 'расходится' },
  major: { cls: 'bg-critical-bg text-critical-text border-critical', Icon: OctagonAlert, label: 'расходится' },
  no_data: { cls: 'bg-surface text-muted border-border', Icon: HelpCircle, label: 'нет данных' },
}

const TOOLTIP = 'Источник истины — GPS-трек (CAN-данных в датасете нет, §10.2)'

/** Число → строка км/ч (ru-RU, до 1 знака). `null` уже отсеян вызывающим кодом. */
function kmh(value: number): string {
  return value.toLocaleString('ru-RU', { maximumFractionDigits: 1 })
}

/** Текст бейджа по §10.2 (вынесен для теста). */
export function speedCheckText(speed: SpeedCheck): string {
  if (speed.agreement === 'no_data' || speed.event_speed_kmh === null || speed.track_speed_kmh === null) {
    return 'Скорость: нет данных GPS-трека'
  }
  const head = `Скорость: событие ${kmh(speed.event_speed_kmh)} · GPS ${kmh(speed.track_speed_kmh)}`
  if (speed.agreement === 'ok') return `${head} → совпадает`
  const delta = speed.delta_kmh ?? Math.abs(speed.event_speed_kmh - speed.track_speed_kmh)
  return `${head} → расходится (±${kmh(delta)})`
}

export function SpeedCheckBadge({ speed, className }: SpeedCheckBadgeProps) {
  const tone = TONE[speed.agreement] ?? TONE.no_data
  const text = speedCheckText(speed)

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-xl border px-2 py-0.5 text-xs font-medium',
        tone.cls,
        className,
      )}
      title={TOOLTIP}
      aria-label={`${text}. ${TOOLTIP}`}
    >
      <tone.Icon className="h-3.5 w-3.5 shrink-0" aria-hidden />
      <span>{text}</span>
    </span>
  )
}

export default SpeedCheckBadge
