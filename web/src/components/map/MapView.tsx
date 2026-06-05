import type { ReactNode } from 'react'
import { MapContainer, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import './map.css'
import { cn } from '../ui/cn'

/**
 * MapView — презентационная обёртка Leaflet-карты для `/monitor` (идея #4/#10).
 *
 * Тёмная тема 24/7: тёмные тайлы (CARTO dark_matter), фон контейнера `ink`
 * (#0F172A) до загрузки тайлов (см. `.skai-map` в map.css). Контролы зума и
 * попапы перекрашены под токены d1 на тёмном фоне.
 *
 * Без fetch и бизнес-логики: только props → разметка. Слои (например
 * `MarkerLayer`) передаются через `children`. Кластеризацию ТС с радиусом 40px
 * (§7.6) применяет `MarkerLayer` — там, где живут маркеры и работает дедуп.
 */
export interface MapViewProps {
  /** Центр карты `[lat, lon]`. */
  center: [number, number]
  /** Начальный зум. */
  zoom: number
  /** Слои карты (маркеры, оверлеи). */
  children?: ReactNode
  className?: string
}

/** Тёмные тайлы CARTO `dark_matter` (эквивалент тёмной темы /monitor). */
const TILE_URL = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors ' +
  '&copy; <a href="https://carto.com/attributions">CARTO</a>'

export function MapView({ center, zoom, children, className }: MapViewProps) {
  return (
    <MapContainer
      center={center}
      zoom={zoom}
      scrollWheelZoom
      className={cn('skai-map', className)}
      style={{ height: '100%', width: '100%' }}
    >
      <TileLayer
        url={TILE_URL}
        attribution={TILE_ATTRIBUTION}
        subdomains="abcd"
        maxZoom={20}
      />
      {children}
    </MapContainer>
  )
}
