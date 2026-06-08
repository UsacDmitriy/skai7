import { useEffect, useMemo, useState } from 'react'
import { ArrowLeft, Gauge, MapPin, Satellite, TriangleAlert } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import { Card } from '@/components'
import { getSensors } from '@/api/client'
import { ApiError } from '@/api/client'
import type { SensorDailyPoint, SensorOnlineStatus, SensorVehicleCard } from '@/api/types'
import { cn } from '@/components/ui/cn'

/**
 * w3-11 · Карточка сенсоров ТС (`/fleet-health/sensors/:plate`). Против §9.2/§9.4.
 *
 * `getSensors(plate)`: KPI разрыва CAN−GPS, спарклайн дневного пробега (7 точек —
 * НЕ сырые 959k graph_points), блоки двигателя/уровня топлива/снимка. `stale` →
 * нейтральный бейдж (не ошибка, §9.5); `distance_gap=null` → «нет данных». 404 →
 * «ТС не найдено».
 */

const PARK_TZ = (import.meta.env.VITE_PARK_TIMEZONE as string | undefined) ?? 'UTC'

function formatDateTime(iso: string | null): string {
  if (!iso) return 'нет данных'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: PARK_TZ,
  })
}

function fmtKm(n: number): string {
  return `${n.toLocaleString('ru-RU', { maximumFractionDigits: 1 })} км`
}

// ── online-бейдж: stale нейтрален, не ошибка (§9.5) ───────────────────────────

const ONLINE: Record<SensorOnlineStatus, { dot: string; chip: string; label: string }> = {
  online: { dot: 'bg-ok', chip: 'bg-ok-bg text-ok-text', label: 'Online' },
  stale: {
    dot: 'bg-warning',
    chip: 'bg-bg text-muted ring-1 ring-border',
    label: 'Stale · нет свежих нав-данных',
  },
  offline: { dot: 'bg-muted', chip: 'bg-bg text-muted ring-1 ring-border', label: 'Offline' },
}

function OnlineBadge({ status }: { status: SensorOnlineStatus }) {
  const { dot, chip, label } = ONLINE[status]
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-xl px-2 py-0.5 text-xs font-medium',
        chip,
      )}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', dot)} aria-hidden />
      {label}
    </span>
  )
}

// ── Спарклайн дневного пробега (7 точек, §9.2 — не сырые graph_points) ─────────

