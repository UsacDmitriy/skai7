import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import type { TripDossier as TripDossierData } from '@/api/types'

/**
 * f10 · TripDossier — состояния:
 *  • loading → скелет (не белый экран);
 *  • empty (пустой трек/таймлайн) → дружелюбные плашки «Трек недоступен» / «Событий рейса нет»;
 *  • error/404 → «Рейс не найден» / «Ошибка загрузки» (обработано, не пусто).
 */
vi.mock('@/components/map', () => ({
  MapView: () => <div data-testid="map" />,
  MarkerLayer: () => null,
}))
vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return { ...actual, getTrip: vi.fn() }
})

import * as client from '@/api/client'
import TripDossier from './TripDossier'

function renderTrip(id = 'trip-001') {
  return render(
    <MemoryRouter
      initialEntries={[`/trip/${id}`]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/trip/:id" element={<TripDossier />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('f10 · TripDossier — состояния', () => {
  afterEach(() => vi.mocked(client.getTrip).mockReset())

  it('loading: скелет вместо белого экрана', () => {
    vi.mocked(client.getTrip).mockReturnValue(new Promise(() => {}))
    const { container } = renderTrip()
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('empty: пустой трек/таймлайн → дружелюбные плашки', async () => {
    const empty: TripDossierData = { vehicle_plate: 'А777ВВ 77', track: [], timeline: [] }
    vi.mocked(client.getTrip).mockResolvedValue(empty)
    renderTrip()
    expect(await screen.findByText('Событий рейса нет')).toBeInTheDocument()
    expect(screen.getAllByText('Трек недоступен').length).toBeGreaterThanOrEqual(1)
  })

  it('404: «Рейс не найден»', async () => {
    const { ApiError } = await import('@/api/client')
    vi.mocked(client.getTrip).mockRejectedValue(new ApiError(404, 'not found'))
    renderTrip('nope')
    expect(await screen.findByText('Рейс не найден')).toBeInTheDocument()
  })

  it('error (≠404): «Ошибка загрузки» обработана', async () => {
    vi.mocked(client.getTrip).mockRejectedValue(new Error('сбой сети'))
    renderTrip()
    expect(await screen.findByText('Ошибка загрузки')).toBeInTheDocument()
  })
})
