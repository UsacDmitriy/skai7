import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DiscrepancyBadge } from './DiscrepancyBadge'
import type { WeatherCrossCheck } from '../../api/types'

/**
 * f16 · DiscrepancyBadge — бейдж «камера ↔ погода» (§8.4).
 *  • показывается ТОЛЬКО при `discrepancy=true` (иначе null);
 *  • тип расхождения проговаривается словами в title/aria-label (a11y);
 *  • `discrepancy_kind='none'` при флаге true → общий текст-фолбэк.
 */

const weather = (over: Partial<WeatherCrossCheck> = {}): WeatherCrossCheck => ({
  id: 'inc-001',
  api_weather: 'clear',
  is_day: true,
  solar_elevation_deg: 12,
  discrepancy: false,
  discrepancy_kind: 'none',
  ...over,
})

describe('f16 · DiscrepancyBadge', () => {
  it('discrepancy=false → ничего не рендерит', () => {
    const { container } = render(<DiscrepancyBadge weather={weather({ discrepancy: false })} />)
    expect(container).toBeEmptyDOMElement()
    expect(screen.queryByText('Камера ↔ погода')).not.toBeInTheDocument()
  })

  it('discrepancy=true, kind=weather → бейдж с расшифровкой «тип осадков»', () => {
    render(<DiscrepancyBadge weather={weather({ discrepancy: true, discrepancy_kind: 'weather' })} />)
    expect(screen.getByText('Камера ↔ погода')).toBeInTheDocument()
    expect(screen.getByLabelText(/тип осадков/)).toBeInTheDocument()
  })

  it('discrepancy=true, kind=daynight → расшифровка «день/ночь»', () => {
    render(<DiscrepancyBadge weather={weather({ discrepancy: true, discrepancy_kind: 'daynight' })} />)
    expect(screen.getByLabelText(/день\/ночь/)).toBeInTheDocument()
  })

  it('discrepancy=true, kind=none → общий текст-фолбэк', () => {
    render(<DiscrepancyBadge weather={weather({ discrepancy: true, discrepancy_kind: 'none' })} />)
    const badge = screen.getByText('Камера ↔ погода')
    expect(badge).toHaveAttribute('title', 'Данные камеры не совпадают с внешней погодой')
  })
})
