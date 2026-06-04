import { type ReactNode } from 'react'
import { cn } from './cn'
import { type Severity } from './SeverityBadge'

export interface CardProps {
  children: ReactNode
  /** `incident` — карточка ленты с цветной левой полосой по severity. */
  variant?: 'default' | 'incident'
  /** Для `incident`: цвет border-left 4px (маппинг d1, medium→warning, low→ok). */
  severity?: Severity
  /** Выделенное состояние (фон primary-50 + рамка primary). */
  selected?: boolean
  onClick?: () => void
  className?: string
}

// Цвет левой полосы incident-карточки — токены d1 (medium→warning, low→ok).
const SEVERITY_BORDER: Record<Severity, string> = {
  critical: 'border-l-critical',
  high: 'border-l-high',
  medium: 'border-l-warning',
  low: 'border-l-ok',
}

export function Card({
  children,
  variant = 'default',
  severity = 'low',
  selected = false,
  onClick,
  className,
}: CardProps) {
  const interactive = typeof onClick === 'function'
  const isIncident = variant === 'incident'
  return (
    <div
      onClick={onClick}
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onClick?.()
              }
            }
          : undefined
      }
      className={cn(
        'rounded-md border border-border bg-surface transition-all duration-150 ease-in-out',
        isIncident ? cn('border-l-4 px-4 py-3', SEVERITY_BORDER[severity]) : 'p-5',
        interactive && 'cursor-pointer',
        interactive &&
          !selected &&
          'hover:border-primary hover:shadow-[0_2px_6px_rgba(30,58,138,0.10)]',
        selected && 'border-primary bg-primary-50',
        className,
      )}
    >
      {children}
    </div>
  )
}
