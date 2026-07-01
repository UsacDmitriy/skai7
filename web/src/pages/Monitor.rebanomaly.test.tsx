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

beforeEach(() => {
  getZones.mockResolvedValue([])
  getRebAnomalies.mockReset()
  getRebAnomalies.mockResolvedValue([]) // пустой ответ — валиден
  listIncidents.mockResolvedValue([])
})

describe('Monitor · слой РЭБ-аномалий', () => {
  it('включение слоя с пустым ответом дёргает getRebAnomalies один раз (регресс: был цикл фетчей)', async () => {
    render(
      <MemoryRouter>
        <RoleProvider>
          <Monitor />
        </RoleProvider>
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByRole('searchbox')).toBeInTheDocument())
    expect(getRebAnomalies).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: /РЭБ-аномалии/ }))

    await waitFor(() => expect(getRebAnomalies).toHaveBeenCalled())
    // даём циклу шанс проявиться: несколько тиков стейт-обновлений
    await new Promise((r) => setTimeout(r, 50))
    expect(getRebAnomalies).toHaveBeenCalledTimes(1)
  })
})
