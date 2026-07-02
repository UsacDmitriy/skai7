import { useEffect, useRef } from 'react'
import { useMap } from 'react-leaflet'
import * as L from 'leaflet'
import type { RiskZone, RiskZoneKind } from '../../api/types'
import { resolveCssColor } from '../ui/cssVar'

export interface RiskHeatLayerProps {
  zones: RiskZone[]
  /** Фильтр типа зоны: incident | reb. */
  kind: RiskZoneKind
}

/** avg_risk [0..100] → цвет токена d1. */
function riskColor(avgRisk: number): string {
  if (avgRisk >= 70) return 'var(--sev-critical)'
  if (avgRisk >= 45) return 'var(--sev-high)'
  if (avgRisk >= 20) return 'var(--sev-warning)'
  return 'var(--sev-ok)'
}

/** avg_risk [0..100] → прозрачность заливки [0.15..0.65]. */
function riskOpacity(avgRisk: number): number {
  return 0.15 + (avgRisk / 100) * 0.5
}

/**
 * RiskHeatLayer — тепловой слой риск-зон поверх MapView/MapContainer.
 *
 * Реализован через L.layerGroup + L.circle (совместимая замена leaflet.heat §d7).
 * Тоггл `kind` меняет отображаемые зоны без перемонтажа карты.
 * Только слой — без логики карты (её даёт d4/f6).
 */
export function RiskHeatLayer({ zones, kind }: RiskHeatLayerProps) {
  const map = useMap()
  const layerRef = useRef<L.LayerGroup | null>(null)

  useEffect(() => {
    if (!layerRef.current) {
      layerRef.current = L.layerGroup().addTo(map)
    }
    const layer = layerRef.current
    layer.clearLayers()

    const visible = zones.filter((z) => z.kind === kind)

    for (const zone of visible) {
      const [lat, lon] = zone.centroid
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue

      L.circle([lat, lon], {
        radius: zone.radius_m > 0 ? zone.radius_m : 300,
        color: 'transparent',
        fillColor: resolveCssColor(riskColor(zone.avg_risk)),
        fillOpacity: riskOpacity(zone.avg_risk),
        interactive: false,
      })
        .bindTooltip(
          `${zone.top_alarm_code} · риск ${zone.avg_risk.toFixed(0)} · ${zone.alarm_count} алярм(ов)`,
          { sticky: true, className: 'text-xs' },
        )
        .addTo(layer)
    }

    return () => {
      layer.clearLayers()
    }
  }, [map, zones, kind])

  // Очистка при размонтировании.
  useEffect(() => {
    return () => {
      layerRef.current?.remove()
      layerRef.current = null
    }
  }, [])

  return null
}
