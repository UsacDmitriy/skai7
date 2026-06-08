import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import type { RebRecovery as RebRecoveryData } from '@/api/types'

/**
 * f11 · RebRecovery — состояния:
 *  • loading → скелет;
 *  • empty (нет разрывов) → «Разрывов GPS не найдено — трек непрерывный»;
 *  • error/404 → «Ошибка загрузки» + «Повторить» / «Рейс не найден».
 */
vi.mock('@/components/map', () => ({
  MapView: () => <div data-testid="map" />,
  MarkerLayer: () => null,
}))
vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return { ...actual, getReb: vi.fn() }
})

import * as client from '@/api/client'
import RebRecovery from './RebRecovery'

const REB_NO_GAPS: RebRecoveryData = {
  vehicle_plate: 'А777ВВ 77',
  gps_track: [
    { lat: 55.75, lon: 37.61, ts: '2026-04-02T03:10:00' },
    { lat: 55.76, lon: 37.62, ts: '2026-04-02T03:11:00' },
  ],
  gap_periods: [],
  video_frames: [],
}

function renderReb(id = 'reb-001') {
  return render(
    <MemoryRouter
      initialEntries={[`/reb/${id}`]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/reb/:id" element={<RebRecovery />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('f11 · RebRecovery — состояния', () => {
  afterEach(() => vi.mocked(client.getReb).mockReset())

  it('loading: скелет вместо белого экрана', () => {
    vi.mocked(client.getReb).mockReturnValue(new Promise(() => {}))
    const { container } = renderReb()
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('empty: пустой список разрывов → «разрывов нет»', async () => {
    vi.mocked(client.getReb).mockResolvedValue(REB_NO_GAPS)
    renderReb()
    expect(
      await screen.findByText('Разрывов GPS не найдено — трек непрерывный'),
    ).toBeInTheDocument()
  })

  it('404: «Рейс не найден»', async () => {
    const { ApiError } = await import('@/api/client')
    vi.mocked(client.getReb).mockRejectedValue(new ApiError(404, 'not found'))
    renderReb('nope')
    expect(await screen.findByText('Рейс не найден')).toBeInTheDocument()
  })

  it('error (≠404): «Ошибка загрузки» + «Повторить» (ретрай грузит снова)', async () => {
    vi.mocked(client.getReb).mockRejectedValue(new Error('РЭБ-сервис недоступен'))
    renderReb()
    expect(await screen.findByText('Ошибка загрузки')).toBeInTheDocument()
    const retry = screen.getByRole('button', { name: /Повторить/ })

    vi.mocked(client.getReb).mockResolvedValue(REB_NO_GAPS)
    fireEvent.click(retry)
    await waitFor(() => expect(vi.mocked(client.getReb).mock.calls.length).toBeGreaterThan(1))
  })
})
