import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { RoleProvider } from '@/state/role'

vi.mock('@/components/map', () => ({
  MapView: ({ children }: { children?: React.ReactNode }) => <div data-testid="map">{children}</div>,
  MarkerLayer: () => <div data-testid="marker-layer" />,
  RoleToggle: () => <div data-testid="role-toggle" />,
}))
vi.mock('@/components/SabotageWidget', () => ({
  SabotageWidget: () => <div data-testid="sabotage" />,
}))
vi.mock('@/components/ai/RiskHeatLayer', () => ({
  RiskHeatLayer: () => <div data-testid="heat-layer" />,
}))
vi.mock('@/components/reb/RebAnomalyLayer', () => ({
  RebAnomalyLayer: () => <div data-testid="reb-layer" />,
}))

const listIncidents = vi.fn()
const getZones = vi.fn()
const getRebAnomalies = vi.fn()
vi.mock('@/api/client', () => ({
  listIncidents: () => listIncidents(),
  getZones: () => getZones(),
  getRebAnomalies: () => getRebAnomalies(),
}))

import Monitor from './Monitor'

const inc = (over: Partial<Record<string, unknown>>) => ({
  id: '1', alarm_type: 'Smoking', alarm_code: 'DMS_SMOKING', alarm_label_ru: 'Курение',
  source: 'DMS', severity: 'medium', risk_level: 'medium', risk_score: 58, ts: '2026-05-19 02:59:00+04',
  vehicle_plate: 'С643УР799', driver: 'Волков Андрей', vehicle_model: 'Volvo FH', speed_kmh: 0,
  lat: 55.7, lon: 37.6, address: null, video_available: true, status: 'new', ...over,
})

beforeEach(() => {
  getZones.mockResolvedValue([])
  getRebAnomalies.mockResolvedValue([])
  listIncidents.mockResolvedValue([
    inc({}),
    inc({ id: '2', driver: 'Гусев Вячеслав', vehicle_plate: 'М477УМ790' }),
  ])
})

describe('Monitor · умный поиск', () => {
  it('ввод «гусев» сужает список алярмов', async () => {
    render(
      <MemoryRouter>
        <RoleProvider>
          <Monitor />
        </RoleProvider>
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByRole('searchbox')).toBeInTheDocument())
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'гусев' } })
    await waitFor(() => {
      expect(screen.getByText(/Гусев/)).toBeInTheDocument()
      expect(screen.queryByText(/Волков/)).toBeNull()
    })
  })
})
