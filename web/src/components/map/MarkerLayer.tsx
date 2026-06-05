import { useRef } from 'react'
import * as L from 'leaflet'
import { Marker, Popup } from 'react-leaflet'
import MarkerClusterGroup from 'react-leaflet-cluster'
import { SeverityBadge, type Severity } from '../ui/SeverityBadge'
import type { MapUnit } from './types'

/**
 * MarkerLayer — слой маркеров ТС поверх `MapView`.
 *
 * Презентация без fetch: props → маркеры. Ключевые инварианты §7.6:
 *  • ДЕДУП: ровно один маркер на `unit_id` (НЕ на `AlarmId`) — защита `Map<unit_id>`
 *    даже при дублях во входном массиве; остаётся наихудший по severity (при равенстве — последний).
 *  • Цвет маркера — severity-маппинг d1 (`critical→critical · high→high · medium→warning · low→ok`),
 *    неизвестный severity → нейтральный фолбэк.
 *  • Кольцо статуса: online `--marker-online` / offline `--marker-offline`.
 *  • Кластеризация по радиусу 40px; одиночное ТС — обычный маркер (без кластер-иконки).
 *
 * Императивные (Leaflet divIcon) цвета берутся из CSS-переменных d1 через `var(...)`
 * в inline-style — без дублирования hex в JS.
 */
export interface MarkerLayerProps {
  units: MapUnit[]
  onSelect?: (unitId: string) => void
}

/** severity (API) → CSS-переменная цвета d1. medium→warning, low→ok (§4). */
const SEVERITY_VAR: Record<Severity, string> = {
  critical: '--sev-critical',
  high: '--sev-high',
  medium: '--sev-warning',
  low: '--sev-ok',
}
/** Неизвестный severity → нейтральный фолбэк (без падения маппинга). */
const FALLBACK_VAR = '--color-muted'

/** Ранг для выбора наихудшего алярма при дедупликации. */
const SEVERITY_RANK: Record<Severity, number> = { critical: 4, high: 3, medium: 2, low: 1 }

/** Локализованная подпись severity для бейджа в попапе. */
const SEVERITY_LABEL: Record<Severity, string> = {
  critical: 'Критично',
  high: 'Высокий',
  medium: 'Средний',
  low: 'Низкий',
}

function pinColorVar(severity: string): string {
  return `var(${SEVERITY_VAR[severity as Severity] ?? FALLBACK_VAR})`
}

function severityRank(severity: string): number {
  return SEVERITY_RANK[severity as Severity] ?? 0
}

/** Координаты пригодны для Leaflet (не null/undefined/NaN/Infinity). */
function hasValidCoords(unit: MapUnit): boolean {
  return Number.isFinite(unit.lat) && Number.isFinite(unit.lon)
}

/**
 * Дедуп по `unit_id`: один маркер на ТС. Остаётся наихудший по severity,
 * при равенстве — последний встреченный (защита от дублей бэка).
 */
function dedupeUnits(units: MapUnit[]): MapUnit[] {
  const byId = new Map<string, MapUnit>()
  for (const unit of units) {
    const prev = byId.get(unit.unit_id)
    if (!prev || severityRank(unit.severity) >= severityRank(prev.severity)) {
      byId.set(unit.unit_id, unit)
    }
  }
  return [...byId.values()]
}

/** Маркер ТС: цветной pin + кольцо статуса. Доступное имя — госномер + статус. */
function buildIcon(unit: MapUnit): L.DivIcon {
  const ring = unit.online ? 'var(--marker-online)' : 'var(--marker-offline)'
  const pin = `--pin-color:${pinColorVar(unit.severity)};--ring-color:${ring}`
  return L.divIcon({
    className: '',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -14],
    html: `<span class="skai-marker__pin" style="${pin}"></span>`,
  })
}

/** Кластер-иконка: кружок `primary` с числом ТС (tabular-nums, белый текст). */
function createClusterIcon(cluster: L.MarkerCluster): L.DivIcon {
  const count = cluster.getChildCount()
  return L.divIcon({
    html: `<div class="skai-cluster" aria-label="Кластер: ${count} ТС">${count}</div>`,
    className: '',
    iconSize: L.point(40, 40),
  })
}

function formatTime(ts: string): string {
  const date = new Date(ts)
  if (Number.isNaN(date.getTime())) return ts
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

/** Один маркер ТС с попапом. Клик/Enter → onSelect + открытие попапа. */
function UnitMarker({ unit, onSelect }: { unit: MapUnit; onSelect?: (unitId: string) => void }) {
  const keyHandlerRef = useRef<((ev: KeyboardEvent) => void) | null>(null)
  const alarm = unit.last_alarm
  const status = unit.online ? 'на связи' : 'не на связи'
  const accessibleName = `ТС ${unit.vehicle_plate}, ${status}`

  const eventHandlers: L.LeafletEventHandlerFnMap = {
    click() {
      onSelect?.(unit.unit_id)
    },
    add(event) {
      const marker = event.target as L.Marker
      const el = marker.getElement()
      if (!el) return
      // Leaflet уже выставил tabindex=0/role=button (keyboard:true); добавляем
      // явную активацию Enter/Space → попап + onSelect (гарантия a11y-чека).
      const handler = (ev: KeyboardEvent) => {
        if (ev.key === 'Enter' || ev.key === ' ' || ev.key === 'Spacebar') {
          ev.preventDefault()
          marker.openPopup()
          onSelect?.(unit.unit_id)
        }
      }
      keyHandlerRef.current = handler
      el.addEventListener('keydown', handler)
    },
    remove(event) {
      const el = (event.target as L.Marker).getElement()
      if (el && keyHandlerRef.current) {
        el.removeEventListener('keydown', keyHandlerRef.current)
        keyHandlerRef.current = null
      }
    },
  }

  return (
    <Marker
      position={[unit.lat, unit.lon]}
      icon={buildIcon(unit)}
      keyboard
      title={accessibleName}
      alt={accessibleName}
      eventHandlers={eventHandlers}
    >
      <Popup>
        <div className="skai-popup__plate">{unit.vehicle_plate}</div>
        {alarm ? (
          <>
            <div className="skai-popup__alarm">
              {alarm.alarm_label_ru}{' '}
              <SeverityBadge
                severity={alarm.severity}
                label={SEVERITY_LABEL[alarm.severity] ?? alarm.severity}
              />
            </div>
            <div className="skai-popup__time">{formatTime(alarm.ts)}</div>
            <a className="skai-popup__link" href={`/incidents/${alarm.id}`}>
              Открыть инцидент →
            </a>
          </>
        ) : (
          <div className="skai-popup__time">Без активных алярмов</div>
        )}
      </Popup>
    </Marker>
  )
}

export function MarkerLayer({ units, onSelect }: MarkerLayerProps) {
  // Сначала дедуп по unit_id, затем отсев точек без валидных координат.
  const visible = dedupeUnits(units).filter(hasValidCoords)

  return (
    <MarkerClusterGroup
      maxClusterRadius={40}
      showCoverageOnHover={false}
      chunkedLoading
      iconCreateFunction={createClusterIcon}
    >
      {visible.map((unit) => (
        <UnitMarker key={unit.unit_id} unit={unit} onSelect={onSelect} />
      ))}
    </MarkerClusterGroup>
  )
}
