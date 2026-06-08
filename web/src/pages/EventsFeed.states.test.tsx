import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { INCIDENTS } from '@/api/fixtures'
import type { IncidentSummary } from '@/api/types'
import { RoleProvider } from '@/state/role'

/**
 * f5 · EventsFeed — состояния и паритет live↔fixtures (перенос из аудита барьеров):
 *  • loading → скелетон (не белый экран);
 *  • empty → дружелюбная плашка «Нет алярмов»;
 *  • error → плашка + «Повторить» (и ретрай повторно дёргает клиент);
 *  • паритет: те же фикстуры §3.1, что и в VITE_USE_FIXTURES, рендерятся; отсутствие
 *    необязательного поля (address/driver/координаты) не роняет рендер.
 */
vi.mock('@/api/client', () => ({
  listIncidents: vi.fn(),
}))

import * as client from '@/api/client'
import EventsFeed from './EventsFeed'

function renderFeed() {
  return render(
    <RoleProvider>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <EventsFeed />
      </MemoryRouter>
    </RoleProvider>,
  )
}

describe('f5 · EventsFeed — состояния', () => {
  beforeEach(() => localStorage.clear())
  afterEach(() => vi.mocked(client.listIncidents).mockReset())

  it('loading: скелетон вместо белого экрана', () => {
    vi.mocked(client.listIncidents).mockReturnValue(new Promise(() => {}))
    const { container } = renderFeed()
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
    expect(screen.queryByText('Нет алярмов')).toBeNull()
  })

  it('empty: дружелюбная плашка «Нет алярмов»', async () => {
    vi.mocked(client.listIncidents).mockResolvedValue([])
    renderFeed()
    expect(await screen.findByText('Нет алярмов')).toBeInTheDocument()
  })

  it('error: плашка + «Повторить» (ретрай повторно дёргает клиент)', async () => {
    vi.mocked(client.listIncidents).mockRejectedValue(new Error('сеть упала'))
    renderFeed()
    expect(await screen.findByText('Не удалось загрузить ленту')).toBeInTheDocument()
    const retry = screen.getByRole('button', { name: /Повторить/ })

    vi.mocked(client.listIncidents).mockResolvedValue(INCIDENTS)
    fireEvent.click(retry)
    await waitFor(() => expect(vi.mocked(client.listIncidents).mock.calls.length).toBeGreaterThan(1))
  })

  it('паритет: фикстуры §3.1 рендерятся как в режиме VITE_USE_FIXTURES', async () => {
    vi.mocked(client.listIncidents).mockResolvedValue(INCIDENTS)
    renderFeed()
    expect(
      await screen.findByRole('button', { name: /Засыпание за рулём \(микросон\), А777ВВ 77/ }),
    ).toBeInTheDocument()
    // ровно столько строк, сколько записей в фикстуре
    await waitFor(() =>
      expect(document.querySelectorAll('tbody tr[role="button"]').length).toBe(INCIDENTS.length),
    )
  })

  it('отсутствие необязательных полей (address/driver/координаты) не роняет рендер', async () => {
    const sparse: IncidentSummary = {
      ...INCIDENTS[0],
      id: 'sparse',
      driver: '',
      address: null,
      lat: null,
      lon: null,
    }
    vi.mocked(client.listIncidents).mockResolvedValue([sparse])
    renderFeed()
    expect(await screen.findByRole('button', { name: /А777ВВ 77/ })).toBeInTheDocument()
    // «—» fallback вместо пустого водителя/адреса
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(1)
  })
})
