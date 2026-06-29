import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMap } from 'react-leaflet'
import * as L from 'leaflet'
import { Clock, Layers, Loader2, MapPinOff, RefreshCw } from 'lucide-react'
import * as client from '@/api/client'
import type { IncidentSummary, RebAnomalyZone, RiskZone, RiskZoneKind, Severity, Source } from '@/api/types'
import { RebAnomalyLayer } from '@/components/reb/RebAnomalyLayer'
import { Card, ScoreBar, SeverityBadge } from '@/components'
import { SabotageWidget } from '@/components/SabotageWidget'
import { MapView, MarkerLayer, RoleToggle } from '@/components/map'
import type { MapUnit } from '@/components/map'
import { RiskHeatLayer } from '@/components/ai/RiskHeatLayer'
import { useRole } from '@/state/role'
import type { Role } from '@/state/role'
import { SmartQueryInput } from '@/components/ui/SmartQueryInput'
import { alarmSearch } from '@/state/alarmSearch'
import { dedupeByUnit, filterByRole } from '@/state/roleFilter'
import { cn } from '@/components/ui/cn'

/**
 * f6 · Живой мониторинг — карта (`/monitor`). Полная версия, **заменяет scaffold
 * f4** (§7.7): после full-scope `Monitor.tsx` принадлежит f6.
 *
 * Боевой экран дежурного 24/7: тёмная Leaflet-карта парка (d4 `MapView` +
 * `MarkerLayer`), один маркер на ТС (дедуп §6/§7.6), цвет по severity, лента
 * активных алярмов справа, ролевые слои (`RoleToggle` d4) и фильтры.
 *
 * Данные: `client.listIncidents()` → `IncidentSummary[]` (§3.1). Идентичность ТС
 * на уровне ленты — `vehicle_plate` (в `IncidentSummary` нет `unit_id`; он есть
 * только в `IncidentDetail`), поэтому `unit_id` карты = госномер. Статус связи
 * `online` выводим из жизненного цикла алярма: `active`/`in_progress` → на связи.
 */

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: 'Критично',
  high: 'Высокий',
  medium: 'Средний',
  low: 'Низкий',
}

const SOURCE_LABEL: Record<Source, string> = {
  DMS: 'DMS',
  ADAS: 'ADAS',
  TELEMATICS: 'Телематика',
  COMBINED: 'Оба',
  DIAGNOSTIC: 'Диагностика',
}

type SortKey = 'ts' | 'risk_score'
type FilterKey = 'all' | 'critical' | 'no_video'

const FILTERS: { value: FilterKey; label: string }[] = [
  { value: 'all', label: 'Все' },
  { value: 'critical', label: 'Критичные' },
  { value: 'no_video', label: 'Без видео' },
]

/** Центр парка по умолчанию (Москва) — фолбэк, когда нет валидных координат. */
const FALLBACK_CENTER: [number, number] = [55.751, 37.618]
const DEFAULT_ZOOM = 11

/** Часовой пояс парка для отображения времени алярма из UTC-`ts`. */
const PARK_TZ = 'Europe/Moscow'

function formatTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: PARK_TZ,
  }).format(d)
}

/** Валидные координаты для карты (не null/NaN/Infinity). */
function hasCoords(inc: IncidentSummary): boolean {
  return inc.lat != null && inc.lon != null && Number.isFinite(inc.lat) && Number.isFinite(inc.lon)
}

function passesFilter(inc: IncidentSummary, filter: FilterKey): boolean {
  if (filter === 'critical') return inc.severity === 'critical'
  if (filter === 'no_video') return inc.video_available === false
  return true
}

/** На связи, если алярм в активной фазе жизненного цикла. */
function isOnline(inc: IncidentSummary): boolean {
  return inc.status === 'active' || inc.status === 'in_progress'
}

/**
 * Дедуп ленты в `MapUnit[]`: один объект на госномер (= `unit_id` карты), через
 * общий хелпер f13 `dedupeByUnit` (1 `unit_id` = 1 маркер, НЕ на каждый `AlarmId`).
 * Остаётся наихудший по severity, при равенстве — последний по `ts`. Координаты
 * берём как есть (null → NaN): `MarkerLayer` сам отсеет точки без координат,
 * но в ленте такие алярмы остаются (бейдж «без координат»).
 */
