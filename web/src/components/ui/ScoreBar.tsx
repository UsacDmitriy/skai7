import { cn } from './cn'

export interface ScoreBarProps {
  /** Риск-скор 0..100 (значения вне диапазона клампятся). */
  score: number
  className?: string
}

export function ScoreBar({ score, className }: ScoreBarProps) {
  const value = Math.round(Math.min(100, Math.max(0, score)))
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="h-1 flex-1 overflow-hidden rounded-[2px] bg-border">
        {/* Заливка-градиент зелёный→жёлтый→красный (.score-bar-fill из tokens.css) */}
        <div className="score-bar-fill h-full rounded-[2px]" style={{ width: `${value}%` }} />
      </div>
      <span className="w-8 text-right text-sm font-bold tabular-nums text-ink">{value}</span>
    </div>
  )
}
