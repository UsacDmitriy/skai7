import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MapView } from './MapView'

/**
 * d4 · MapView — презентационная обёртка Leaflet. Монтирует контейнер карты в jsdom
 * и пробрасывает слои через children (без fetch/бизнес-логики).
 */
describe('MapView · d4', () => {
  it('монтирует leaflet-контейнер и рендерит слои-children', () => {
    const { container } = render(
      <MapView center={[55.751, 37.618]} zoom={11}>
        <div data-testid="layer">слой</div>
      </MapView>,
    )
    expect(container.querySelector('.leaflet-container')).toBeInTheDocument()
    expect(container.querySelector('.skai-map')).toBeInTheDocument()
    expect(screen.getByTestId('layer')).toBeInTheDocument()
  })
})
