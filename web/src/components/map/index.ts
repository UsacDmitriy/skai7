/**
 * Публичный API map-примитивов (d4). Точка входа для экранов f6/f10/f11/f13:
 * `import { MapView, MarkerLayer, RoleToggle } from '@/components/map'`.
 */
export { MapView } from './MapView'
export type { MapViewProps } from './MapView'

export { MarkerLayer } from './MarkerLayer'
export type { MarkerLayerProps } from './MarkerLayer'

export { RoleToggle } from './RoleToggle'
export type { RoleToggleProps } from './RoleToggle'

export type { MapUnit, MapAlarm, Role } from './types'
