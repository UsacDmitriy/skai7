import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'

/**
 * w3-15 · Кросс-врезка видеодосье рейса (§9.4): бэк-ссылка
 * «К карточке инцидента» → `/incidents/<id>` (id рейса == incident_id).
 *
 * NB: основной рендер-тест досье (f10) живёт в `TripDossier.test.tsx` (трек w3-4) —
 * его правит соседний агент в этой же воркти. Чтобы коммитить только w3-15-файлы
 * и не задеть чужую работу, врезка вынесена в отдельный файл.
 *
 * Карту (leaflet) мокаем заглушкой без children → Polyline/useMap/MarkerLayer не
 * монтируются. Данные рейса — фикстуры f3 (`VITE_USE_FIXTURES=true`).
 */

// MapView-заглушка не рендерит детей → leaflet не монтируется в jsdom.
vi.mock('@/components/map', () => ({
  MapView: () => <div data-testid="map" />,
  MarkerLayer: () => null,
}))

import TripDossier from './TripDossier'

function LocationProbe() {
  const loc = useLocation()
  return <div data-testid="loc">{loc.pathname}</div>
}

function renderTrip(id: string) {
  return render(
    <MemoryRouter
      initialEntries={[`/trip/${id}`]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/trip/:id" element={<TripDossier />} />
        <Route path="*" element={null} />
      </Routes>
      <LocationProbe />
    </MemoryRouter>,
  )
}

describe('TripDossier · кросс-врезка (w3-15)', () => {
  it('бэк-ссылка «К карточке инцидента» → /incidents/<id>', async () => {
    renderTrip('trip-001')

    const back = await screen.findByRole('button', { name: /К карточке инцидента/ })
    fireEvent.click(back)
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/incidents/trip-001'))
  })
})
