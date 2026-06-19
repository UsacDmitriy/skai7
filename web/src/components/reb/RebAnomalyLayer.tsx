/**
 * RebAnomalyLayer — слой РЭБ-аномалий поверх MapView.
 *
 * Рисует:
 *   - Circle на каждую зону (цвет по confidence_label)
 *   - Marker на каждое ТС в зоне (иконка RadioTower SVG)
 *   - Dashed Polyline (possible_route) для gap-аномалий
 *   - Popup по клику на маркер: госномер, тип, скорость, confidence, время, кнопка РЭБ
 *
 * Использует императивный Leaflet (как RiskHeatLayer.tsx) — useEffect + useRef + L.layerGroup.
 */

import { useEffect, useRef } from 'react'
import { useMap } from 'react-leaflet'
import * as L from 'leaflet'
import type { RebAnomalyZone, RebVehicleAnomaly } from '@/api/types'

const COLORS = {
  reb: { fill: '#dc2626', stroke: '#dc2626' },
  suspicious: { fill: '#ea580c', stroke: '#ea580c' },
} as const

const ANOMALY_LABEL: Record<string, string> = {
  gap: 'Потеря GPS',
  speed_spike: 'Скачок скорости',
  coord_jump: 'Прыжок координат',
}

function formatClock(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

function markerIcon(): L.DivIcon {
  return L.divIcon({
    className: '',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    html: `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M4.9 16.1C1 12.2 1 5.8 4.9 1.9"/>
      <path d="M7.8 4.7a6.14 6.14 0 0 0-.8 7.5"/>
      <circle cx="12" cy="9" r="2"/>
      <path d="M16.2 4.8c2 2 2.26 5.11.8 7.47"/>
      <path d="M19.1 1.9a11.93 11.93 0 0 1 0 16.97"/>
      <line x1="12" y1="9" x2="12" y2="22"/>
    </svg>`,
  })
}

function popupHtml(v: RebVehicleAnomaly, zone_confidence: number, confidence_label: string): string {
  const speed = v.max_speed_kmh != null ? `${Math.round(v.max_speed_kmh)} км/ч` : '—'
  const label = confidence_label === 'reb' ? 'РЭБ-зона' : 'Подозрительная аномалия'
  const time = formatClock(v.ts_start) + (v.ts_end ? ` – ${formatClock(v.ts_end)}` : '')
  const btn = v.reb_link_id
    ? `<a href="/reb/${encodeURIComponent(v.reb_link_id)}"
         style="display:inline-block;margin-top:8px;padding:4px 10px;border-radius:6px;
                background:#1e40af;color:#fff;font-size:12px;text-decoration:none;">
         Открыть РЭБ →
       </a>`
    : `<span style="display:inline-block;margin-top:8px;padding:4px 10px;border-radius:6px;
                    background:#e5e7eb;color:#6b7280;font-size:12px;">
         Нет данных РЭБ
       </span>`
  return `
    <div style="font-size:13px;line-height:1.6;min-width:180px;">
      <div style="font-weight:600;color:#0f172a;">${v.vehicle_plate}</div>
      <div style="color:#64748b;">Тип: ${ANOMALY_LABEL[v.anomaly_type] ?? v.anomaly_type}</div>
      <div style="color:#64748b;">Макс. скорость: ${speed}</div>
      <div style="color:#64748b;">Confidence: ${zone_confidence} (${label})</div>
      <div style="color:#64748b;">Время: ${time}</div>
      ${btn}
    </div>
  `
}

export interface RebAnomalyLayerProps {
  zones: RebAnomalyZone[]
}

export function RebAnomalyLayer({ zones }: RebAnomalyLayerProps) {
  const map = useMap()
  const layerRef = useRef<L.LayerGroup | null>(null)

  useEffect(() => {
    if (!layerRef.current) {
      layerRef.current = L.layerGroup().addTo(map)
    }
    const layer = layerRef.current
    layer.clearLayers()

    for (const zone of zones) {
      const [clat, clon] = zone.centroid
      if (!Number.isFinite(clat) || !Number.isFinite(clon)) continue
      const color = COLORS[zone.confidence_label] ?? COLORS.suspicious

      // Круг зоны.
      L.circle([clat, clon], {
        radius: zone.radius_m > 0 ? zone.radius_m : 300,
        color: color.stroke,
        fillColor: color.fill,
        fillOpacity: zone.confidence_label === 'reb' ? 0.15 : 0.10,
        opacity: zone.confidence_label === 'reb' ? 0.6 : 0.5,
        weight: 1.5,
      })
        .bindTooltip(
          `РЭБ-зона · ${zone.confidence_label === 'reb' ? 'подтверждена' : 'подозрительная'} · ${zone.vehicles.length} ТС · confidence ${zone.confidence}`,
          { sticky: true, className: 'text-xs' },
        )
        .addTo(layer)

      // Маркеры и пунктиры ТС.
      for (const v of zone.vehicles) {
        if (!Number.isFinite(v.lat) || !Number.isFinite(v.lon)) continue

        L.marker([v.lat, v.lon], { icon: markerIcon() })
          .bindPopup(popupHtml(v, zone.confidence, zone.confidence_label), {
            maxWidth: 260,
            className: 'reb-popup',
          })
          .addTo(layer)

        if (v.possible_route.length >= 2) {
          const positions = v.possible_route.filter(
            ([la, lo]) => Number.isFinite(la) && Number.isFinite(lo),
          ) as [number, number][]
          if (positions.length >= 2) {
            L.polyline(positions, {
              color: '#dc2626',
              weight: 2,
              opacity: 0.7,
              dashArray: '6 8',
            }).addTo(layer)
          }
        }
      }
    }

    return () => {
      layer.clearLayers()
    }
  }, [map, zones])

  useEffect(() => {
    return () => {
      layerRef.current?.remove()
      layerRef.current = null
    }
  }, [])

  return null
}