function buildUnits(incidents: IncidentSummary[]): MapUnit[] {
  // `unit_id` карты = госномер (в IncidentSummary нет unit_id — он в IncidentDetail).
  const tagged = incidents.map((inc) => ({ ...inc, unit_id: inc.vehicle_plate }))
  return dedupeByUnit(tagged).map((inc) => ({
    unit_id: inc.vehicle_plate,
    vehicle_plate: inc.vehicle_plate,
    lat: inc.lat ?? Number.NaN,
    lon: inc.lon ?? Number.NaN,
    severity: inc.severity,
    online: isOnline(inc),
    last_alarm: {
      id: inc.id,
      alarm_label_ru: inc.alarm_label_ru,
      severity: inc.severity,
      ts: inc.ts,
    },
  }))
}

/** Центр карты — среднее валидных координат, иначе фолбэк парка. */
function computeCenter(incidents: IncidentSummary[]): [number, number] {
  const pts = incidents.filter(hasCoords)
  if (pts.length === 0) return FALLBACK_CENTER
  const lat = pts.reduce((s, p) => s + (p.lat as number), 0) / pts.length
  const lon = pts.reduce((s, p) => s + (p.lon as number), 0) / pts.length
  return [lat, lon]
}

// ── f18 · Тепловая карта нарушений + риск-зоны (идея #14) ─────────────────────

/** Слои карты, переключаемые независимо. */
type LayerKey = 'heat' | 'incident' | 'reb' | 'reb_anomaly'

/** Тип фильтра по часу пика зоны (`peak_hour` 0..23) либо «все часы». */
type ZoneHour = number | 'all'

/** Максимум точек теплового слоя нарушений — защита от лагов при многих алярмах. */
const MAX_HEAT_POINTS = 500

/** Префикс кода DMS-аларма: Логист не видит DMS-зоны (как и DMS-ленту, f13). */
const DMS_PREFIX = 'DMS'

/** Экранирование текста зоны для HTML-попапа Leaflet. */
function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/**
 * Ролевая видимость риск-зон: Логист — без DMS-зон (зоны с `top_alarm_code`,
 * начинающимся на `DMS`). Остальные роли видят все зоны. Чистая, без мутаций.
 */
function zonesForRole(role: Role, zones: readonly RiskZone[]): RiskZone[] {
  if (role === 'logist') return zones.filter((z) => !z.top_alarm_code.startsWith(DMS_PREFIX))
  return [...zones]
}

/**
 * Видимые алярмы → псевдо-зоны для теплового слоя нарушений: каждая точка —
 * `centroid` алярма, «жар» по `risk_score`. При многих точках берём топ по риску
 * (`MAX_HEAT_POINTS`) — слой остаётся отзывчивым. `peak_hour` не используется в
 * heat-режиме (0), чтобы не зависеть от часового пояса.
 */
function buildHeatZones(incidents: IncidentSummary[]): RiskZone[] {
  const pts = incidents.filter(hasCoords)
  const limited =
    pts.length > MAX_HEAT_POINTS
      ? [...pts].sort((a, b) => b.risk_score - a.risk_score).slice(0, MAX_HEAT_POINTS)
      : pts
  return limited.map((inc) => ({
    zone_id: inc.id,
    centroid: [inc.lat as number, inc.lon as number],
    radius_m: 250,
    alarm_count: 1,
    avg_risk: inc.risk_score,
    top_alarm_code: inc.alarm_label_ru,
    peak_hour: 0,
    kind: 'incident' as RiskZoneKind,
  }))
}

/**
 * ZoneInfoLayer — интерактивные маркеры центроидов риск-зон с попапом
 * (`top_alarm_code`, час пика `peak_hour`, число алярмов `alarm_count`).
 * Идёт поверх `RiskHeatLayer` (тот рисует «жар», но некликабелен §d7).
 * Живёт только внутри `MapView`/`MapContainer` (использует `useMap`).
 */
