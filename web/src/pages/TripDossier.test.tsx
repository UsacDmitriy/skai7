import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { TRIP_DOSSIER } from '@/api/fixtures'

/**
 * f10 · TripDossier (`/trip/:id`) — видеодосье рейса:
 *  • рендерит трек (карту/график) + хронологию событий;
 *  • `has_video` управляет иконкой пункта: «видео» vs «без видео»;
 *  • выбор события синхронизирует видео-панель момента.
 * Карта мокается (MapView игнорирует children → Leaflet не монтируется).
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

describe('f10 · TripDossier', () => {
  afterEach(() => vi.mocked(client.getTrip).mockReset())

  it('рендерит шапку рейса, трек и хронологию событий', async () => {
    vi.mocked(client.getTrip).mockResolvedValue(TRIP_DOSSIER)
    renderTrip()

    expect(await screen.findByText('Видеодосье рейса')).toBeInTheDocument()
    expect(screen.getAllByText('А777ВВ 77').length).toBeGreaterThanOrEqual(1)
    // Событий = длина timeline
    expect(screen.getByText(String(TRIP_DOSSIER.timeline.length))).toBeInTheDocument()
    // Метки событий хронологии
    expect(screen.getByText('Превышение скорости')).toBeInTheDocument()
    expect(screen.getByText('Резкий манёвр')).toBeInTheDocument()
  })

  it('has_video управляет иконкой пункта (видео / без видео)', async () => {
    vi.mocked(client.getTrip).mockResolvedValue(TRIP_DOSSIER)
    renderTrip()
    await screen.findByText('Видеодосье рейса')

    // HARSH_CORNERING (has_video=false) → «без видео»
    const noVideoRow = screen.getByText('Резкий манёвр').closest('button') as HTMLElement
    expect(within(noVideoRow).getByText('без видео')).toBeInTheDocument()
    // OVERSPEED (has_video=true) → «видео»
    const videoRow = screen.getByText('Превышение скорости').closest('button') as HTMLElement
    expect(within(videoRow).getByText('видео')).toBeInTheDocument()
  })

  it('выбор события без видео показывает плашку «Видео недоступно»', async () => {
    vi.mocked(client.getTrip).mockResolvedValue(TRIP_DOSSIER)
    renderTrip()
    await screen.findByText('Видеодосье рейса')

    fireEvent.click(screen.getByText('Резкий манёвр')) // has_video=false
    expect(await screen.findByText('Видео недоступно')).toBeInTheDocument()
  })
})
