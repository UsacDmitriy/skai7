import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { INCIDENTS } from '@/api/fixtures'
import { RoleProvider } from '@/state/role'

/**
 * f6 · Monitor — состояния и паритет live↔fixtures:
 *  • loading → скелет ленты + индикатор «Загрузка слоя…» (карта не падает);
 *  • empty → плашка «Нет активных алярмов по фильтрам.»;
 *  • error → баннер + «Повторить» (карта остаётся);
 *  • паритет: фикстуры §3.1 дают по одному маркеру на ТС.
 * Карта/виджеты мокаются — наблюдаем состояние, а не Leaflet.
 */
vi.mock('@/components/map', () => ({
  MapView: ({ children }: { children?: React.ReactNode }) => <div data-testid="map">{children}</div>,
  MarkerLayer: ({ units }: { units: Array<{ unit_id: string }> }) => (
    <div data-testid="marker-layer" data-count={units.length} />
  ),
  RoleToggle: () => <div data-testid="role-toggle" />,
}))
vi.mock('@/components/SabotageWidget', () => ({
  SabotageWidget: () => <div data-testid="sabotage" />,
}))
vi.mock('@/api/client', () => ({
  listIncidents: vi.fn(),
  // f18: Monitor запрашивает риск-зоны при монтировании; пустой набор валиден.
  getZones: () => Promise.resolve([]),
}))

import * as client from '@/api/client'
import Monitor from './Monitor'

function renderMonitor() {
  return render(
    <RoleProvider>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Monitor />
      </MemoryRouter>
    </RoleProvider>,
  )
}

describe('f6 · Monitor — состояния', () => {
  beforeEach(() => localStorage.clear())
  afterEach(() => vi.mocked(client.listIncidents).mockReset())

  it('loading: скелет ленты + «Загрузка слоя…» (карта не падает)', () => {
    vi.mocked(client.listIncidents).mockReturnValue(new Promise(() => {}))
    const { container } = renderMonitor()
    expect(screen.getByText('Загрузка слоя…')).toBeInTheDocument()
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
    expect(screen.getByTestId('map')).toBeInTheDocument()
  })

  it('empty: дружелюбная плашка без активных алярмов', async () => {
    vi.mocked(client.listIncidents).mockResolvedValue([])
    renderMonitor()
    expect(await screen.findByText('Нет активных алярмов по фильтрам.')).toBeInTheDocument()
  })

  it('error: баннер + «Повторить», карта остаётся смонтированной', async () => {
    vi.mocked(client.listIncidents).mockRejectedValue(new Error('сеть упала'))
    renderMonitor()
    expect(await screen.findByText('сеть упала')).toBeInTheDocument()
    const retry = screen.getByRole('button', { name: /Повторить/ })
    expect(screen.getByTestId('map')).toBeInTheDocument()

    vi.mocked(client.listIncidents).mockResolvedValue(INCIDENTS)
    fireEvent.click(retry)
    await waitFor(() => expect(vi.mocked(client.listIncidents).mock.calls.length).toBeGreaterThan(1))
  })

  it('паритет: фикстуры §3.1 → 1 маркер на ТС', async () => {
    vi.mocked(client.listIncidents).mockResolvedValue(INCIDENTS)
    renderMonitor()
    const layer = await screen.findByTestId('marker-layer')
    const uniquePlates = new Set(INCIDENTS.map((i) => i.vehicle_plate)).size
    expect(layer).toHaveAttribute('data-count', String(uniquePlates))
  })
})
