import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import * as L from 'leaflet'
import { Polyline, useMap } from 'react-leaflet'
import {
  AlertTriangle,
  ArrowLeft,
  RadioTower,
  RotateCcw,
  SatelliteDish,
  VideoOff,
} from 'lucide-react'
import * as client from '@/api/client'
import { ApiError } from '@/api/client'
import type {
  RebGapPeriod,
  RebGpsPoint,
  RebRecovery,
  RebVideoFrame,
} from '@/api/types'
import { MapView, MarkerLayer, type MapUnit } from '@/components/map'
import { Button, Card, VideoPlayer } from '@/components'

/**
 * f11 · РЭБ-восстановление трека (идея #8, §7.4 `GET /api/reb/{id}`, §7.5 `RebRecovery`).
 *
 * При глушении/потере GPS (РЭБ) трек рвётся, но видео продолжает писаться. Экран
 * показывает, что происходило в моменты потери сигнала: на карту (MapView/MarkerLayer d4)
 * накладывается GPS-трек с визуально отличимыми разрывами (`gap_periods`), таймлайн
 * «GPS есть / GPS потерян», и соседние видеокадры момента потери (`video_frames`).
 *
 * Синхронизация: выбор разрыва на таймлайне ↔ подсветка gap-сегмента на карте ↔ маркер ↔
 * видеокадры. Состояния loading / error («Повторить») / 404 / пустые данные — без падения.
 *
 * Границы (зоны прочих треков): маршрут `/reb/:id` в `App.tsx` — зона f1/x2; метод
 * `client.getReb` и фикстуры — зона f2/f3. Этот файл — единственный во владении f11.
 */

// ── Таймзона парка (как в f14): env VITE_PARK_TIMEZONE, иначе UTC ──────────────
const PARK_TZ = (import.meta.env.VITE_PARK_TIMEZONE as string | undefined) ?? 'UTC'

// Центр по умолчанию, когда GPS-точек нет вовсе (Москва) — карта не падает на пустом массиве.
const DEFAULT_CENTER: [number, number] = [55.751, 37.618]

// Цвета слоёв трека = severity-токены d1 (sev-ok / sev-critical), как в map.css.
const TRACK_COLOR = '#16a34a' // GPS есть — сплошная зелёная линия
const GAP_COLOR = '#dc2626' // сигнал потерян — пунктир/полупрозрачная красная линия

// Окно подбора видеокадров вокруг разрыва (мс) — кадры «внутри/рядом» с gap.
const FRAME_PAD_MS = 90_000

// ── Утилиты времени/координат ─────────────────────────────────────────────────

function tsMs(iso: string): number {
  return Date.parse(iso)
}

function hasCoords(p: RebGpsPoint): boolean {
  return Number.isFinite(p.lat) && Number.isFinite(p.lon)
}

function formatClock(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: PARK_TZ,
  })
}

/** «3 мин 0 с» / «45 с» — человекочитаемая длительность разрыва. */
function formatDuration(sec: number): string {
  if (!Number.isFinite(sec) || sec < 0) return '—'
  const m = Math.floor(sec / 60)
  const s = Math.round(sec % 60)
  return m > 0 ? `${m} мин ${s} с` : `${s} с`
}

function humanError(e: unknown): string {
  if (e instanceof ApiError) return e.message
  if (e instanceof Error) return e.message
  return 'Неизвестная ошибка'
}

// ── Производные данные трека ──────────────────────────────────────────────────

interface GapAnchor {
  gi: number
  gap: RebGapPeriod
  /** GPS-позиция, ближайшая к началу разрыва (последняя точка до потери сигнала). */
  anchor: RebGpsPoint | null
}

interface TrackGeometry {
  /** Сплошные участки трека (GPS был) — каждый ≥2 точек. */
  solid: [number, number][][]
  /** Gap-сегменты (пунктир) — между точкой до и после разрыва, привязаны к gi. */
  gaps: { gi: number; positions: [number, number][] }[]
  /** Все валидные позиции — для fitBounds. */
  allPositions: [number, number][]
}

/**
 * Делит отсортированный трек на сплошные участки и gap-сегменты.
 * Ребро (i → i+1) считается разрывом, если между ts двух соседних точек целиком
 * лежит хотя бы один `gap_period` (нет точек во время потери сигнала).
 */
