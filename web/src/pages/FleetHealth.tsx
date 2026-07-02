import { useCallback } from 'react'
import { useAsyncLoad } from '@/state/useAsyncLoad'
import {
  Fuel,
  Inbox,
  Navigation2,
  RotateCcw,
  SatelliteDish,
  TriangleAlert,
  Video,
} from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { Button, Card, DataTable, type Column } from '@/components'
import { getFleetHealth } from '@/api/client'
import type { FleetHealthResponse, FleetHealthRow, SensorOnlineStatus } from '@/api/types'
import { cn } from '@/components/ui/cn'

/**
 * w3-11 · Хаб «Здоровье парка» (`/fleet-health`). Против `00-CONTRACT.md` §9.0/§9.4.
 *
 * Disjoint-домены (fuel:10, sensors:7, nav:5, в видеопарке:2 — §9.0): одна строка =
 * одно ТС объединения. Отсутствующий у ТС домен честно рендерится «—» (фича, не баг),
 * баннер покрытия обязателен. Клик по строке ведёт в самый «богатый» домен ТС
 * (fuel → sensor → РЭБ). Маршруты подключает w3-13 (этот экран их не регистрирует).
 */

const MINUS = '−' // типографский минус для KPI

// ── Цель «богатого» домена при клике по строке (fuel → sensor → reb) ──────────

/** URL самого информативного экрана для ТС; null → строка некликабельна. */
function richestTarget(row: FleetHealthRow): string | null {
  const plate = encodeURIComponent(row.plate)
  if (row.has_fuel) return `/fleet-health/fuel/${plate}`
  if (row.has_sensors) return `/fleet-health/sensors/${plate}`
  if (row.has_nav && row.reb_link_id) return `/reb/${encodeURIComponent(row.reb_link_id)}`
  return null
}

// ── Топливная дельта: severity-цвет при |Δ| > 4 л (§9.4) ──────────────────────

function FuelDeltaCell({ value }: { value: number | null }) {
  if (value == null) return <Dash />
  const severe = Math.abs(value) > 4
  const sign = value < 0 ? MINUS : '+'
  const text = `${sign}${Math.abs(value).toLocaleString('ru-RU', { maximumFractionDigits: 1 })} л`
  return (
    <span className={cn('tabular-nums', severe ? 'font-semibold text-warning-text' : 'text-ink')}>
      {text}
    </span>
  )
}

// ── Сенсорный online-индикатор: точка online/stale/offline (stale ≠ ошибка) ───

const ONLINE_DOT: Record<SensorOnlineStatus, { dot: string; label: string }> = {
  online: { dot: 'bg-ok', label: 'Online' },
  stale: { dot: 'bg-warning', label: 'Stale' }, // §9.5: нейтрально, не ошибка
  offline: { dot: 'bg-muted', label: 'Offline' },
}

function OnlineCell({ status }: { status: SensorOnlineStatus | null }) {
  if (status == null) return <Dash />
  const { dot, label } = ONLINE_DOT[status]
  return (
    <span className="inline-flex items-center gap-1.5 text-ink">
      <span className={cn('h-2 w-2 rounded-full', dot)} aria-hidden />
      {label}
    </span>
  )
}

// ── Прочерк для отсутствующего у ТС домена («—», не пусто/не ошибка) ──────────

function Dash() {
  return (
    <span className="text-muted" title="Домен недоступен для этого ТС">
      —
    </span>
  )
}

// ── Колонки хаба (§9.4) ──────────────────────────────────────────────────────

