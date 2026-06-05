import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Clock, Loader2, MapPinOff, RefreshCw } from 'lucide-react'
import * as client from '@/api/client'
import type { IncidentSummary, Severity, Source } from '@/api/types'
import { Card, ScoreBar, SeverityBadge } from '@/components'
import { SabotageWidget } from '@/components/SabotageWidget'
import { MapView, MarkerLayer, RoleToggle } from '@/components/map'
import type { MapUnit, Role } from '@/components/map'
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

/** Ранг severity для выбора наихудшего алярма ТС при дедупе. */
const SEVERITY_RANK: Record<Severity, number> = { critical: 4, high: 3, medium: 2, low: 1 }

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

/** Логист видит телематику/ADAS, но не DMS (и COMBINED-по-DMS). §7.8. */
function passesRole(inc: IncidentSummary, role: Role): boolean {
  if (role === 'logist') return inc.source !== 'DMS' && inc.source !== 'COMBINED'
  return true
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
 * Дедуп ленты в `MapUnit[]`: один объект на госномер (= `unit_id` карты).
 * Остаётся наихудший по severity, при равенстве — последний по `ts`. Координаты
 * берём как есть (null → NaN): `MarkerLayer` сам отсеет точки без координат,
 * но в ленте такие алярмы остаются (бейдж «без координат»).
 */
function buildUnits(incidents: IncidentSummary[]): MapUnit[] {
  const byPlate = new Map<string, IncidentSummary>()
  for (const inc of incidents) {
    const prev = byPlate.get(inc.vehicle_plate)
    const better =
      !prev ||
      SEVERITY_RANK[inc.severity] > SEVERITY_RANK[prev.severity] ||
      (SEVERITY_RANK[inc.severity] === SEVERITY_RANK[prev.severity] && inc.ts >= prev.ts)
    if (better) byPlate.set(inc.vehicle_plate, inc)
  }
  return [...byPlate.values()].map((inc) => ({
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

  const [role, setRole] = useState<Role>('dispatcher')
  const [filter, setFilter] = useState<FilterKey>('all')
  const [sortKey, setSortKey] = useState<SortKey>('ts')
  const [selected, setSelected] = useState<string | null>(null)

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

  // Лента: роль + фильтр + сортировка. Показываем ВСЕ алярмы (в т.ч. без координат).
  const visible = useMemo(() => {
    const rows = incidents
      .filter((inc) => passesRole(inc, role))
      .filter((inc) => passesFilter(inc, filter))
    return [...rows].sort((a, b) =>
      sortKey === 'risk_score' ? b.risk_score - a.risk_score : b.ts.localeCompare(a.ts),
    )
  }, [incidents, role, filter, sortKey])

  // Маркеры: дедуп ленты по госномеру (MarkerLayer ещё раз защитит от дублей).
  const units = useMemo(() => buildUnits(visible), [visible])
  const center = useMemo(() => computeCenter(incidents), [incidents])

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

      {/* ── Карта + лента ─────────────────────────────────────────────────── */}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[1fr_minmax(340px,400px)]">
        {/* Карта (рендерится всегда, в т.ч. при пустой/ошибочной ленте). */}
        <div className="relative min-h-[360px] overflow-hidden rounded-xl border border-border">
          <MapView center={center} zoom={DEFAULT_ZOOM}>
            {!loading && !error && <MarkerLayer units={units} onSelect={handleSelect} />}
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

            {/* empty */}
            {!loading && !error && visible.length === 0 && (
              <p className="py-8 text-center text-sm text-muted">Нет активных алярмов по фильтрам.</p>
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
