import type { ReactElement } from 'react'
import { cloneElement } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TelemetryChart, type TelemetryPoint } from './TelemetryChart'

// recharts ResponsiveContainer измеряет размер через ResizeObserver, которого в
// jsdom нет (→ width/height 0 и шумный warning). Подменяем его на фикс-размер,
// чтобы график реально отрисовался и тест проверял рендер, а не заглушку 0×0.
vi.mock('recharts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('recharts')>()
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactElement }) =>
      cloneElement(children, { width: 600, height: 240 }),
  }
})

/**
 * d2 · TelemetryChart — принимает `data: TelemetryPoint[]` и `playheadOffset`
 * (CONTRACT §3.1), рендерится без ошибок. Пустые данные → текстовая заглушка.
 */
const DATA: TelemetryPoint[] = [
  { ts_offset: -60, speed: 75, ax: 0.1, ay: -0.2 },
  { ts_offset: -30, speed: 72, ax: 0.0, ay: 0.1 },
  { ts_offset: 0, speed: 72, ax: -0.3, ay: 0.5 },
  { ts_offset: 30, speed: 73, ax: 0.2, ay: -0.1 },
]

describe('TelemetryChart', () => {
  it('рендерит график с данными и playheadOffset без ошибок', () => {
    const { container } = render(<TelemetryChart data={DATA} playheadOffset={5} />)
    // Доступная обёртка графика (role=img + aria-label со сводкой) присутствует.
    const chart = screen.getByRole('img')
    expect(chart).toBeInTheDocument()
    expect(chart.getAttribute('aria-label')).toMatch(/Телеметрия/)
    // SVG реально отрисован (две линии: скорость + акселерометр).
    expect(container.querySelector('svg')).toBeInTheDocument()
  })

  it('принимает данные без playheadOffset (маркер playhead не обязателен)', () => {
    render(<TelemetryChart data={DATA} />)
    expect(screen.getByRole('img')).toBeInTheDocument()
  })

  it('пустые данные → заглушка «Нет телеметрии»', () => {
    render(<TelemetryChart data={[]} />)
    expect(screen.getByText('Нет телеметрии')).toBeInTheDocument()
    expect(screen.getByRole('img')).toHaveAttribute('aria-label', 'Телеметрия недоступна')
  })
})