const COLUMNS: Column<FleetHealthRow>[] = [
  {
    id: 'vehicle',
    header: 'ТС',
    sortable: true,
    sortValue: (r) => r.vehicle_label ?? r.plate,
    cell: (r) => (
      <div className="flex items-center gap-2">
        <span className="font-medium tabular-nums text-ink">{r.vehicle_label ?? r.plate}</span>
        {r.in_video_fleet ? (
          <span className="inline-flex items-center gap-1 rounded bg-primary-50 px-1.5 py-0.5 text-[11px] font-medium text-primary">
            <Video size={11} aria-hidden />в видеопарке
          </span>
        ) : null}
      </div>
    ),
  },
  {
    id: 'fuel',
    header: 'Топливо Δ ЗИС−карта',
    align: 'right',
    sortable: true,
    sortValue: (r) => r.volume_delta_zis_minus_card_l ?? Number.NEGATIVE_INFINITY,
    cell: (r) => <FuelDeltaCell value={r.volume_delta_zis_minus_card_l} />,
  },
  {
    id: 'sensors_gap',
    header: 'Пробег CAN−GPS',
    align: 'right',
    sortable: true,
    sortValue: (r) => r.distance_gap_odometer_minus_gps_km ?? Number.NEGATIVE_INFINITY,
    cell: (r) =>
      r.distance_gap_odometer_minus_gps_km == null ? (
        <Dash />
      ) : (
        <span className="tabular-nums text-ink">
          {r.distance_gap_odometer_minus_gps_km.toLocaleString('ru-RU', {
            maximumFractionDigits: 1,
          })}{' '}
          км
        </span>
      ),
  },
  {
    id: 'online',
    header: 'Сенсоры online',
    cell: (r) => <OnlineCell status={r.online_status} />,
  },
  {
    id: 'nav',
    header: 'Навигация',
    cell: (r) => {
      if (r.gap_count == null) return <Dash />
      const label = (
        <span className="inline-flex items-center gap-1 rounded-xl bg-warning-bg px-2 py-0.5 text-xs font-medium text-warning-text">
          <Navigation2 size={12} aria-hidden />
          {r.gap_count} разр.
        </span>
      )
      // matched → ссылка в РЭБ; unmatched (reb_link_id=null) → бейдж без ссылки.
      return r.reb_link_id ? (
        <Link
          to={`/reb/${encodeURIComponent(r.reb_link_id)}`}
          onClick={(e) => e.stopPropagation()}
          className="rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          title="Открыть РЭБ-восстановление"
        >
          {label}
        </Link>
      ) : (
        <span title="ТС не сматчено — РЭБ недоступен">{label}</span>
      )
    },
  },
]

// ── Состояния загрузки ────────────────────────────────────────────────────────

function TableSkeleton() {
  return (
    <div className="space-y-2 p-4" aria-hidden>
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="h-9 w-full animate-pulse rounded bg-border/60" />
      ))}
    </div>
  )
}

// ── Баннер покрытия (disjoint-популяции, §9.0) ────────────────────────────────

function CoverageBanner({ coverage }: { coverage: FleetHealthResponse['coverage'] }) {
  const items: { icon: typeof Fuel; label: string; value: number }[] = [
    { icon: Fuel, label: 'Топливо', value: coverage.fuel },
    { icon: SatelliteDish, label: 'Сенсоры', value: coverage.sensors },
    { icon: Navigation2, label: 'Навигация', value: coverage.navigation },
    { icon: Video, label: 'в видеопарке', value: coverage.in_video_fleet },
  ]
  return (
    <Card className="flex flex-wrap items-center gap-x-6 gap-y-2 py-3">
      <span className="text-xs font-semibold uppercase tracking-wide text-muted">
        Покрытие парка
      </span>
      {items.map(({ icon: Icon, label, value }) => (
        <span key={label} className="inline-flex items-center gap-2 text-sm text-ink">
          <Icon size={15} className="text-muted" aria-hidden />
          {label}: <span className="font-semibold tabular-nums">{value}</span>
          <span className="text-muted">ТС</span>
        </span>
      ))}
    </Card>
  )
}

// ── Экран ─────────────────────────────────────────────────────────────────────

export default function FleetHealth() {
  const navigate = useNavigate()
  const { state, data, error, reload } = useAsyncLoad(getFleetHealth, {
    errorMessage: 'Не удалось загрузить здоровье парка.',
  })

  const handleRowClick = useCallback(
    (row: FleetHealthRow) => {
      const target = richestTarget(row)
      if (target) navigate(target)
    },
    [navigate],
  )

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-lg font-bold text-ink">Здоровье парка</h1>
        <p className="text-sm text-muted">
          Объединение телематических доменов (топливо · сенсоры · навигация). «—» — у ТС нет домена,
          это особенность фрагментированного парка, а не ошибка.
        </p>
      </header>

      {data ? <CoverageBanner coverage={data.coverage} /> : null}

      <Card className="p-0">
        {state === 'loading' ? (
          <TableSkeleton />
        ) : state === 'error' ? (
          <div className="flex flex-col items-center gap-3 py-12 text-center">
            <TriangleAlert className="h-8 w-8 text-high-text" aria-hidden />
            <p className="max-w-sm text-sm text-muted">
              {error ?? 'Не удалось загрузить здоровье парка.'}
            </p>
            <Button variant="secondary" icon={RotateCcw} onClick={reload}>
              Повторить
            </Button>
          </div>
        ) : !data || data.rows.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-16 text-center text-muted">
            <Inbox className="h-8 w-8" aria-hidden />
            <p className="text-sm">Нет ТС с телематическими данными</p>
          </div>
        ) : (
          <DataTable
            columns={COLUMNS}
            rows={data.rows}
            rowKey={(r) => r.plate}
            onRowClick={handleRowClick}
          />
        )}
      </Card>
    </div>
  )
}
