import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { INCIDENT_DETAILS } from '@/api/fixtures'

/**
 * f9 · DispatchAlert — состояния оверлея:
 *  • loading → скелет «Загрузка алерта» (не белый экран);
 *  • empty/404 → «Алерт не найден» (дружелюбно, не пусто);
 *  • error (≠404) → «Ошибка загрузки» + «Повторить» (ретрай повторно грузит).
 */
vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return { ...actual, getAlert: vi.fn(), postAction: vi.fn() }
})

import * as client from '@/api/client'
import DispatchAlert from './DispatchAlert'

function renderAlert(id: string) {
  return render(
    <MemoryRouter
      initialEntries={[`/alert/${id}`]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/alert/:id" element={<DispatchAlert />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('f9 · DispatchAlert — состояния', () => {
  afterEach(() => vi.clearAllMocks())

  it('loading: скелет «Загрузка алерта»', () => {
    vi.mocked(client.getAlert).mockReturnValue(new Promise(() => {}))
    renderAlert('inc-001')
    expect(screen.getByText('Загрузка алерта')).toBeInTheDocument()
  })

  it('empty/404: «Алерт не найден»', async () => {
    const { ApiError } = await import('@/api/client')
    vi.mocked(client.getAlert).mockRejectedValue(new ApiError(404, 'not found'))
    renderAlert('nope')
    expect(await screen.findByText('Алерт не найден')).toBeInTheDocument()
  })

  it('error (≠404): «Ошибка загрузки» + «Повторить» (ретрай грузит снова)', async () => {
    vi.mocked(client.getAlert).mockRejectedValue(new Error('сервис недоступен'))
    renderAlert('inc-001')
    expect(await screen.findByText('Ошибка загрузки')).toBeInTheDocument()
    const retry = screen.getByRole('button', { name: /Повторить/ })

    vi.mocked(client.getAlert).mockResolvedValue({
      incident: INCIDENT_DETAILS['inc-001'],
      video_window_sec: 15,
      requested_at: INCIDENT_DETAILS['inc-001'].ts_end,
    })
    fireEvent.click(retry)
    await waitFor(() => expect(vi.mocked(client.getAlert).mock.calls.length).toBeGreaterThan(1))
  })
})