function ZoneInfoLayer({ zones, kind }: { zones: RiskZone[]; kind: RiskZoneKind }) {
  const map = useMap()
  const layerRef = useRef<L.LayerGroup | null>(null)

  useEffect(() => {
    if (!layerRef.current) {
      layerRef.current = L.layerGroup().addTo(map)
    }
    const layer = layerRef.current
    layer.clearLayers()

    for (const zone of zones.filter((z) => z.kind === kind)) {
      const [lat, lon] = zone.centroid
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue

      L.circleMarker([lat, lon], {
        radius: 7,
        weight: 2,
        color: '#fff',
        fillColor: 'var(--sev-high)',
        fillOpacity: 0.9,
      })
        .bindPopup(
          `<div class="text-xs leading-relaxed">
             <div class="font-semibold">${escapeHtml(zone.top_alarm_code)}</div>
             <div>Час пика: ${zone.peak_hour}:00</div>
             <div>Алярмов: ${zone.alarm_count}</div>
             <div>Средний риск: ${zone.avg_risk.toFixed(0)}</div>
           </div>`,
        )
        .addTo(layer)
    }

    return () => {
      layer.clearLayers()
    }
  }, [map, zones, kind])

  // Очистка слоя при размонтировании.
  useEffect(() => {
    return () => {
      layerRef.current?.remove()
      layerRef.current = null
    }
  }, [])

  return null
}

function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        'rounded-md border px-2.5 py-1 text-xs font-medium transition-colors',
        active
          ? 'border-primary bg-primary-50 text-primary'
          : 'border-border bg-surface text-muted hover:border-primary hover:text-ink',
      )}
    >
      {children}
    </button>
  )
}

