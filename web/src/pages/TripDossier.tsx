import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Polyline, useMap } from 'react-leaflet'
import type { LatLngBoundsExpression, LatLngExpression } from 'leaflet'
import { AlertTriangle, ArrowLeft, RouteOff, Video, VideoOff } from 'lucide-react'
import * as client from '@/api/client'
import { ApiError } from '@/api/client'
import type {
  Severity,
  TelemetryPoint,
  TripDossier as TripDossierData,
  TripTimelineEntry,
  VideoChannel,
} from '@/api/types'
import {
  Button,
  Card,
  SeverityBadge,
  TelemetryChart,
  Timeline,
  VideoPlayer,
} from '@/components'
import type { TimelineEvent } from '@/components'
import { MapView, MarkerLayer } from '@/components/map'
import type { MapUnit } from '@/components/map'
import { cn } from '@/components/ui/cn'

/**
 * f10 · Видеодосье рейса (идея #7). Единое полотно расследования рейса:
 * маршрут ТС на карте (d4) + хронология событий (Timeline d5) + график скорости
 * (TelemetryChart d2) + видео выбранного момента (VideoPlayer d2). Один
 * `selectedOffset` синхронизирует карту ↔ таймлайн ↔ график ↔ видео.
 *
 * Контракт §7.4 (`GET /api/trips/{id}`), §7.5 (`TripDossier`), §7.8 (AC «Видеодосье»).
 *
 * NB: §7.5 `TelemetryPoint` не несёт координат (`lat/lon`), а `TripTimelineEntry`
 * не несёт `severity`. Поэтому маршрут на карте строим из последовательности точек
 * (детерминированная синтетика — до уточнения с b13), а severity события выводим
 * из `alarm_code` (gross-маппинг §7.5). Это явно отмечено в промпте f10.
 */

// ── Каналы видео: ADAS (ch1) по умолчанию, переключатель на DMS (ch5) (§7.4) ───
const ADAS_CHANNEL: VideoChannel = 1
const DMS_CHANNEL: VideoChannel = 5

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: 'Критично',
  high: 'Высокий',
  medium: 'Средний',
  low: 'Низкий',
}

/**
 * severity события из `alarm_code` (схема §7.5 не несёт severity на событие).
 * Маппинг согласован с gross-логикой §7.5 / фикстурами f3. Неизвестный → medium.
 */
const SEVERITY_BY_CODE: Record<string, Severity> = {
  DMS_DROWSY: 'critical',
  CRASH_SENSOR: 'critical',
  DRIVER_SUBSTITUTION: 'medium',
  DMS_PHONE: 'high',
  OVERSPEED: 'high',
  HARSH_BRAKING: 'high',
  HARSH_ACCELERATION: 'medium',
  HARSH_CORNERING: 'medium',
  DMS_SMOKING: 'medium',
  DMS_SEATBELT: 'low',
}

/** severity события: t=0 всегда critical (§7.6), иначе — по alarm_code. */
function eventSeverity(e: TripTimelineEntry): Severity {
  if (e.ts_offset === 0) return 'critical'
  return SEVERITY_BY_CODE[e.alarm_code] ?? 'medium'
}

// ── Форматтеры времени рейса (относительные секунды, без Date.now()) ──────────

/** Смещение события: «t=0» · «+12 с» · «−3 с» (минус — типографский). */
function formatOffset(s: number): string {
  if (s === 0) return 't=0'
  return `${s > 0 ? '+' : '−'}${Math.abs(s)} с`
}

/** Длительность рейса в секундах → «N мин M с» / «M с». */
function formatDuration(sec: number): string {
  const total = Math.max(0, Math.round(sec))
  const m = Math.floor(total / 60)
  const s = total % 60
  return m > 0 ? `${m} мин ${s} с` : `${s} с`
}

// ── Синтетический маршрут (нет координат в §7.5 TelemetryPoint) ────────────────
// Детерминированная кривая вокруг базовой точки — только для визуализации трека.
const TRIP_CENTER: [number, number] = [55.751244, 37.618423]

function synthCoords(track: TelemetryPoint[]): [number, number][] {
  return track.map((_, i) => [
    TRIP_CENTER[0] + i * 0.0009 + Math.sin(i * 0.55) * 0.0011,
    TRIP_CENTER[1] + i * 0.0013 + Math.cos(i * 0.5) * 0.0009,
  ])
}

/** Индекс точки трека, ближайшей по ts_offset к заданному смещению. */
function nearestTrackIndex(track: TelemetryPoint[], offset: number): number {
  let best = 0
  for (let i = 1; i < track.length; i++) {
    if (Math.abs(track[i].ts_offset - offset) < Math.abs(track[best].ts_offset - offset)) {
      best = i
    }
  }
  return best
}