function buildGeometry(sorted: RebGpsPoint[], gaps: RebGapPeriod[]): TrackGeometry {
  const allPositions: [number, number][] = sorted.map((p) => [p.lat, p.lon])

  // edgeIndex → giIndex: ребро после точки `beforeIdx` — это разрыв `gi`.
  const gapEdge = new Map<number, number>()
  gaps.forEach((g, gi) => {
    const startMs = tsMs(g.start)
    let beforeIdx = -1
    for (let i = 0; i < sorted.length; i++) {
      if (tsMs(sorted[i].ts) <= startMs) beforeIdx = i
      else break
    }
    // Разрыв должен лежать между beforeIdx и следующей точкой (есть «после»).
    if (beforeIdx >= 0 && beforeIdx < sorted.length - 1) gapEdge.set(beforeIdx, gi)
  })

  const solid: [number, number][][] = []
  const gapSegs: { gi: number; positions: [number, number][] }[] = []
  let run: [number, number][] = []

  sorted.forEach((p, i) => {
    run.push([p.lat, p.lon])
    const gi = i < sorted.length - 1 ? gapEdge.get(i) : undefined
    if (gi !== undefined) {
      if (run.length >= 2) solid.push(run)
      gapSegs.push({
        gi,
        positions: [
          [p.lat, p.lon],
          [sorted[i + 1].lat, sorted[i + 1].lon],
        ],
      })
      run = []
    }
  })
  if (run.length >= 2) solid.push(run)

  return { solid, gaps: gapSegs, allPositions }
}

/** Якоря разрывов (последняя позиция до потери сигнала) — для маркеров и панели. */
function buildAnchors(sorted: RebGpsPoint[], gaps: RebGapPeriod[]): GapAnchor[] {
  return gaps.map((gap, gi) => {
    const startMs = tsMs(gap.start)
    let anchor: RebGpsPoint | null = null
    for (const p of sorted) {
      if (tsMs(p.ts) <= startMs) anchor = p
      else break
    }
    // Если до разрыва точек нет — берём первую известную (визуальный якорь, не падаем).
    return { gi, gap, anchor: anchor ?? sorted[0] ?? null }
  })
}

// ── Карта: авто-вписывание границ ─────────────────────────────────────────────

function FitBounds({ positions }: { positions: [number, number][] }) {
  const map = useMap()
  useEffect(() => {
    if (positions.length === 0) return
    if (positions.length === 1) {
      map.setView(positions[0], 14)
      return
    }
    map.fitBounds(L.latLngBounds(positions), { padding: [40, 40] })
  }, [map, positions])
  return null
}

// ── Сегментный таймлайн «GPS есть / GPS потерян» ──────────────────────────────

function GapTimeline({
  range,
  gaps,
  selectedGi,
  onSelect,
}: {
  range: { min: number; max: number }
  gaps: RebGapPeriod[]
  selectedGi: number | null
  onSelect: (gi: number) => void
}) {
  const span = Math.max(1, range.max - range.min)
  const pct = (ms: number) => Math.min(100, Math.max(0, ((ms - range.min) / span) * 100))

  return (
    <div className="w-full">
      <div className="mb-2 flex items-center gap-4 text-xs text-muted">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-4 rounded-full" style={{ background: TRACK_COLOR }} aria-hidden />
          GPS есть
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-4 rounded-full" style={{ background: GAP_COLOR }} aria-hidden />
          Сигнал потерян
        </span>
      </div>

      {/* Полоса рейса: зелёная база (GPS есть) + красные overlay-сегменты (потеря). */}
      <div
        className="relative h-6 w-full overflow-hidden rounded-md"
        style={{ background: TRACK_COLOR }}
        role="group"
        aria-label="Таймлайн рейса: периоды наличия и потери GPS"
      >
        {gaps.map((g, gi) => {
          const left = pct(tsMs(g.start))
          const right = pct(tsMs(g.end))
          const width = Math.max(1.5, right - left) // минимум — чтобы короткий разрыв был кликабелен
          const selected = gi === selectedGi
          return (
            <button
              key={`${g.start}-${gi}`}
              type="button"
              onClick={() => onSelect(gi)}
              aria-selected={selected}
              aria-current={selected ? 'true' : undefined}
              aria-label={`Разрыв GPS ${gi + 1}: ${formatClock(g.start)}–${formatClock(g.end)}, ${formatDuration(g.duration_sec)}. Видео есть, GPS нет.`}
              title={`Сигнал потерян · ${formatDuration(g.duration_sec)}`}
              className="absolute top-0 h-full cursor-pointer border-0 outline-none transition-[filter] focus-visible:ring-2 focus-visible:ring-ink"
              style={{
                left: `${left}%`,
                width: `${width}%`,
                background: GAP_COLOR,
                boxShadow: selected ? 'inset 0 0 0 2px #0f172a' : undefined,
                filter: selected ? 'brightness(1.15)' : undefined,
              }}
            />
          )
        })}
      </div>

      <div className="mt-1 flex justify-between text-[11px] tabular-nums text-muted">
        <span>{formatClock(new Date(range.min).toISOString())}</span>
        <span>{formatClock(new Date(range.max).toISOString())}</span>
      </div>
    </div>
  )
}

