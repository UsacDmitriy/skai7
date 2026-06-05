import { Video } from 'lucide-react'
import { cn } from './cn'
import type { Severity } from './SeverityBadge'

export interface TimelineEvent {
  /** Смещение события относительно начала трека (сек). */
  ts_offset: number
  alarm_code: string
  label: string
  severity: Severity
  has_video: boolean
}

export interface TimelineProps {
  events: TimelineEvent[]
  onSelect?: (e: TimelineEvent) => void
  /** Опциональный курсор-плейхед (сек); вне диапазона/undefined — скрыт. */
  playheadOffset?: number
}

// Цвет точки по severity (маппинг d1: medium→warning, low→ok). Неизвестный → фолбэк.
const DOT_COLOR: Record<Severity, string> = {
  critical: 'bg-critical',
  high: 'bg-high',
  medium: 'bg-warning',
  low: 'bg-ok',
}
const FALLBACK_DOT = 'bg-muted'

function dotColor(severity: Severity): string {
  return DOT_COLOR[severity] ?? FALLBACK_DOT
}

const clamp = (pct: number) => Math.min(100, Math.max(0, pct))

// Время в подписи: «t=0», «+12s», «-3s».
function fmtOffset(s: number): string {
  if (s === 0) return 't=0'
  return `${s > 0 ? '+' : ''}${s}s`
}

export function Timeline({ events, onSelect, playheadOffset }: TimelineProps) {
  // Диапазон трека по событиям. Пустой список → нет точек, рисуем только линию.
  const offsets = events.map((e) => e.ts_offset)
  const min = offsets.length ? Math.min(...offsets) : 0
  const max = offsets.length ? Math.max(...offsets) : 0
  const range = max - min

  // Единственная точка / совпадающие offset (range=0) → центр, без деления на ноль.
  const toPct = (offset: number) => (range === 0 ? 50 : clamp(((offset - min) / range) * 100))

  // Плейхед виден только если задан, диапазон ненулевой и значение внутри [min,max].
  const playheadVisible =
    playheadOffset != null && range > 0 && playheadOffset >= min && playheadOffset <= max
  const playheadPct = playheadVisible ? toPct(playheadOffset as number) : 0

  return (
    <div className="w-full px-4 py-8">
      <div className="relative h-1 w-full rounded-full bg-primary">
        {/* Курсор-плейхед */}
        {playheadVisible && (
          <div
            className="absolute top-1/2 h-6 w-0.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-ink"
            style={{ left: `${playheadPct}%` }}
            aria-hidden
          />
        )}

        {events.map((ev, i) => {
          const isZero = ev.ts_offset === 0
          return (
            <button
              key={`${ev.alarm_code}-${ev.ts_offset}-${i}`}
              type="button"
              onClick={() => onSelect?.(ev)}
              aria-label={`${ev.label}, ${fmtOffset(ev.ts_offset)}${ev.has_video ? ', есть видео' : ''}`}
              className="group absolute top-1/2 -translate-x-1/2 -translate-y-1/2 focus-visible:outline-none"
              style={{ left: `${toPct(ev.ts_offset)}%` }}
            >
              {/* Точка-событие: t=0 — critical и крупнее остальных. */}
              <span
                className={cn(
                  'block rounded-full ring-2 ring-surface transition-transform group-hover:scale-125',
                  'group-focus-visible:ring-2 group-focus-visible:ring-primary',
                  isZero ? 'h-4 w-4 bg-critical' : cn('h-3 w-3', dotColor(ev.severity)),
                )}
              />
              {/* Значок видео у точек с has_video. */}
              {ev.has_video && (
                <Video
                  size={12}
                  className="absolute -top-5 left-1/2 -translate-x-1/2 text-muted"
                  aria-hidden
                />
              )}
              {/* Подпись времени — табличные цифры. */}
              <span className="absolute top-4 left-1/2 -translate-x-1/2 whitespace-nowrap text-[11px] tabular-nums text-muted">
                {fmtOffset(ev.ts_offset)}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
