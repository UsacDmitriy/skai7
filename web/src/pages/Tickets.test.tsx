import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { TICKETS } from '@/api/fixtures'

/**
 * f8 · Tickets (`/tickets`) — реестр заявок:
 *  • оверлей «⏱ Просрочено» рисуется по производному `is_overdue`, НЕ по `status` (W3-1):
 *    две активные заявки, просрочена только помеченная `is_overdue=true`;
 *  • enum `Status` (§3.1) отображается человекочитаемо;
 *  • клиентский фильтр по статусу сужает таблицу.
 */
vi.mock('@/api/client', () => ({ getTickets: vi.fn() }))

import * as client from '@/api/client'
import Tickets from './Tickets'

function rowOf(text: string): HTMLElement {
  return screen.getByText(text).closest('tr') as HTMLElement
}

// Бейджи статуса в таблице, в отличие от одноимённых <option> фильтра.
function table(): HTMLElement {
  return screen.getByRole('table')
}

function renderTickets() {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Tickets />
    </MemoryRouter>,
  )
}

describe('f8 · Tickets', () => {
  beforeEach(() => vi.mocked(client.getTickets).mockResolvedValue(TICKETS))
  afterEach(() => vi.mocked(client.getTickets).mockReset())

  it('«Просрочено» — оверлей по is_overdue, отдельный от статуса', async () => {
    renderTickets()
    await screen.findByText('Назначить разбор засыпания с водителем')

    // tkt-001 и tkt-005 — обе status=active, но просрочена ТОЛЬКО is_overdue=true (tkt-005).
    const activeNotOverdue = rowOf('Назначить разбор засыпания с водителем') // tkt-001
    const activeOverdue = rowOf('Связаться с водителем по факту резкого торможения') // tkt-005
    expect(within(activeNotOverdue).queryByText('Просрочено')).toBeNull()
    expect(within(activeOverdue).getByText('Просрочено')).toBeInTheDocument()

    // Всего просроченных = число is_overdue в фикстуре (tkt-002 + tkt-005).
    const overdueCount = TICKETS.filter((t) => t.is_overdue).length
    expect(screen.getAllByText('Просрочено')).toHaveLength(overdueCount)
  })

  it('enum Status (§3.1) отображается человекочитаемо', async () => {
    renderTickets()
    await screen.findByText('Назначить разбор засыпания с водителем')
    const t = within(table())
    expect(t.getAllByText('Активна').length).toBeGreaterThanOrEqual(1)
    expect(t.getAllByText('В работе').length).toBeGreaterThanOrEqual(1)
    expect(t.getByText('Подтверждена')).toBeInTheDocument()
    expect(t.getByText('Закрыта')).toBeInTheDocument()
  })

  it('фильтр по статусу «Закрыта» оставляет только закрытые заявки', async () => {
    renderTickets()
    await screen.findByText('Назначить разбор засыпания с водителем')

    fireEvent.change(screen.getByLabelText('Статус'), { target: { value: 'closed' } })
    // Закрытая заявка одна (tkt-003); активные/в работе исчезают из таблицы.
    const t = within(table())
    expect(t.getByText('Закрыта')).toBeInTheDocument()
    expect(t.queryByText('Активна')).toBeNull()
    expect(t.queryByText('Просрочено')).toBeNull() // закрытая не просрочена
  })
})