function Sparkline({ points }: { points: SensorDailyPoint[] }) {
  const geom = useMemo(() => {
    const W = 320
    const H = 64
    const P = 6
    const values = points.map((p) => p.distance_km)
    const max = Math.max(...values, 1)
    const min = Math.min(...values, 0)
    const range = max - min || 1
    const stepX = points.length > 1 ? (W - P * 2) / (points.length - 1) : 0
    const coords = values.map((v, i) => {
      const x = P + i * stepX
      const y = P + (1 - (v - min) / range) * (H - P * 2)
      return [x, y] as const
    })
    const line = coords
      .map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`)
      .join(' ')
    const area = `${line} L${(P + (points.length - 1) * stepX).toFixed(1)},${(H - P).toFixed(1)} L${P.toFixed(1)},${(H - P).toFixed(1)} Z`
    return { W, H, coords, line, area }
  }, [points])

  if (points.length === 0) {
    return <div className="text-sm text-muted">Нет дневного пробега</div>
  }

  const total = points.reduce((s, p) => s + p.distance_km, 0)
  const label = `Дневной пробег за ${points.length} дн.: ${points
    .map((p) => `${p.date} ${Math.round(p.distance_km)} км`)
    .join(', ')}`

  return (
    <div className="space-y-1">
      <svg
        viewBox={`0 0 ${geom.W} ${geom.H}`}
        className="h-16 w-full"
        preserveAspectRatio="none"
        role="img"
        aria-label={label}
      >
        <path d={geom.area} fill="rgb(30 58 138 / 0.08)" />
        <path
          d={geom.line}
          fill="none"
          stroke="#1E3A8A"
          strokeWidth={1.75}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {geom.coords.map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r={2} fill="#1E3A8A" />
        ))}
      </svg>
      <div className="flex justify-between text-xs tabular-nums text-muted">
        <span>{points[0].date}</span>
        <span>Σ {fmtKm(total)}</span>
        <span>{points[points.length - 1].date}</span>
      </div>
    </div>
  )
}

// ── KPI / поле «ключ-значение» ────────────────────────────────────────────────

function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="flex min-w-[120px] flex-col gap-0.5">
      <span className="text-xs uppercase tracking-wide text-muted">{label}</span>
      <span className="text-lg font-semibold tabular-nums text-ink">{value}</span>
      {hint ? <span className="text-xs text-muted">{hint}</span> : null}
    </div>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-border py-1.5 last:border-b-0">
      <span className="text-sm text-muted">{label}</span>
      <span className="text-sm tabular-nums text-ink">{value}</span>
    </div>
  )
}

// ── Состояние загрузки ────────────────────────────────────────────────────────

function CardSkeleton() {
  return (
    <div
      className="mx-auto max-w-5xl space-y-4"
      aria-busy="true"
      aria-label="Загрузка карточки сенсоров"
    >
      <Card>
        <div className="flex flex-wrap gap-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-12 w-28 animate-pulse rounded bg-border/60" />
          ))}
        </div>
      </Card>
      <Card>
        <div className="h-32 animate-pulse rounded bg-border/60" />
      </Card>
    </div>
  )
}

// ── Экран ─────────────────────────────────────────────────────────────────────

export default function SensorCard() {
  const { plate = '' } = useParams<{ plate: string }>()
  const navigate = useNavigate()
  const [card, setCard] = useState<SensorVehicleCard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<{ status?: number; message: string } | null>(null)

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError(null)
    setCard(null)
    getSensors(plate)
      .then((data) => {
        if (alive) setCard(data)
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
  }, [plate])

  if (loading) return <CardSkeleton />

  if (error || !card) {
    const is404 = error?.status === 404
    return (
      <div className="grid h-full place-items-center">
        <Card className="max-w-md text-center">
          <TriangleAlert className="mx-auto h-8 w-8 text-high" aria-hidden />
          <h2 className="mt-3 text-lg font-semibold text-ink">
            {is404 ? 'ТС не найдено' : 'Ошибка загрузки'}
          </h2>
          <p className="mt-1 text-sm text-muted">
            {is404 ? `Сенсорные данные для «${plate}» отсутствуют.` : error?.message}
          </p>
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="mx-auto mt-4 inline-flex items-center gap-2 rounded-md border border-border bg-surface px-4 py-2 text-sm font-medium text-ink hover:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <ArrowLeft size={16} aria-hidden /> Назад
          </button>
        </Card>
      </div>
    )
  }

  const gap = card.distance_gap_odometer_minus_gps_km

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <header className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-surface text-muted hover:border-primary hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          aria-label="Назад"
        >
          <ArrowLeft size={16} aria-hidden />
        </button>
        <Gauge className="h-5 w-5 text-primary" aria-hidden />
        <h1 className="text-lg font-bold text-ink">Сенсоры · {card.plate ?? card.vehicle_label}</h1>
        <OnlineBadge status={card.online_status} />
      </header>

      {/* KPI: разрыв CAN−GPS (null → «нет данных») + пробеги/скорости/спутники */}
      <Card>
        <div className="flex flex-wrap gap-x-8 gap-y-3">
          <Kpi
            label="Разрыв CAN − GPS"
            value={gap == null ? 'нет данных' : fmtKm(gap)}
            hint="одометр − GPS"
          />
          <Kpi label="Пробег по GPS" value={fmtKm(card.gps_total_distance_km)} />
          <Kpi label="Пробег по одометру" value={fmtKm(card.distance_odometer_km)} />
          <Kpi
            label="Скорость макс / ср"
            value={`${Math.round(card.max_speed_kmh)} / ${Math.round(card.average_speed_kmh)} км/ч`}
          />
          <Kpi
            label="Спутники"
            value={String(card.satellite_amount)}
            hint={`датчиков: ${card.sensor_count}`}
          />
        </div>
      </Card>

      {/* Спарклайн дневного пробега (7 точек) */}
      <Card>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
          Дневной пробег
        </h2>
        <Sparkline points={card.daily_mileage} />
      </Card>

      {/* Блоки: двигатель · уровень топлива · последний снимок */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted">
            Двигатель
          </h2>
          <Field label="Первый запуск" value={formatDateTime(card.engine.first_ignition_on)} />
          <Field
            label="Последняя остановка"
            value={formatDateTime(card.engine.last_ignition_off)}
          />
          <Field label="Время работы" value={card.engine.ignition_duration} />
          <Field label="Холостой ход" value={card.engine.idle_duration} />
        </Card>

        <Card>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted">
            Уровень топлива
          </h2>
          <Field
            label="На начало"
            value={`${card.fuel_level.first_fuel_level.toLocaleString('ru-RU', { maximumFractionDigits: 1 })} л`}
          />
          <Field
            label="На конец"
            value={`${card.fuel_level.last_fuel_level.toLocaleString('ru-RU', { maximumFractionDigits: 1 })} л`}
          />
          <Field
            label="Δ за период"
            value={`${card.fuel_level.delta_fuel_level < 0 ? '−' : '+'}${Math.abs(card.fuel_level.delta_fuel_level).toLocaleString('ru-RU', { maximumFractionDigits: 1 })} л`}
          />
        </Card>

        <Card>
          <h2 className="mb-2 flex items-center gap-1.5 text-sm font-semibold uppercase tracking-wide text-muted">
            <Satellite size={14} aria-hidden /> Последний снимок
          </h2>
          <Field label="Время" value={formatDateTime(card.snapshot.timestamp_utc)} />
          <Field
            label="Свежие нав-данные"
            value={formatDateTime(card.snapshot.last_valid_navigation_timestamp)}
          />
          <Field label="Скорость" value={`${Math.round(card.snapshot.speed_kmh)} км/ч`} />
          <Field
            label="Топливо"
            value={`${card.snapshot.fuel_volume.toLocaleString('ru-RU', { maximumFractionDigits: 1 })} л`}
          />
          <Field label="Одометр" value={fmtKm(card.snapshot.odometer_mileage)} />
          <div className="flex items-baseline justify-between gap-3 py-1.5">
            <span className="inline-flex items-center gap-1 text-sm text-muted">
              <MapPin size={13} aria-hidden /> Координаты
            </span>
            <span className="text-sm tabular-nums text-ink">
              {card.snapshot.latitude.toFixed(4)}, {card.snapshot.longitude.toFixed(4)}
            </span>
          </div>
        </Card>
      </div>
    </div>
  )
}
