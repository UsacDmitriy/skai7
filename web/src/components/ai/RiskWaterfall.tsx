import { useCallback, useEffect, useState } from 'react'
import { ChevronDown, RotateCcw, Scale, TriangleAlert } from 'lucide-react'
import * as client from '../../api/client'
import { ApiError } from '../../api/client'
import type { RiskBreakdown } from '../../api/types'
import { cn } from '../ui/cn'

/**
 * f20 · Risk-cause waterfall — explainability (§8.8).
 *
 * Показывает, ПОЧЕМУ у инцидента такой `risk_score`: горизонтальное waterfall-разложение
 * по вкладам слагаемых формулы §2 (severity / speed / night / weather / freq). Вклады уже
 * в очках score (умножены на веса §2), сумма = `total_risk_score` = `risk_score` инцидента.
 *
 * Чистая explainability — ничего «магического». Аддитивный блок: раскрывашка «Почему такой
 * риск» на карточке инцидента и в строке отчёта. Данные тянутся лениво (при первом раскрытии)
 * через f2-клиент `getRiskBreakdown(id)`; ошибка/404 не ломают родителя (блок схлопнут).
 */

export interface RiskWaterfallProps {
  /** id инцидента (для `GET /api/incidents/{id}/risk-breakdown`). */
  id: string
  /** Заголовок раскрывашки. */
  title?: string
  /** Открыть сразу (по умолчанию свёрнуто — ленивая загрузка). */
  defaultOpen?: boolean
  className?: string
}

/** Порядок и подписи слагаемых waterfall (§2 + §8.2 — погодная надбавка). */
const FACTORS: { key: keyof RiskBreakdown; label: string; hint: string }[] = [
  { key: 'severity_w', label: 'Тяжесть', hint: 'severity_w · вес 0.45' },
  { key: 'speed_ratio', label: 'Превышение', hint: 'speed_ratio · вес 0.25' },
  { key: 'night', label: 'Ночь', hint: 'is_night · вес 0.15' },
  { key: 'weather_bonus', label: 'Погода/сцена', hint: '§8.2 надбавка (0 без кэша)' },
  { key: 'freq_w', label: 'Частота', hint: 'events_last_7d · вес 0.15' },
]

/** Цвет вклада по знаку/величине доли в итоге (токены d1). */
function levelClasses(value: number, total: number): { bar: string; text: string } {
  if (value < 0) return { bar: 'bg-primary', text: 'text-primary' }
  const share = total > 0 ? value / total : 0
  if (share >= 0.35) return { bar: 'bg-critical', text: 'text-critical-text' }
  if (share >= 0.2) return { bar: 'bg-high', text: 'text-high-text' }
  if (share >= 0.1) return { bar: 'bg-warning', text: 'text-warning-text' }
  return { bar: 'bg-ok', text: 'text-ok-text' }
}

/**
 * RiskWaterfall — презентационное разложение (без загрузки), для тестов и переиспользования.
 * Горизонтальная стэк-полоса вкладов + список со знаком и накопительной суммой; итог = `risk_score`.
 */