// ── Видеокадры выбранного разрыва ─────────────────────────────────────────────

function GapVideo({ gap, frames }: { gap: RebGapPeriod; frames: RebVideoFrame[] }) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1.5 rounded-md bg-critical-bg px-2.5 py-1 text-xs font-semibold text-critical-text">
          <SatelliteDish className="h-3.5 w-3.5" aria-hidden />
          Видео есть, GPS нет · {formatDuration(gap.duration_sec)}
        </span>
        <span className="text-xs text-muted tabular-nums">
          {formatClock(gap.start)} – {formatClock(gap.end)}
        </span>
      </div>

      {frames.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-md border border-border bg-bg py-8 text-center text-muted">
          <VideoOff className="h-7 w-7" aria-hidden />
          <p className="text-sm">Видео за момент потери отсутствует</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {frames.map((f, i) => (
            <figure key={`${f.ts}-${f.channel}-${i}`} className="space-y-1.5">
              <VideoPlayer src={f.url} ariaLabel={`Видеокадр, канал ${f.channel}, ${formatClock(f.ts)}`} />
              <figcaption className="flex items-center justify-between text-[11px] text-muted">
                <span className="rounded bg-bg px-1.5 py-0.5 tabular-nums">Канал {f.channel}</span>
                <span className="tabular-nums">{formatClock(f.ts)}</span>
              </figcaption>
            </figure>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Скелетон / ошибка ─────────────────────────────────────────────────────────

function Bar({ className }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-border/60 ${className ?? ''}`} />
}

function ErrorBlock({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <Card className="flex flex-col items-center gap-3 py-10 text-center">
      <AlertTriangle className="h-8 w-8 text-high-text" aria-hidden />
      <p className="max-w-sm text-sm text-muted">{message}</p>
      <Button variant="secondary" icon={RotateCcw} onClick={onRetry}>
        Повторить
      </Button>
    </Card>
  )
}

// ── Экран ─────────────────────────────────────────────────────────────────────

export default function RebRecovery() {
  const { id = '' } = useParams()
  const navigate = useNavigate()

  const [reb, setReb] = useState<RebRecovery | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<{ status?: number; message: string } | null>(null)
  const [selectedGi, setSelectedGi] = useState<number | null>(null)

  const load = useCallback(() => {
    let alive = true
    setLoading(true)
    setError(null)
    setReb(null)
    setSelectedGi(null)
    client
      .getReb(id)
      .then((data) => {
        if (!alive) return
        setReb(data)
        // Авто-выбор первого разрыва — сразу видны видеокадры (Check: клик показывает кадры).
        if (data.gap_periods.length > 0) setSelectedGi(0)
      })
      .catch((e: unknown) => {
        if (!alive) return
        if (e instanceof ApiError) setError({ status: e.status, message: e.message })
        else setError({ message: humanError(e) })
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [id])

  useEffect(() => load(), [load])

  // ── Производные ──────────────────────────────────────────────────────────────
  const sorted = useMemo(
    () =>
      (reb?.gps_track ?? [])
        .filter((p) => hasCoords(p) && !Number.isNaN(tsMs(p.ts)))
        .slice()
        .sort((a, b) => tsMs(a.ts) - tsMs(b.ts)),
    [reb],
  )

  const geometry = useMemo(
    () => buildGeometry(sorted, reb?.gap_periods ?? []),
    [sorted, reb],
  )

  const anchors = useMemo(
    () => buildAnchors(sorted, reb?.gap_periods ?? []),
    [sorted, reb],
  )

  // Диапазон таймлайна = от первой точки/разрыва до последней точки/разрыва.
  const timeRange = useMemo(() => {
    const stamps: number[] = []
    sorted.forEach((p) => stamps.push(tsMs(p.ts)))
    ;(reb?.gap_periods ?? []).forEach((g) => {
      stamps.push(tsMs(g.start), tsMs(g.end))
    })
    const valid = stamps.filter((n) => Number.isFinite(n))
    if (valid.length === 0) return null
    return { min: Math.min(...valid), max: Math.max(...valid) }
  }, [sorted, reb])

  // Маркеры разрывов как MapUnit (d4 MarkerLayer): один маркер на разрыв, в якорной позиции.
  // severity=high (потеря — высокая значимость), online=false (сигнал потерян → серое кольцо).
  const gapUnits = useMemo<MapUnit[]>(
    () =>
      anchors
        .filter((a): a is GapAnchor & { anchor: RebGpsPoint } => a.anchor !== null)
        .map((a) => ({
          unit_id: `gap-${a.gi}`,
          vehicle_plate: reb?.vehicle_plate ?? '—',
          lat: a.anchor.lat,
          lon: a.anchor.lon,
          severity: 'high',
          online: false,
          last_alarm: null,
        })),
    [anchors, reb],
  )

  // Видеокадры выбранного разрыва: внутри/рядом с окном, иначе — ближайший кадр.
  const selectedFrames = useMemo<RebVideoFrame[]>(() => {
    if (selectedGi == null || !reb) return []
    const gap = reb.gap_periods[selectedGi]
    if (!gap) return []
    const lo = tsMs(gap.start) - FRAME_PAD_MS
    const hi = tsMs(gap.end) + FRAME_PAD_MS
    const within = reb.video_frames
      .filter((f) => {
        const t = tsMs(f.ts)
        return Number.isFinite(t) && t >= lo && t <= hi
      })
      .sort((a, b) => tsMs(a.ts) - tsMs(b.ts))
    if (within.length > 0) return within
    if (reb.video_frames.length === 0) return []
    const nearest = reb.video_frames
      .slice()
      .sort(
        (a, b) =>
          Math.abs(tsMs(a.ts) - tsMs(gap.start)) - Math.abs(tsMs(b.ts) - tsMs(gap.start)),
      )[0]
    return nearest ? [nearest] : []
  }, [selectedGi, reb])

  const selectGapByUnit = useCallback((unitId: string) => {
    const gi = Number.parseInt(unitId.replace('gap-', ''), 10)
    if (Number.isFinite(gi)) setSelectedGi(gi)
  }, [])

  // ── Loading ───────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="mx-auto max-w-5xl space-y-4" aria-busy="true" aria-label="Загрузка восстановления трека">
        <Card>
          <Bar className="h-6 w-56" />
          <Bar className="mt-2 h-4 w-72" />
        </Card>
        <Card>
          <Bar className="h-[360px] w-full" />
        </Card>
        <Card>
          <Bar className="h-10 w-full" />
        </Card>
      </div>
    )
  }

  // ── Error / 404 ────────────────────────────────────────────────────────────────
  if (error || !reb) {
    const is404 = error?.status === 404
    return (
      <div className="grid h-full place-items-center">
        <Card className="max-w-md text-center">
          <AlertTriangle className="mx-auto h-8 w-8 text-high-text" aria-hidden />
          <h2 className="mt-3 text-lg font-semibold text-ink">
            {is404 ? 'Рейс не найден' : 'Ошибка загрузки'}
          </h2>
          <p className="mt-1 text-sm text-muted">
            {is404 ? `Рейс «${id}» не существует.` : (error?.message ?? 'Не удалось загрузить данные.')}
          </p>
          <div className="mt-4 flex justify-center gap-2">
            {!is404 && (
              <Button variant="secondary" icon={RotateCcw} onClick={load}>
                Повторить
              </Button>
            )}
            <Button variant="secondary" icon={ArrowLeft} onClick={() => navigate('/monitor')}>
              К мониторингу
            </Button>
          </div>
        </Card>
      </div>
    )
  }

  const totalGapSec = reb.gap_periods.reduce((s, g) => s + (g.duration_sec || 0), 0)
  const hasGaps = reb.gap_periods.length > 0
  const hasTrack = sorted.length > 0
  const mapCenter: [number, number] = hasTrack ? [sorted[0].lat, sorted[0].lon] : DEFAULT_CENTER
  const selectedGap = selectedGi != null ? reb.gap_periods[selectedGi] : null

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      {/* ── Шапка ───────────────────────────────────────────────────────────────── */}
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <RadioTower className="h-5 w-5 text-primary" aria-hidden />
            <h1 className="text-lg font-semibold text-ink">
              РЭБ-восстановление трека · {reb.vehicle_plate}
            </h1>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <div className="text-right">
              <div className="text-[11px] uppercase tracking-wide text-muted">Разрывов GPS</div>
              <div className="text-base font-bold tabular-nums text-ink">{reb.gap_periods.length}</div>
            </div>
            <div className="text-right">
              <div className="text-[11px] uppercase tracking-wide text-muted">Суммарно потеряно</div>
              <div className="text-base font-bold tabular-nums text-critical-text">
                {formatDuration(totalGapSec)}
              </div>
            </div>
          </div>
        </div>
        <p className="mt-1 text-sm text-muted">
          При глушении GPS трек рвётся, но видео продолжает писаться — ниже наложены имеющийся
          трек с разрывами и видеокадры момента потери сигнала.
        </p>
      </Card>

      {/* ── Карта: трек с разрывами + маркеры разрывов ──────────────────────────── */}
      <Card className="p-0">
        <div className="h-[360px] w-full overflow-hidden rounded-md" aria-label="Карта трека с разрывами GPS">
          <MapView center={mapCenter} zoom={12}>
            {/* Сплошные участки — GPS был. */}
            {geometry.solid.map((positions, i) => (
              <Polyline
                key={`solid-${i}`}
                positions={positions}
                pathOptions={{ color: TRACK_COLOR, weight: 4, opacity: 0.9 }}
              />
            ))}
            {/* Gap-сегменты — пунктир/полупрозрачные; выбранный разрыв подсвечен. */}
            {geometry.gaps.map(({ gi, positions }) => {
              const selected = gi === selectedGi
              return (
                <Polyline
                  key={`gap-${gi}`}
                  positions={positions}
                  pathOptions={{
                    color: GAP_COLOR,
                    weight: selected ? 5 : 3,
                    opacity: selected ? 1 : 0.6,
                    dashArray: '6 8',
                  }}
                />
              )
            })}
            {gapUnits.length > 0 && <MarkerLayer units={gapUnits} onSelect={selectGapByUnit} />}
            <FitBounds positions={geometry.allPositions} />
          </MapView>
        </div>
        {!hasTrack && (
          <div className="border-t border-border px-4 py-3 text-center text-sm text-muted">
            Нет GPS-данных по рейсу
          </div>
        )}
      </Card>

      {/* ── Таймлайн «GPS есть / потерян» ───────────────────────────────────────── */}
      <Card>
        <h2 className="mb-3 text-sm font-semibold text-ink">Таймлайн сигнала GPS</h2>
        {hasGaps && timeRange ? (
          <GapTimeline
            range={timeRange}
            gaps={reb.gap_periods}
            selectedGi={selectedGi}
            onSelect={setSelectedGi}
          />
        ) : (
          <div className="flex flex-col items-center gap-2 py-8 text-center text-muted">
            <SatelliteDish className="h-7 w-7" aria-hidden />
            <p className="text-sm">Разрывов GPS не найдено — трек непрерывный</p>
          </div>
        )}
      </Card>

      {/* ── Видеокадры выбранного разрыва ───────────────────────────────────────── */}
      {hasGaps && (
        <Card>
          <h2 className="mb-3 text-sm font-semibold text-ink">
            Видеокадры момента потери
            {selectedGap && (
              <span className="ml-2 font-normal text-muted">
                — разрыв {(selectedGi ?? 0) + 1} из {reb.gap_periods.length}
              </span>
            )}
          </h2>
          {selectedGap ? (
            <GapVideo gap={selectedGap} frames={selectedFrames} />
          ) : (
            <p className="py-6 text-center text-sm text-muted">
              Выберите разрыв на таймлайне или маркер на карте, чтобы увидеть видеокадры.
            </p>
          )}
        </Card>
      )}
    </div>
  )
}
