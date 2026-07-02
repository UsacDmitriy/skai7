import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { INCIDENT_DETAILS } from '@/api/fixtures'
import { ROLE_STORAGE_KEY, RoleProvider } from '@/state/role'

/**
 * f13/идея #10 · IncidentCard читает роль из глобального RoleProvider (не локально).
 * Деструктивное stop_vehicle («Стоп ТС») доступно только Диспетчеру (role==='dispatcher').
 */
vi.mock('@/components', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/components')>()
  return {
    ...actual,
    VideoPlayer: () => <div data-testid="vp" />,
    TelemetryChart: () => <div data-testid="tc" />,
  }
})
vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return {
    ...actual,
    getIncident: vi.fn(),
    getTickets: vi.fn(),
    getScene: vi.fn(),
    getSpeedCheck: vi.fn(),
  }
})

import * as client from '@/api/client'
import IncidentCard from './IncidentCard'

const inc = INCIDENT_DETAILS['inc-001']

function renderAs(role: string) {
  localStorage.setItem(ROLE_STORAGE_KEY, role)
  return render(
    <MemoryRouter
      initialEntries={[`/incidents/${inc.id}`]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <RoleProvider>
        <Routes>
          <Route path="/incidents/:id" element={<IncidentCard />} />
        </Routes>
      </RoleProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.mocked(client.getIncident).mockResolvedValue(inc)
  vi.mocked(client.getTickets).mockResolvedValue([])
  vi.mocked(client.getScene).mockRejectedValue(new Error('no scene'))
  vi.mocked(client.getSpeedCheck).mockRejectedValue(new Error('no speed-check'))
})

describe('IncidentCard · ролевой гейтинг stop_vehicle (f13)', () => {
  it('security — «Стоп ТС» заблокирован (не Диспетчер)', async () => {
    renderAs('security')
    const btn = await screen.findByRole('button', { name: /Стоп ТС/ })
    expect(btn).toBeDisabled()
  })

  it('dispatcher — «Стоп ТС» доступен', async () => {
    renderAs('dispatcher')
    const btn = await screen.findByRole('button', { name: /Стоп ТС/ })
    expect(btn).not.toBeDisabled()
  })

  it('logist — «Стоп ТС» заблокирован', async () => {
    renderAs('logist')
    const btn = await screen.findByRole('button', { name: /Стоп ТС/ })
    expect(btn).toBeDisabled()
  })
})
