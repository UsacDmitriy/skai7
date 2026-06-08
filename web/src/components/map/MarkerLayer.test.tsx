import { describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import type { MapUnit } from './types'

/**
 * d4 · MarkerLayer (map-primitives) — расширяет t3:
 *  • цвет pin'а маппится по severity (medium→warning, low→ok, неизвестный→muted);
 *  • ДЕДУП §7.6: «1 unit_id = 1 маркер» (НЕ на AlarmId) — при дублях остаётся наихудший severity;
 *  • точки с невалидными координатами (NaN) отсеиваются;
 *  • попап несёт госномер + последний алярм + ссылку на инцидент.
 *
 * Leaflet-кластер и Marker/Popup мокаются (кластер в jsdom рендерит маркеры асинхронно);
 * сам `L.divIcon` — настоящий, поэтому из `icon.options.html` читаем цвет pin'а.
 */
vi.mock('react-leaflet-cluster', () => ({
  default: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="cluster">{children}</div>
  ),
}))

vi.mock('react-leaflet', () => ({
  Marker: ({
    icon,
    title,
    children,
  }: {
    icon?: { options?: { html?: string } }
    title?: string
    children?: React.ReactNode
  }) => (
    <div data-testid="marker" data-pin={icon?.options?.html ?? ''} data-title={title}>
      {children}
    </div>
  ),
  Popup: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="popup">{children}</div>
  ),
}))

import { MarkerLayer } from './MarkerLayer'

const unit = (over: Partial<MapUnit>): MapUnit => ({
  unit_id: 'u1',
  vehicle_plate: 'А777ВВ 77',
  lat: 55.75,
  lon: 37.61,
  severity: 'high',
  online: true,
  last_alarm: null,
  ...over,
})

function pins(): string[] {
  return screen.getAllByTestId('marker').map((m) => m.getAttribute('data-pin') ?? '')
}

describe('MarkerLayer · d4 map-primitives', () => {
  it('цвет pin по severity (critical/high/medium→warning/low→ok)', () => {
    render(
      <MarkerLayer
        units={[
          unit({ unit_id: 'c', severity: 'critical' }),
          unit({ unit_id: 'h', severity: 'high' }),
          unit({ unit_id: 'm', severity: 'medium' }),
          unit({ unit_id: 'l', severity: 'low' }),
        ]}
      />,
    )
    const all = pins().join('|')
    expect(all).toContain('--sev-critical')
    expect(all).toContain('--sev-high')
    expect(all).toContain('--sev-warning') // medium → warning-токен
    expect(all).toContain('--sev-ok') // low → ok-токен
  })

  it('неизвестный severity → нейтральный фолбэк (muted)', () => {
    render(<MarkerLayer units={[unit({ severity: 'bogus' as unknown as MapUnit['severity'] })]} />)
    expect(pins()[0]).toContain('--color-muted')
  })

  it('дедуп «1 unit_id = 1 маркер»: дубли схлопываются, остаётся наихудший severity', () => {
    render(
      <MarkerLayer
        units={[
          unit({ unit_id: 'А777ВВ 77', severity: 'low' }),
          unit({ unit_id: 'А777ВВ 77', severity: 'critical' }),
          unit({ unit_id: 'А777ВВ 77', severity: 'medium' }),
        ]}
      />,
    )
    const markers = screen.getAllByTestId('marker')
    expect(markers).toHaveLength(1) // 3 алярма на одно ТС → 1 маркер
    expect(markers[0].getAttribute('data-pin')).toContain('--sev-critical') // наихудший выжил
  })

  it('точки без валидных координат (NaN) отсеиваются', () => {
    render(
      <MarkerLayer
        units={[
          unit({ unit_id: 'ok', lat: 55.75, lon: 37.61 }),
          unit({ unit_id: 'nan', lat: Number.NaN, lon: 37.61 }),
        ]}
      />,
    )
    expect(screen.getAllByTestId('marker')).toHaveLength(1)
  })

  it('попап несёт госномер, последний алярм и ссылку на инцидент', () => {
    render(
      <MarkerLayer
        units={[
          unit({
            unit_id: 'А777ВВ 77',
            last_alarm: {
              id: 'inc-001',
              alarm_label_ru: 'Засыпание за рулём',
              severity: 'critical',
              ts: '2026-04-02T00:36:43',
            },
          }),
        ]}
      />,
    )
    const popup = screen.getByTestId('popup')
    expect(within(popup).getByText('А777ВВ 77')).toBeInTheDocument()
    expect(within(popup).getByText(/Засыпание за рулём/)).toBeInTheDocument()
    expect(within(popup).getByRole('link', { name: /Открыть инцидент/ })).toHaveAttribute(
      'href',
      '/incidents/inc-001',
    )
  })

  it('без алярма попап показывает «Без активных алярмов»', () => {
    render(<MarkerLayer units={[unit({ last_alarm: null })]} />)
    expect(screen.getByText('Без активных алярмов')).toBeInTheDocument()
  })
})