export function RiskWaterfallView({ data }: { data: RiskBreakdown }) {
  const total = data.total_risk_score
  // Денонимантор стэк-полосы — сумма ширин (по модулю), чтобы нулевые/мелкие вклады не ломали раскладку.
  const widthBasis = FACTORS.reduce((s, f) => s + Math.abs(data[f.key] as number), 0) || 1

  let running = 0

  return (
    <div className="space-y-3">
      {/* Горизонтальная стэк-полоса: ширина сегмента ∝ модулю вклада. */}
      <div
        className="flex h-3 w-full overflow-hidden rounded-full bg-bg"
        role="img"
        aria-label={`Разложение риска: ${FACTORS.map((f) => `${f.label} ${data[f.key]}`).join(', ')}; итог ${total}`}
      >
        {FACTORS.map((f) => {
          const value = data[f.key] as number
          const pct = (Math.abs(value) / widthBasis) * 100
          if (pct <= 0) return null
          const { bar } = levelClasses(value, total)
          return (
            <div
              key={f.key}
              className={cn('h-full', bar)}
              style={{ width: `${pct}%` }}
              title={`${f.label}: ${value >= 0 ? '+' : ''}${value} (${f.hint})`}
            />
          )
        })}
      </div>

      {/* Список вкладов: подпись, вклад со знаком, накопительная сумма. */}
      <ul className="space-y-1">
        {FACTORS.map((f) => {
          const value = data[f.key] as number
          running += value
          const { bar, text } = levelClasses(value, total)
          return (
            <li key={f.key} className="flex items-center gap-2 text-sm">
              <span className={cn('h-2.5 w-2.5 shrink-0 rounded-sm', bar)} aria-hidden />
              <span className="min-w-0 flex-1 truncate text-ink" title={f.hint}>
                {f.label}
              </span>
              <span className={cn('shrink-0 tabular-nums font-medium', text)}>
                {value >= 0 ? '+' : '−'}
                {Math.abs(value)}
              </span>
              <span className="w-10 shrink-0 text-right tabular-nums text-muted">{running}</span>
            </li>
          )
        })}
        {/* Итог = risk_score инцидента (совпадает с API). */}
        <li className="flex items-center gap-2 border-t border-border pt-1.5 text-sm font-semibold">
          <Scale className="h-3.5 w-3.5 shrink-0 text-muted" aria-hidden />
          <span className="min-w-0 flex-1 text-ink">Итоговый риск</span>
          <span className="w-10 shrink-0 text-right tabular-nums text-ink">{total}</span>
        </li>
      </ul>
    </div>
  )
}

export function RiskWaterfall({
  id,
  title = 'Почему такой риск',
  defaultOpen = false,
  className,
}: RiskWaterfallProps) {
  const [open, setOpen] = useState(defaultOpen)
  const [state, setState] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle')
  const [data, setData] = useState<RiskBreakdown | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    setState('loading')
    setError(null)
    client
      .getRiskBreakdown(id)
      .then((d) => {
        setData(d)
        setState('ready')
      })
      .catch((e: unknown) => {
        setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Ошибка')
        setState('error')
      })
  }, [id])

  // Ленивая загрузка: тянем разложение при первом раскрытии (и сбрасываем при смене id).
  useEffect(() => {
    setData(null)
    setState('idle')
    setError(null)
  }, [id])

  useEffect(() => {
    if (open && state === 'idle') load()
  }, [open, state, load])

  const panelId = `risk-waterfall-${id}`

  return (
    <div className={cn('rounded-md border border-border bg-surface', className)}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={panelId}
        className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-medium text-ink transition-colors hover:bg-bg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        <Scale className="h-4 w-4 shrink-0 text-primary" aria-hidden />
        <span className="flex-1">{title}</span>
        <ChevronDown
          className={cn('h-4 w-4 shrink-0 text-muted transition-transform', open && 'rotate-180')}
          aria-hidden
        />
      </button>

      {open && (
        <div id={panelId} className="border-t border-border px-3 py-3">
          {state === 'loading' && (
            <div className="space-y-2" aria-hidden>
              <div className="h-3 w-full animate-pulse rounded-full bg-border" />
              <div className="h-3 w-2/3 animate-pulse rounded bg-border" />
              <div className="h-3 w-1/2 animate-pulse rounded bg-border" />
            </div>
          )}

          {state === 'error' && (
            <div className="flex flex-col items-center gap-2 py-4 text-center">
              <TriangleAlert className="h-6 w-6 text-high-text" aria-hidden />
              <p className="text-xs text-muted">{error ?? 'Не удалось загрузить разложение риска.'}</p>
              <button
                type="button"
                onClick={load}
                className="inline-flex items-center gap-1.5 rounded px-2 py-1 text-xs font-medium text-primary hover:bg-primary-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              >
                <RotateCcw className="h-3.5 w-3.5" aria-hidden />
                Повторить
              </button>
            </div>
          )}

          {state === 'ready' && data && <RiskWaterfallView data={data} />}
        </div>
      )}
    </div>
  )
}