export default function Monitor() {
  const navigate = useNavigate()
  const [incidents, setIncidents] = useState<IncidentSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const { role, setRole } = useRole()
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<FilterKey>('all')
  const [sortKey, setSortKey] = useState<SortKey>('ts')
  const [selected, setSelected] = useState<string | null>(null)

  // f18 · слои карты (тепловая карта нарушений + риск-зоны) и фильтр по часу пика.
  const [layers, setLayers] = useState<Record<LayerKey, boolean>>({
    heat: false,
    incident: false,
    reb: false,
    reb_anomaly: false,
  })
  const [zoneHour, setZoneHour] = useState<ZoneHour>('all')
  const [zones, setZones] = useState<RiskZone[]>([])
  const [zonesLoading, setZonesLoading] = useState(false)
  const [zonesError, setZonesError] = useState<string | null>(null)

  const [rebAnomalyZones, setRebAnomalyZones] = useState<RebAnomalyZone[]>([])
  const [rebAnomalyLoading, setRebAnomalyLoading] = useState(false)

  const toggleLayer = useCallback((key: LayerKey) => {
    setLayers((prev) => ({ ...prev, [key]: !prev[key] }))
  }, [])

  // Безопасник — акцент на риск: лента по умолчанию сортируется по risk_score.
  useEffect(() => {
    if (role === 'security') setSortKey('risk_score')
  }, [role])

  // Ссылки на карточки ленты по госномеру — для скролла при onSelect.
  const cardRefs = useRef(new Map<string, HTMLDivElement>())

  const load = useCallback(() => {
    let alive = true
    setLoading(true)
    setError(null)
    client
      .listIncidents()
      .then((data) => alive && setIncidents(data))
      .catch((e: unknown) => alive && setError(e instanceof Error ? e.message : 'Ошибка загрузки'))
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => load(), [load])

  // f18 · риск-зоны (`GET /api/zones`, b19). Один запрос всех зон; фильтрация
  // по типу/часу/роли — на клиенте. Пустой набор валиден (слой пуст, карта жива).
  const loadZones = useCallback(() => {
    let alive = true
    setZonesLoading(true)
    setZonesError(null)
    client
      .getZones()
      .then((data) => alive && setZones(data))
      .catch(
        (e: unknown) =>
          alive && setZonesError(e instanceof Error ? e.message : 'Ошибка загрузки зон'),
      )
      .finally(() => alive && setZonesLoading(false))
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => loadZones(), [loadZones])

  const loadRebAnomalies = useCallback(() => {
    if (rebAnomalyZones.length > 0 || rebAnomalyLoading) return
    let alive = true
    setRebAnomalyLoading(true)
    client
      .getRebAnomalies()
      .then((data) => { if (alive) setRebAnomalyZones(data) })
      .catch(() => { if (alive) setRebAnomalyZones([]) })
      .finally(() => { if (alive) setRebAnomalyLoading(false) })
    return () => { alive = false }
  }, [rebAnomalyZones.length, rebAnomalyLoading])

  useEffect(() => {
    if (layers.reb_anomaly) loadRebAnomalies()
  }, [layers.reb_anomaly, loadRebAnomalies])

  // Ролевая видимость (f13: единое правило `filterByRole` — общее с лентой событий).
  const roleVisible = useMemo(() => filterByRole(role, incidents), [role, incidents])

  // Лента: роль → поиск → фильтр → сортировка. Показываем ВСЕ алярмы (в т.ч. без координат).
  const visible = useMemo(() => {
    const searched = alarmSearch(search, roleVisible)
    const rows = searched.filter((inc) => passesFilter(inc, filter))
    return [...rows].sort((a, b) =>
      sortKey === 'risk_score' ? b.risk_score - a.risk_score : b.ts.localeCompare(a.ts),
    )
  }, [roleVisible, search, filter, sortKey])

  // Маркеры: дедуп ленты по госномеру (MarkerLayer ещё раз защитит от дублей).
  const units = useMemo(() => buildUnits(visible), [visible])
  const center = useMemo(() => computeCenter(incidents), [incidents])

  // f18 · тепловой слой нарушений из видимых (роль+фильтр) алярмов; кап по точкам.
  const heatZones = useMemo(() => buildHeatZones(visible), [visible])

  // f18 · риск-зоны под текущую роль и фильтр по часу пика (`peak_hour`).
  const visibleZones = useMemo(() => {
    const roled = zonesForRole(role, zones)
    return zoneHour === 'all' ? roled : roled.filter((z) => z.peak_hour === zoneHour)
  }, [zones, role, zoneHour])

  // Часы, в которые реально есть зоны (для компактного селектора фильтра по часу).
  const zoneHours = useMemo(() => {
    const set = new Set(zonesForRole(role, zones).map((z) => z.peak_hour))
    return [...set].sort((a, b) => a - b)
  }, [zones, role])

  // Сброс осиротевшего фильтра по часу, если под текущую роль такого часа нет.
  useEffect(() => {
    if (zoneHour !== 'all' && !zoneHours.includes(zoneHour)) setZoneHour('all')
  }, [zoneHours, zoneHour])

  // Смена роли/фильтра не оставляет «осиротевшую» подсветку.
  useEffect(() => {
    if (selected && !visible.some((inc) => inc.vehicle_plate === selected)) {
      setSelected(null)
    }
  }, [visible, selected])

  const handleSelect = useCallback((unitId: string) => {
    setSelected(unitId)
    const el = cardRefs.current.get(unitId)
    el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [])

  const activeCount = visible.length

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      {/* ── Тулбар: роль + фильтры + сортировка ───────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold text-ink">Живой мониторинг</h1>
          <RoleToggle value={role} onChange={setRole} />
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {FILTERS.map((f) => (
            <Chip key={f.value} active={filter === f.value} onClick={() => setFilter(f.value)}>
              {f.label}
            </Chip>
          ))}
        </div>
      </div>

      {/* ── Сводка саботажа камеры (f12, идея #9) ─────────────────────────── */}
      <SabotageWidget variant="compact" />

      {/* ── f18 · Слои карты: тепловая карта нарушений + риск-зоны (идея #14) ─ */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-muted">
          <Layers className="h-3.5 w-3.5" aria-hidden />
          Слои:
        </span>
        <Chip active={layers.heat} onClick={() => toggleLayer('heat')}>
          Тепловая карта
        </Chip>
        <Chip active={layers.incident} onClick={() => toggleLayer('incident')}>
          Зоны инцидентов
        </Chip>
        <Chip active={layers.reb} onClick={() => toggleLayer('reb')}>
          РЭБ-зоны
        </Chip>
        <Chip active={layers.reb_anomaly} onClick={() => toggleLayer('reb_anomaly')}>
          {rebAnomalyLoading ? <Loader2 className="h-3 w-3 animate-spin" aria-hidden /> : null}
          РЭБ-аномалии
        </Chip>

        {/* Фильтр зон по часу пика (`peak_hour`); виден, когда есть слой зон. */}
        {(layers.incident || layers.reb) && zoneHours.length > 0 && (
          <label className="ml-1 inline-flex items-center gap-1.5 text-xs text-muted">
            <Clock className="h-3.5 w-3.5" aria-hidden />
            Час пика:
            <select
              value={zoneHour}
              onChange={(e) =>
                setZoneHour(e.target.value === 'all' ? 'all' : Number(e.target.value))
              }
              className="rounded-md border border-border bg-surface px-1.5 py-1 text-xs text-ink"
            >
              <option value="all">все</option>
              {zoneHours.map((h) => (
                <option key={h} value={h}>
                  {h}:00
                </option>
              ))}
            </select>
          </label>
        )}

        {/* Состояния загрузки/ошибки зон (карта продолжает работать). */}
        {zonesLoading && (
          <span className="inline-flex items-center gap-1 text-xs text-muted" role="status">
            <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
            зоны…
          </span>
        )}
        {!zonesLoading && zonesError && (
          <button
            type="button"
            onClick={loadZones}
            className="inline-flex items-center gap-1 rounded-md border border-critical-border bg-critical-bg px-2 py-1 text-xs text-critical-text hover:opacity-90"
          >
            <RefreshCw className="h-3 w-3" aria-hidden />
            зоны не загрузились — повторить
          </button>
        )}
      </div>

      {/* ── Карта + лента ─────────────────────────────────────────────────── */}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[1fr_minmax(340px,400px)]">
        {/* Карта (рендерится всегда, в т.ч. при пустой/ошибочной ленте). */}
        <div className="relative min-h-[360px] overflow-hidden rounded-xl border border-border">
          <MapView center={center} zoom={DEFAULT_ZOOM}>
            {!loading && !error && <MarkerLayer units={units} onSelect={handleSelect} />}
            {/* f18 · тепловая карта нарушений (переиспользуем d7 RiskHeatLayer). */}
            {layers.heat && !error && <RiskHeatLayer zones={heatZones} kind="incident" />}
            {/* f18 · слой зон инцидентов: «жар» (d7) + кликабельные центроиды-попапы. */}
            {layers.incident && (
              <>
                <RiskHeatLayer zones={visibleZones} kind="incident" />
                <ZoneInfoLayer zones={visibleZones} kind="incident" />
              </>
            )}
            {/* f18 · РЭБ-зоны отдельным слоем (никто из конкурентов их не даёт). */}
            {layers.reb && (
              <>
                <RiskHeatLayer zones={visibleZones} kind="reb" />
                <ZoneInfoLayer zones={visibleZones} kind="reb" />
              </>
            )}
            {/* РЭБ-аномалии: аномальные зоны по данным getRebAnomalies. */}
            {layers.reb_anomaly && rebAnomalyZones.length > 0 && (
              <RebAnomalyLayer zones={rebAnomalyZones} />
            )}
          </MapView>
          {loading && (
            <div
              className="pointer-events-none absolute right-3 top-3 z-[500] inline-flex items-center gap-1.5 rounded-md bg-ink/80 px-2.5 py-1 text-xs text-white"
              role="status"
            >
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
              Загрузка слоя…
            </div>
          )}
        </div>

        {/* Лента активных алярмов. */}
        <div className="flex min-h-0 flex-col">
          <SmartQueryInput
            value={search}
            onChange={setSearch}
            placeholder="Поиск: госномер, водитель, тип, «критичные», «риск>70»"
            className="mb-3"
          />
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-ink">
              Активные алярмы{' '}
              <span className="font-normal tabular-nums text-muted">({activeCount})</span>
            </h2>
            <div className="flex items-center gap-1 text-xs text-muted">
              Сортировка:
              <button
                type="button"
                onClick={() => setSortKey('ts')}
                aria-pressed={sortKey === 'ts'}
                className={cn('px-1', sortKey === 'ts' ? 'font-semibold text-ink' : 'hover:text-ink')}
              >
                время
              </button>
              <span>·</span>
              <button
                type="button"
                onClick={() => setSortKey('risk_score')}
                aria-pressed={sortKey === 'risk_score'}
                className={cn(
                  'px-1',
                  sortKey === 'risk_score' ? 'font-semibold text-ink' : 'hover:text-ink',
                )}
              >
                риск
              </button>
            </div>
          </div>

          <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
            {/* loading: скелет ленты */}
            {loading &&
              Array.from({ length: 4 }).map((_, i) => (
                <div
                  key={i}
                  className="h-[84px] animate-pulse rounded-xl border border-border bg-surface"
                  aria-hidden
                />
              ))}

            {/* error: баннер + повтор (карта при этом не падает) */}
            {!loading && error && (
              <div className="rounded-xl border border-critical-border bg-critical-bg p-4 text-center">
                <p className="text-sm text-critical-text">{error}</p>
                <button
                  type="button"
                  onClick={load}
                  className="mt-2 inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-1.5 text-xs font-medium text-ink hover:border-primary hover:text-primary"
                >
                  <RefreshCw className="h-3.5 w-3.5" aria-hidden />
                  Повторить
                </button>
              </div>
            )}

            {/* empty: роль отфильтровала всё → отдельный текст, иначе — фильтры */}
            {!loading && !error && visible.length === 0 && (
              <p className="py-8 text-center text-sm text-muted">
                {incidents.length > 0 && roleVisible.length === 0
                  ? 'Под выбранную роль событий нет'
                  : 'Нет активных алярмов по фильтрам.'}
              </p>
            )}

            {/* лента */}
            {!loading &&
              !error &&
              visible.map((inc) => {
                const isSelected = selected === inc.vehicle_plate
                const noCoords = !hasCoords(inc)
                return (
                  <div
                    key={inc.id}
                    aria-current={isSelected ? 'true' : undefined}
                    ref={(el) => {
                      // Первая карточка ТС — якорь скролла для onSelect.
                      if (el && !cardRefs.current.has(inc.vehicle_plate)) {
                        cardRefs.current.set(inc.vehicle_plate, el)
                      }
                    }}
                  >
                    <Card
                      variant="incident"
                      severity={inc.severity}
                      onClick={() => navigate(`/incidents/${inc.id}`)}
                      className={cn(isSelected && 'ring-2 ring-primary ring-offset-1')}
                    >
                      {isSelected && (
                        <div className="mb-1 inline-flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-primary">
                          ● Выбрано на карте
                        </div>
                      )}
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-medium text-ink">
                            {inc.alarm_label_ru}
                          </div>
                          <div className="mt-0.5 truncate text-xs text-muted">
                            {inc.vehicle_model} · {inc.vehicle_plate} · {inc.driver}
                          </div>
                        </div>
                        <SeverityBadge severity={inc.severity} label={SEVERITY_LABEL[inc.severity]} />
                      </div>
                      <div className="mt-2 flex items-center justify-between gap-3">
                        <ScoreBar score={inc.risk_score} className="max-w-[160px] flex-1" />
                        <div className="flex shrink-0 items-center gap-2 text-xs text-muted">
                          {noCoords && (
                            <span
                              className="inline-flex items-center gap-1 rounded bg-bg px-1.5 py-0.5"
                              title="Алярм без координат — не отображается на карте"
                            >
                              <MapPinOff className="h-3 w-3" aria-hidden />
                              без координат
                            </span>
                          )}
                          <span className="inline-flex items-center gap-1 tabular-nums">
                            <Clock className="h-3 w-3" aria-hidden />
                            {formatTime(inc.ts)}
                          </span>
                          <span className="rounded bg-bg px-1.5 py-0.5">
                            {SOURCE_LABEL[inc.source]}
                          </span>
                        </div>
                      </div>
                    </Card>
                  </div>
                )
              })}
          </div>
        </div>
      </div>
    </div>
  )
}
