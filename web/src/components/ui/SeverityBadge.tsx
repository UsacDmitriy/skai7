import { cn } from './cn'

/** Severity из API-контракта §3.1. */
export type Severity = 'critical' | 'high' | 'medium' | 'low'

export interface SeverityBadgeProps {
  severity: Severity
  label: string
  className?: string
}

/**
 * Маппинг API-severity → токен-палитра d1 (CONTRACT §4):
 *   critical→critical · high→high · medium→warning(жёлтый) · low→ok(зелёный).
 * badge — фон+текст бейджа, dot — цвет 6px-кружка.
 */
const TOKEN: Record<Severity, { badge: string; dot: string }> = {
  critical: { badge: 'bg-critical-bg text-critical-text', dot: 'bg-critical' },
  high: { badge: 'bg-high-bg text-high-text', dot: 'bg-high' },
  medium: { badge: 'bg-warning-bg text-warning-text', dot: 'bg-warning' },
  low: { badge: 'bg-ok-bg text-ok-text', dot: 'bg-ok' },
}

export function SeverityBadge({ severity, label, className }: SeverityBadgeProps) {
  const token = TOKEN[severity]
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-xl pl-1.5 pr-2 py-0.5 text-xs font-medium',
        token.badge,
        className,
      )}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', token.dot)} aria-hidden />
      {label}
    </span>
  )
}
