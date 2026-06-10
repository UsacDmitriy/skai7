import type { ReactElement } from 'react'
import { cloneElement } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ForecastSparkline } from './ForecastSparkline'
import type { RiskForecastPoint } from '../../api/types'

/**
 * f18 · ForecastSparkline — коридор `ci_low/ci_high` + линия прогноза, точка аномалии (§8.4).
 *  • пустой trend → текстовая заглушка «Нет данных» (без svg);
 *  • непустой trend → реальный svg-график (recharts);
 *  • anomaly=true → подсветка пиковой точки (ReferenceDot = доп. circle на svg).
 *
 * recharts ResponsiveContainer меряет размер через ResizeObserver (в jsdom 0×0) —
 * подменяем на фикс-размер, чтобы график отрисовался, а не схлопнулся (паттерн d2).
 */
vi.mock('recharts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('recharts')>()
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactElement }) =>
      cloneElement(children, { width: 400, height: 56 }),
  }
})

const TREND: RiskForecastPoint[] = [
  { date: '2026-04-03', predicted_events: 1, ci_low: 0, ci_high: 3 },
  { date: '2026-04-04', predicted_events: 5, ci_low: 2, ci_high: 7 }, // пик → аномалия
  { date: '2026-04-05', predicted_events: 1, ci_low: 0, ci_high: 3 },
]

describe('f18 · ForecastSparkline', () => {
  it('пустой trend → заглушка «Нет данных», без графика', () => {
    const { container } = render(<ForecastSparkline trend={[]} />)
    expect(screen.getByText('Нет данных')).toBeInTheDocument()
    expect(container.querySelector('svg')).not.toBeInTheDocument()
  })

  it('непустой trend → отрисован svg-график (коридор + линия)', () => {
    const { container } = render(<ForecastSparkline trend={TREND} />)
    expect(screen.queryByText('Нет данных')).not.toBeInTheDocument()
    expect(container.querySelector('svg')).toBeInTheDocument()
    // Коридор ci_low/ci_high рисуется как Area → path-заливки на svg.
    expect(container.querySelectorAll('path.recharts-area-area').length).toBeGreaterThan(0)
  })

  it('anomaly=true → подсвечена пиковая точка (доп. circle), без аномалии — нет', () => {
    const { container: withDot } = render(<ForecastSparkline trend={TREND} anomaly />)
    const { container: noDot } = render(<ForecastSparkline trend={TREND} anomaly={false} />)
    // ReferenceDot рисует <circle> поверх графика; без аномалии точек нет (dot=false на линии).
    expect(withDot.querySelectorAll('circle').length).toBeGreaterThan(0)
    expect(noDot.querySelectorAll('circle').length).toBe(0)
  })
})
