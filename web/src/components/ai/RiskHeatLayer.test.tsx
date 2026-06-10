import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import type { RiskZone } from '../../api/types'

/**
 * d7 · RiskHeatLayer — тепловой слой риск-зон (L.layerGroup + L.circle, §8.4).
 *  • рисует circle на каждую ВИДИМУЮ зону (фильтр по `kind`);
 *  • тоггл `kind` перерисовывает слой (clearLayers + новые круги);
 *  • зоны с невалидным центроидом (NaN) отсеиваются;
 *  • цвет/радиус берутся из avg_risk/radius_m.
 *
 * Leaflet и react-leaflet мокаются (карта в jsdom не нужна): фиксируем вызовы L.circle.
 */

const circleHandle = { bindTooltip: vi.fn(), addTo: vi.fn() }
circleHandle.bindTooltip.mockReturnValue(circleHandle)
circleHandle.addTo.mockReturnValue(circleHandle)

const circle = vi.fn(() => circleHandle)
const layerGroupHandle = {
  addTo: vi.fn(),
  clearLayers: vi.fn(),
  remove: vi.fn(),
}
layerGroupHandle.addTo.mockReturnValue(layerGroupHandle)

vi.mock('leaflet', () => ({
  circle: (...args: unknown[]) => circle(...args),
  layerGroup: () => layerGroupHandle,
}))

vi.mock('react-leaflet', () => ({
  useMap: () => ({ id: 'fake-map' }),
}))

import { RiskHeatLayer } from './RiskHeatLayer'

const ZONES: RiskZone[] = [
  {
    zone_id: 'inc-1',
    centroid: [55.75, 37.61],
    radius_m: 800,
    alarm_count: 4,
    avg_risk: 78, // ≥70 → critical-токен
    top_alarm_code: 'DMS_DROWSY',
    peak_hour: 1,
    kind: 'incident',
  },
  {
    zone_id: 'reb-1',
    centroid: [55.5, 37.9],
    radius_m: 1200,
    alarm_count: 2,
    avg_risk: 0,
    top_alarm_code: 'REB_GAP',
    peak_hour: 14,
    kind: 'reb',
  },
  {
    zone_id: 'bad',
    centroid: [Number.NaN, Number.NaN], // невалидные координаты → отсев
    radius_m: 300,
    alarm_count: 1,
    avg_risk: 50,
    top_alarm_code: 'X',
    peak_hour: 3,
    kind: 'incident',
  },
]

describe('d7 · RiskHeatLayer', () => {
  beforeEach(() => {
    circle.mockClear()
    layerGroupHandle.clearLayers.mockClear()
  })

  it('kind=incident → круг только на валидную incident-зону (NaN отсеян)', () => {
    render(<RiskHeatLayer zones={ZONES} kind="incident" />)
    // 2 incident-зоны, но одна с NaN → 1 круг.
    expect(circle).toHaveBeenCalledTimes(1)
    const [center, opts] = circle.mock.calls[0] as [number[], Record<string, unknown>]
    expect(center).toEqual([55.75, 37.61])
    expect(opts.radius).toBe(800)
    expect(opts.fillColor).toBe('var(--sev-critical)') // avg_risk 78 ≥ 70
    expect(opts.interactive).toBe(false)
  })

  it('kind=reb → круг на reb-зону с её радиусом', () => {
    render(<RiskHeatLayer zones={ZONES} kind="reb" />)
    expect(circle).toHaveBeenCalledTimes(1)
    const [center, opts] = circle.mock.calls[0] as [number[], Record<string, unknown>]
    expect(center).toEqual([55.5, 37.9])
    expect(opts.radius).toBe(1200)
  })

  it('тоггл kind перерисовывает слой (clearLayers + новый набор кругов)', () => {
    const { rerender } = render(<RiskHeatLayer zones={ZONES} kind="incident" />)
    expect(circle).toHaveBeenCalledTimes(1)

    circle.mockClear()
    rerender(<RiskHeatLayer zones={ZONES} kind="reb" />)
    // Слой очищается перед перерисовкой и рисует уже reb-зону.
    expect(layerGroupHandle.clearLayers).toHaveBeenCalled()
    expect(circle).toHaveBeenCalledTimes(1)
    const [center] = circle.mock.calls[0] as [number[], Record<string, unknown>]
    expect(center).toEqual([55.5, 37.9])
  })

  it('пустой набор зон → ни одного круга', () => {
    render(<RiskHeatLayer zones={[]} kind="incident" />)
    expect(circle).not.toHaveBeenCalled()
  })
})
