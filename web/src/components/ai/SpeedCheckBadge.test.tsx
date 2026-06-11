import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SpeedCheckBadge, speedCheckText } from './SpeedCheckBadge'
import type { SpeedCheck } from '../../api/types'

/**
 * f25 · SpeedCheckBadge — сверка скоростей событие ↔ GPS-трек (§10.2).
 *  • ok (32/28.4) → «совпадает», нейтрально/успех;
 *  • major (90/61) → «расходится (±delta)», danger;
 *  • no_data → «нет данных GPS-трека», muted, без чисел.
 * Чистый презентационный компонент — props конструируем в тесте, без сети.
 */

const speed = (over: Partial<SpeedCheck> = {}): SpeedCheck => ({
  id: 'inc-001',
  event_speed_kmh: 32,
  track_speed_kmh: 28.4,
  max_track_speed_kmh: 34.1,
  delta_kmh: 3.6,
  agreement: 'ok',
  truth_source: 'gps_track',
  ...over,
})

/** Бейдж несёт title об источнике истины — опорный элемент. */
function badge() {
  return screen.getByTitle(/Источник истины/)
}

describe('f25 · SpeedCheckBadge', () => {
  it('ok (32/28.4): «совпадает», нейтральный/успешный токен', () => {
    render(<SpeedCheckBadge speed={speed()} />)
    expect(screen.getByText(/совпадает/)).toBeInTheDocument()
    expect(screen.getByText(/событие 32/)).toBeInTheDocument()
    expect(screen.getByText(/GPS 28,4/)).toBeInTheDocument()
    expect(badge()).toHaveClass('border-ok')
  })

  it('major (90/61): «расходится (±delta)», danger-токен', () => {
    render(
      <SpeedCheckBadge
        speed={speed({ event_speed_kmh: 90, track_speed_kmh: 61, delta_kmh: 29, agreement: 'major' })}
      />,
    )
    expect(screen.getByText(/расходится \(±29\)/)).toBeInTheDocument()
    expect(badge()).toHaveClass('border-critical')
    expect(badge()).not.toHaveClass('border-ok')
  })

  it('no_data: «нет данных GPS-трека», muted, без чисел', () => {
    render(
      <SpeedCheckBadge
        speed={speed({
          event_speed_kmh: null,
          track_speed_kmh: null,
          max_track_speed_kmh: null,
          delta_kmh: null,
          agreement: 'no_data',
        })}
      />,
    )
    expect(screen.getByText('Скорость: нет данных GPS-трека')).toBeInTheDocument()
    expect(screen.queryByText(/событие/)).not.toBeInTheDocument()
    expect(badge()).toHaveClass('border-border')
  })

  it('текст использует GPS-трек, НЕ CAN (ASSUMPTION §10.2)', () => {
    const txt = speedCheckText(speed({ agreement: 'minor', delta_kmh: 8, event_speed_kmh: 40, track_speed_kmh: 32 }))
    expect(txt).toContain('GPS')
    expect(txt).not.toContain('CAN')
    expect(txt).toContain('±8')
  })
})