/** Событие, ближайшее по ts_offset к заданному смещению (для клика по графику/треку). */
function nearestEvent(
  events: TripTimelineEntry[],
  offset: number,
): TripTimelineEntry | null {
  if (events.length === 0) return null
  return events.reduce((best, e) =>
    Math.abs(e.ts_offset - offset) < Math.abs(best.ts_offset - offset) ? e : best,
  )
}

const clamp01 = (v: number) => Math.min(1, Math.max(0, v))

// ── Карта: подгон границ под трек ─────────────────────────────────────────────

function FitTrack({ coords }: { coords: [number, number][] }) {
  const map = useMap()
  useEffect(() => {
    if (coords.length === 0) return
    if (coords.length === 1) {
      map.setView(coords[0], 14)
      return
    }
    map.fitBounds(coords as LatLngBoundsExpression, { padding: [40, 40] })
  }, [coords, map])
  return null
}

function SkeletonBox({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded bg-border', className)} />
}

// ── Экран ─────────────────────────────────────────────────────────────────────

export default function TripDossier() {
  const { id = '' } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [trip, setTrip] = useState<TripDossierData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<{ status?: number; message: string } | null>(null)

  // Единый «выбранный момент» — синхронизирует карту ↔ таймлайн ↔ график ↔ видео.
  const [selectedOffset, setSelectedOffset] = useState<number | null>(null)
  // Канал видео: ADAS (ch1) по умолчанию, переключатель на DMS (ch5).
  const [channel, setChannel] = useState<VideoChannel>(ADAS_CHANNEL)

  const chartBoxRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError(null)
    setTrip(null)
    setSelectedOffset(null)
    client
      .getTrip(id)
      .then((data) => {
        if (!alive) return
        setTrip(data)
        // Авто-выбор: критический момент t=0, иначе первое событие.
        const zero = data.timeline.find((e) => e.ts_offset === 0)
        const first = data.timeline[0]
        setSelectedOffset(zero?.ts_offset ?? first?.ts_offset ?? null)
      })
      .catch((e: unknown) => {
        if (!alive) return
        if (e instanceof ApiError) setError({ status: e.status, message: e.message })
        else setError({ message: e instanceof Error ? e.message : 'Неизвестная ошибка' })
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [id])

  const track = trip?.track ?? []
  const timeline = trip?.timeline ?? []

  const coords = useMemo(() => synthCoords(track), [track])

  // Диапазон трека по ts_offset (для графика и подписи рейса).
  const span = useMemo(() => {
    const offsets = track.map((p) => p.ts_offset)
    const min = offsets.length ? Math.min(...offsets) : 0
    const max = offsets.length ? Math.max(...offsets) : 0
    return { min, max, range: max - min }
  }, [track])

  // Маркеры событий на карте (переиспользуем MarkerLayer d4: цвет по severity).
  const eventUnits = useMemo<MapUnit[]>(
    () =>
      timeline.map((e, i) => {
        const idx = track.length ? nearestTrackIndex(track, e.ts_offset) : 0
        const coord = coords[idx] ?? TRIP_CENTER
        return {
          unit_id: `evt-${i}`,
          vehicle_plate: trip?.vehicle_plate ?? '—',
          lat: coord[0],
          lon: coord[1],
          severity: eventSeverity(e),
          online: true,
          last_alarm: null,
        }
      }),
    [timeline, track, coords, trip],
  )

  // События для таймлайна d5 (с выведенным severity).
  const timelineEvents = useMemo<TimelineEvent[]>(
    () =>
      timeline.map((e) => ({
        ts_offset: e.ts_offset,
        alarm_code: e.alarm_code,
        label: e.label,
        severity: eventSeverity(e),
        has_video: e.has_video,
      })),
    [timeline],
  )

  const selectedEvent = useMemo(
    () => timeline.find((e) => e.ts_offset === selectedOffset) ?? null,
    [timeline, selectedOffset],
  )

  // Клик по маркеру карты → выбрать соответствующее событие.
  const handleMarkerSelect = useCallback(
    (unitId: string) => {
      const i = Number(unitId.replace('evt-', ''))
      const e = timeline[i]
      if (e) setSelectedOffset(e.ts_offset)
    },
    [timeline],
  )

  // Клик по графику → ближайшее событие (синхронизация выбора).
  const handleChartSeek = useCallback(
    (ev: React.MouseEvent<HTMLDivElement>) => {
      const box = chartBoxRef.current
      if (!box || span.range === 0) return
      const rect = box.getBoundingClientRect()
      const ratio = clamp01((ev.clientX - rect.left) / rect.width)
      const offset = span.min + ratio * span.range
      const target = nearestEvent(timeline, offset)
      if (target) setSelectedOffset(target.ts_offset)
    },
    [span, timeline],
  )

  const mapCenter: [number, number] =
    coords[Math.floor(coords.length / 2)] ?? TRIP_CENTER

  // ── Loading: скелетоны панелей ───────────────────────────────────────────────
  if (loading) {
    return (
      <div className="mx-auto max-w-6xl space-y-4" aria-busy="true" aria-label="Загрузка рейса">
        <Card>
          <div className="flex flex-wrap items-center gap-3">
            <SkeletonBox className="h-7 w-40" />
            <SkeletonBox className="h-5 w-32" />
            <SkeletonBox className="h-5 w-24" />
          </div>
        </Card>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="space-y-4">
            <Card><SkeletonBox className="h-72" /></Card>
            <Card><SkeletonBox className="h-32" /></Card>
          </div>
          <div className="space-y-4">
            <Card><SkeletonBox className="aspect-video" /></Card>
            <Card><SkeletonBox className="h-60" /></Card>
          </div>
        </div>
      </div>
    )
  }

  // ── Error / 404 «Рейс не найден» ─────────────────────────────────────────────
  if (error || !trip) {
    const is404 = error?.status === 404
    return (
      <div className="grid h-full place-items-center">
        <Card className="max-w-md text-center">
          <AlertTriangle className="mx-auto h-8 w-8 text-high" aria-hidden />
          <h2 className="mt-3 text-lg font-semibold text-ink">
            {is404 ? 'Рейс не найден' : 'Ошибка загрузки'}
          </h2>
          <p className="mt-1 text-sm text-muted">
            {is404 ? `Рейс «${id}» не существует.` : error?.message}
          </p>
          <Button
            variant="secondary"
            icon={ArrowLeft}
            onClick={() => navigate(-1)}
            className="mx-auto mt-4"
          >
            Назад
          </Button>
        </Card>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      {/* ── Шапка рейса ──────────────────────────────────────────────────────── */}
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-baseline gap-3">
            <h1 className="text-xl font-semibold tracking-tight text-ink">
              Видеодосье рейса
            </h1>
            <span className="rounded-md bg-bg px-2 py-0.5 text-sm font-medium tabular-nums text-ink">
              {trip.vehicle_plate}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-4 text-sm text-muted">
            <span>
              Длительность:{' '}
              <span className="font-medium tabular-nums text-ink">
                {track.length ? formatDuration(span.range) : '—'}
              </span>
            </span>
            <span>
              Диапазон:{' '}
              <span className="font-medium tabular-nums text-ink">
                {track.length ? `${formatOffset(span.min)} … ${formatOffset(span.max)}` : '—'}
              </span>
            </span>
            <span>
              Событий:{' '}
              <span className="font-medium tabular-nums text-ink">{timeline.length}</span>
            </span>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* ── Левая колонка: карта + таймлайн ───────────────────────────────── */}
        <div className="space-y-4">
          <Card>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
              Маршрут рейса
            </h2>
            {track.length === 0 ? (
              <div className="flex h-72 flex-col items-center justify-center gap-2 rounded-md border border-dashed border-border bg-bg text-center">
                <RouteOff className="h-8 w-8 text-muted" aria-hidden />
                <span className="text-sm text-muted">Трек недоступен</span>
              </div>
            ) : (
              <div className="h-72 overflow-hidden rounded-md">
                <MapView center={mapCenter} zoom={13}>
                  <Polyline
                    positions={coords as LatLngExpression[]}
                    pathOptions={{ color: '#1E3A8A', weight: 4, opacity: 0.9 }}
                  />
                  <MarkerLayer units={eventUnits} onSelect={handleMarkerSelect} />
                  <FitTrack coords={coords} />
                </MapView>
              </div>
            )}
            <p className="mt-2 text-xs text-muted">
              Линия — маршрут ТС, маркеры — события (цвет по severity). Клик по маркеру
              выбирает момент.
            </p>
          </Card>

          <Card>
            <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-muted">
              Хронология событий
            </h2>
            {timeline.length === 0 ? (
              <div className="flex h-24 items-center justify-center rounded-md border border-dashed border-border bg-bg">
                <span className="text-sm text-muted">Событий рейса нет</span>
              </div>
            ) : (
              <>
                {/* Визуальный скраббер d5: точки = severity, t=0 — critical, playhead = выбор. */}
                <Timeline
                  events={timelineEvents}
                  onSelect={(e) => setSelectedOffset(e.ts_offset)}
                  playheadOffset={selectedOffset ?? undefined}
                />
                {/* Доступный список событий (клавиатура + aria-current/selected). */}
                <ul role="list" className="mt-2 flex flex-col gap-1">
                  {timeline.map((e, i) => {
                    const sev = eventSeverity(e)
                    const selected = e.ts_offset === selectedOffset
                    return (
                      <li key={`${e.alarm_code}-${e.ts_offset}-${i}`} role="listitem">
                        <button
                          type="button"
                          onClick={() => setSelectedOffset(e.ts_offset)}
                          aria-current={selected ? 'true' : undefined}
                          aria-selected={selected}
                          className={cn(
                            'flex w-full items-center gap-3 rounded-md border px-3 py-2 text-left text-sm transition-colors',
                            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
                            selected
                              ? 'border-primary bg-primary-50'
                              : 'border-transparent hover:bg-bg',
                          )}
                        >
                          <SeverityBadge severity={sev} label={SEVERITY_LABEL[sev]} />
                          <span className="min-w-0 flex-1 truncate text-ink">{e.label}</span>
                          {e.has_video ? (
                            <span className="inline-flex shrink-0 items-center gap-1 text-xs text-muted">
                              <Video size={13} aria-hidden /> видео
                            </span>
                          ) : (
                            <span className="shrink-0 text-xs text-muted">без видео</span>
                          )}
                          <span className="shrink-0 tabular-nums text-xs text-muted">
                            {formatOffset(e.ts_offset)}
                          </span>
                        </button>
                      </li>
                    )
                  })}
                </ul>
              </>
            )}
          </Card>
        </div>

        {/* ── Правая колонка: видео + график ─────────────────────────────────── */}
        <div className="space-y-4">
          <Card>
            <div className="mb-3 flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
                Видео момента
              </h2>
              {/* Переключатель ADAS / DMS — меняет channel в videoUrl. */}
              <div className="flex gap-1" role="group" aria-label="Канал видео">
                {(
                  [
                    { ch: ADAS_CHANNEL, label: 'ADAS' },
                    { ch: DMS_CHANNEL, label: 'DMS' },
                  ] as const
                ).map(({ ch, label }) => (
                  <button
                    key={ch}
                    type="button"
                    onClick={() => setChannel(ch)}
                    aria-pressed={channel === ch}
                    className={cn(
                      'rounded px-2.5 py-1 text-xs font-medium transition-colors',
                      channel === ch
                        ? 'bg-primary text-white'
                        : 'bg-primary/10 text-primary hover:bg-primary/20',
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {!selectedEvent ? (
              <div className="flex aspect-video flex-col items-center justify-center gap-2 rounded-md border border-dashed border-border bg-bg text-center">
                <Video className="h-8 w-8 text-muted" aria-hidden />
                <span className="text-sm text-muted">Выберите событие на таймлайне</span>
              </div>
            ) : selectedEvent.has_video ? (
              <VideoPlayer
                src={client.videoUrl(id, channel)}
                ariaLabel={`Видео момента: ${selectedEvent.label}, канал ${
                  channel === ADAS_CHANNEL ? 'ADAS' : 'DMS'
                }`}
              />
            ) : (
              <div className="flex aspect-video flex-col items-center justify-center gap-2 rounded-md border border-dashed border-border bg-bg text-center">
                <VideoOff className="h-8 w-8 text-muted" aria-hidden />
                <div className="text-sm font-medium text-ink">Видео недоступно</div>
                <p className="max-w-xs text-xs text-muted">
                  Для события «{selectedEvent.label}» запись не передана в архив.
                </p>
              </div>
            )}

            {selectedEvent && (
              <div className="mt-2 flex items-center gap-2 text-xs text-muted">
                <span className="tabular-nums">{formatOffset(selectedEvent.ts_offset)}</span>
                <span>·</span>
                <span className="truncate">{selectedEvent.label}</span>
              </div>
            )}
          </Card>

          <Card>
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
                Скорость за рейс
              </h2>
              {track.length > 0 && (
                <span className="text-xs text-muted">клик по графику — выбор момента</span>
              )}
            </div>
            {track.length === 0 ? (
              <div className="flex h-60 items-center justify-center rounded-md border border-dashed border-border bg-bg">
                <span className="text-sm text-muted">Трек недоступен</span>
              </div>
            ) : (
              <>
                <div
                  ref={chartBoxRef}
                  onClick={handleChartSeek}
                  className="cursor-crosshair"
                  role="img"
                  aria-label={`График скорости за рейс: ${track.length} точек, диапазон ${formatOffset(
                    span.min,
                  )}…${formatOffset(span.max)}. Синяя вертикаль — выбранный момент.`}
                >
                  <TelemetryChart
                    data={track}
                    playheadOffset={selectedOffset ?? undefined}
                  />
                </div>
                <p className="mt-2 text-xs text-muted">
                  Жёлтая пунктирная вертикаль — t=0. Синяя — выбранный момент.
                </p>
              </>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
