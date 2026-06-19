import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import type { RebAnomalyZone } from '@/api/types'

/**
 * RebAnomalyLayer — слой РЭБ-аномалий поверх MapView.
 *  • рисует circle на каждую зону (цвет по confidence_label);
 *  • маркер на каждое ТС в зоне (иконка RadioTower SVG);
 *  • dashed polyline для possible_route (если длина ≥ 2);
 *  • popup по клику на маркер: госномер, тип, скорость, confidence, время.
 *
 * Leaflet и react-leaflet мокаются: фиксируем вызовы L.circle, L.marker, L.polyline.
 */

const popupHandle = { on: vi.fn() }
const markerHandle = { bindPopup: vi.fn(), addTo: vi.fn() }
markerHandle.bindPopup.mockReturnValue(markerHandle)
markerHandle.addTo.mockReturnValue(markerHandle)

const polylineHandle = { addTo: vi.fn() }
polylineHandle.addTo.mockReturnValue(polylineHandle)

const circleHandle = { bindTooltip: vi.fn(), addTo: vi.fn() }
circleHandle.bindTooltip.mockReturnValue(circleHandle)
circleHandle.addTo.mockReturnValue(circleHandle)

const layerGroupHandle = {
  addTo: vi.fn(),
  clearLayers: vi.fn(),
  remove: vi.fn(),
}
layerGroupHandle.addTo.mockReturnValue(layerGroupHandle)

const circle = vi.fn((..._args: unknown[]) => circleHandle)
const marker = vi.fn((..._args: unknown[]) => markerHandle)
const polyline = vi.fn((..._args: unknown[]) => polylineHandle)
const layerGroup = vi.fn(() => layerGroupHandle)
const divIcon = vi.fn(() => ({}))

vi.mock('leaflet', () => ({
  default: {
    circle: (...args: unknown[]) => circle(...args),
    marker: (...args: unknown[]) => marker(...args),
    polyline: (...args: unknown[]) => polyline(...args),
    layerGroup: () => layerGroup(),
    divIcon: (...args: unknown[]) => divIcon(...args),
  },
  circle: (...args: unknown[]) => circle(...args),
  marker: (...args: unknown[]) => marker(...args),
  polyline: (...args: unknown[]) => polyline(...args),
  layerGroup: () => layerGroup(),
  divIcon: (...args: unknown[]) => divIcon(...args),
}))

vi.mock('react-leaflet', () => ({
  useMap: () => ({ on: vi.fn(), off: vi.fn() }),
}))

import { RebAnomalyLayer } from './RebAnomalyLayer'

// ── Фикстуры ──────────────────────────────────────────────────────────────
const ZONE_REB: RebAnomalyZone = {
  zone_id: 'reb_anomaly_0',
  centroid: [50.0, 35.0],
  radius_m: 5000,
  confidence: 75,
  confidence_label: 'reb',
  vehicles: [
    {
      vehicle_plate: 'А001АА777',
      anomaly_type: 'gap',
      max_speed_kmh: null,
      lat: 50.01,
      lon: 35.01,
      ts_start: '2026-05-07T10:00:00+00:00',
      ts_end: '2026-05-07T10:15:00+00:00',
      possible_route: [[50.0, 35.0], [50.01, 35.01]],
      reb_link_id: 'А001АА777',
    },
    {
      vehicle_plate: 'Б002ББ777',
      anomaly_type: 'speed_spike',
      max_speed_kmh: 247,
      lat: 50.02,
      lon: 35.02,
      ts_start: '2026-05-07T10:05:00+00:00',
      ts_end: null,
      possible_route: [],
      reb_link_id: 'Б002ББ777',
    },
  ],
  event_count: 5,
  date_count: 2,
}

const ZONE_SUSPICIOUS: RebAnomalyZone = {
  ...ZONE_REB,
  zone_id: 'reb_anomaly_1',
  confidence: 30,
  confidence_label: 'suspicious',
}

describe('RebAnomalyLayer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    circle.mockReturnValue(circleHandle)
    marker.mockReturnValue(markerHandle)
    polyline.mockReturnValue(polylineHandle)
    layerGroup.mockReturnValue(layerGroupHandle)
  })

  it('пустой список зон — рендерится без ошибок, clearLayers не вызывается с маркерами', () => {
    render(<RebAnomalyLayer zones={[]} />)
    expect(circle).not.toHaveBeenCalled()
    expect(marker).not.toHaveBeenCalled()
  })

  it('РЭБ-зона рисует circle + 2 marker + 1 polyline (у gap-ТС)', () => {
    render(<RebAnomalyLayer zones={[ZONE_REB]} />)
    expect(circle).toHaveBeenCalledTimes(1)
    expect(marker).toHaveBeenCalledTimes(2)
    // Только первое ТС имеет possible_route длиной 2 → 1 polyline.
    expect(polyline).toHaveBeenCalledTimes(1)
  })

  it('подозрительная зона тоже рисует circle', () => {
    render(<RebAnomalyLayer zones={[ZONE_SUSPICIOUS]} />)
    expect(circle).toHaveBeenCalledTimes(1)
  })

  it('marker.bindPopup вызывается для каждого ТС', () => {
    render(<RebAnomalyLayer zones={[ZONE_REB]} />)
    expect(markerHandle.bindPopup).toHaveBeenCalledTimes(2)
  })

  it('ТС без possible_route (пустой массив) не рисует polyline', () => {
    const zoneNoRoute: RebAnomalyZone = {
      ...ZONE_REB,
      vehicles: [{ ...ZONE_REB.vehicles[1], possible_route: [] }],
    }
    render(<RebAnomalyLayer zones={[zoneNoRoute]} />)
    expect(polyline).not.toHaveBeenCalled()
  })
})
