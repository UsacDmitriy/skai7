import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { TICKETS } from '@/api/fixtures'
import type { Ticket } from '@/api/types'

/**
 * f8 · Tickets — состояния и паритет/устойчивость:
 *  • loading → скелет; empty → «Заявок пока нет»; error → «Повторить» (ретрай);
 *  • устойчивость: deadline=null и неизвестный код действия не роняют рендер.
 */
vi.mock('@/api/client', () => ({ getTickets: vi.fn() }))

import * as client from '@/api/client'
import Tickets from './Tickets'

function renderTickets() {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Tickets />
    </MemoryRouter>,
  )
}

describe('f8 · Tickets — состояния', () => {
  afterEach(() => vi.mocked(client.getTickets).mockReset())

  it('loading: скелет вместо белого экрана', () => {
    vi.mocked(client.getTickets).mockReturnValue(new Promise(() => {}))
    const { container } = renderTickets()
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('empty: «Заявок пока нет»', async () => {
    vi.mocked(client.getTickets).mockResolvedValue([])
    renderTickets()
    expect(await screen.findByText('Заявок пока нет')).toBeInTheDocument()
  })

  it('error: плашка + «Повторить» (ретрай повторно дёргает клиент)', async () => {
    vi.mocked(client.getTickets).mockRejectedValue(new Error('заявки недоступны'))
    renderTickets()
    expect(await screen.findByText('заявки недоступны')).toBeInTheDocument()
    const retry = screen.getByRole('button', { name: /Повторить/ })

    vi.mocked(client.getTickets).mockResolvedValue(TICKETS)
    fireEvent.click(retry)
    await waitFor(() => expect(vi.mocked(client.getTickets).mock.calls.length).toBeGreaterThan(1))
  })

  it('устойчивость: deadline=null и неизвестный код действия рендерятся без падения', async () => {
    const odd: Ticket = {
      id: 'tkt-odd',
      created_at: '2026-04-02T08:00:00',
      incident_id: 'inc-001',
      action: 'unknown_action_code',
      comment: 'нестандартное действие',
      status: 'active',
      deadline: null,
      is_overdue: false,
    }
    vi.mocked(client.getTickets).mockResolvedValue([odd])
    renderTickets()
    // raw-код как fallback человекочитаемого ярлыка (в ячейке и в <option> фильтра)
    expect((await screen.findAllByText('unknown_action_code')).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(1) // «—» для пустого дедлайна
  })
})
