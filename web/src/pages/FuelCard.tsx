import { useEffect, useState } from 'react'
import {
  ArrowDownToLine,
  ArrowLeft,
  ArrowUpFromLine,
  Droplet,
  Fuel,
  Inbox,
  TriangleAlert,
} from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import { Card, DataTable, SeverityBadge, type Column } from '@/components'
import type { Severity } from '@/components'
import { getFuel } from '@/api/client'
import { ApiError } from '@/api/client'
import type { FuelReconRow, FuelReconStatus, FuelVehicleCard } from '@/api/types'
import { cn } from '@/components/ui/cn'

/**
 * w3-11 · Карточка топлива ТС (`/fleet-health/fuel/:plate`). Против §9.2/§9.4.
 *
 * `getFuel(plate)`: шапка KPI (Δ ЗИС−карта + recon-бейдж), таблица сверки
 * транзакция↔датчик (`FuelReconRow[]`), список заправок/сливов (`FuelEvent[]`).
 * Пустые списки → дружелюбная плашка (валидно, не ошибка); 404 → «ТС не найдено».
 */

const PARK_TZ = (import.meta.env.VITE_PARK_TIMEZONE as string | undefined) ?? 'UTC'
const MINUS = '−'

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
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

/** Число литров: «64,5 л» / «—» для null. */
function fmtL(n: number | null): string {
  if (n == null) return '—'
  return `${n.toLocaleString('ru-RU', { maximumFractionDigits: 1 })} л`
}

/** Знаковая дельта (типографский минус): «+22,5 л» / «−3,0 л». */
function fmtSignedL(n: number | null): string {
  if (n == null) return '—'
  const sign = n < 0 ? MINUS : '+'
  return `${sign}${Math.abs(n).toLocaleString('ru-RU', { maximumFractionDigits: 1 })} л`
}

// ── Статус сверки → токен d2 (matched→low/green, review→medium, missing→high) ──

const RECON: Record<FuelReconStatus, { severity: Severity; label: string }> = {
  matched: { severity: 'low', label: 'Сверено' },
  review: { severity: 'medium', label: 'Требует проверки' },
  missing_sensor_event: { severity: 'high', label: 'Нет события датчика' },
}

function ReconBadge({ status }: { status: FuelReconStatus }) {
  const { severity, label } = RECON[status]
  return <SeverityBadge severity={severity} label={label} />
}

// ── Таблица сверки (поля FuelReconRow §9.2) ───────────────────────────────────

const RECON_COLUMNS: Column<FuelReconRow>[] = [
  {
    id: 'transaction_ts',
    header: 'Транзакция (карта)',
    cell: (r) => (
      <span className="whitespace-nowrap tabular-nums">{formatDateTime(r.transaction_ts)}</span>
    ),
  },
  {
    id: 'event_ts',
    header: 'Событие (датчик)',
    cell: (r) => (
      <span className="whitespace-nowrap tabular-nums">{formatDateTime(r.event_ts)}</span>
    ),
  },
  {
    id: 'transaction_volume_l',
    header: 'Объём карты',
    align: 'right',
    cell: (r) => <span className="tabular-nums">{fmtL(r.transaction_volume_l)}</span>,
  },
  {
    id: 'sensor_volume_l',
    header: 'Объём датчика',
    align: 'right',
    cell: (r) => <span className="tabular-nums">{fmtL(r.sensor_volume_l)}</span>,
  },
  {
    id: 'volume_delta_l',
    header: 'Δ объёма',
    align: 'right',
    cell: (r) => {
      const severe = r.volume_delta_l != null && Math.abs(r.volume_delta_l) > 4
      return (
        <span
          className={cn('tabular-nums', severe ? 'font-semibold text-warning-text' : 'text-ink')}
        >
          {fmtSignedL(r.volume_delta_l)}
        </span>
      )
    },
  },
  {
    id: 'time_delta_min',
    header: 'Δ времени',
    align: 'right',
    cell: (r) =>
      r.time_delta_min == null ? (
        <span className="text-muted">—</span>
      ) : (
        <span className="tabular-nums">
          {r.time_delta_min.toLocaleString('ru-RU', { maximumFractionDigits: 1 })} мин
        </span>
      ),
  },
  {
    id: 'amount_rub',
    header: 'Сумма',
    align: 'right',
    cell: (r) =>
      r.amount_rub == null ? (
        <span className="text-muted">—</span>
      ) : (
        <span className="tabular-nums">
          {r.amount_rub.toLocaleString('ru-RU', { maximumFractionDigits: 0 })} ₽
        </span>
      ),
  },
  {
    id: 'reason',
    header: 'Причина',
    cell: (r) => <span className="text-muted">{r.reason || '—'}</span>,
  },
]

// ── KPI-плитка шапки ──────────────────────────────────────────────────────────

function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="flex min-w-[120px] flex-col gap-0.5">
      <span className="text-xs uppercase tracking-wide text-muted">{label}</span>
      <span className="text-lg font-semibold tabular-nums text-ink">{value}</span>
      {hint ? <span className="text-xs text-muted">{hint}</span> : null}
    </div>
  )
}

// ── Состояния ─────────────────────────────────────────────────────────────────

function CardSkeleton() {
  return (
    <div
      className="mx-auto max-w-5xl space-y-4"
      aria-busy="true"
      aria-label="Загрузка карточки топлива"
    >
      <Card>
        <div className="flex flex-wrap gap-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-12 w-28 animate-pulse rounded bg-border/60" />
          ))}
        </div>
      </Card>
      <Card>
        <div className="h-48 animate-pulse rounded bg-border/60" />
      </Card>
    </div>
  )
}

// ── Список заправок/сливов (FuelEvent §9.2) ───────────────────────────────────

function EventsList({ events }: { events: FuelVehicleCard['events'] }) {
  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-10 text-center text-muted">
        <Inbox className="h-7 w-7" aria-hidden />
        <p className="text-sm">Заправок и сливов за период не зафиксировано</p>
      </div>
    )
  }
  return (
    <ul role="list" className="flex flex-col gap-2">
      {events.map((e) => {
        const isRefuel = e.volume_l >= 0
        const Icon = isRefuel ? ArrowDownToLine : ArrowUpFromLine
        return (
          <li
            key={e.event_id}
            className="flex items-start gap-3 rounded-md border border-border bg-bg px-3 py-2"
          >
            <span
              className={cn(
                'mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full',
                isRefuel ? 'bg-ok-bg text-ok-text' : 'bg-critical-bg text-critical-text',
              )}
            >
              <Icon size={15} aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline gap-x-2">
                <span className="font-medium text-ink">{e.event_name}</span>
                <span className="tabular-nums text-muted">{formatDateTime(e.event_ts)}</span>
              </div>
              {e.address ? <div className="truncate text-xs text-muted">{e.address}</div> : null}
            </div>
            <div className="shrink-0 text-right">
              <div
                className={cn(
                  'font-semibold tabular-nums',
                  isRefuel ? 'text-ok-text' : 'text-critical-text',
                )}
              >
                {fmtSignedL(e.volume_l)}
              </div>
              {e.before_l != null && e.after_l != null ? (
                <div className="text-xs tabular-nums text-muted">
                  {fmtL(e.before_l)} → {fmtL(e.after_l)}
                </div>
              ) : null}
            </div>
          </li>
        )
      })}
    </ul>
  )
}

// ── Экран ─────────────────────────────────────────────────────────────────────

export default function FuelCard() {
  const { plate = '' } = useParams<{ plate: string }>()
  const navigate = useNavigate()
  const [card, setCard] = useState<FuelVehicleCard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<{ status?: number; message: string } | null>(null)

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError(null)
    setCard(null)
    getFuel(plate)
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
            {is404 ? `Топливные данные для «${plate}» отсутствуют.` : error?.message}
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
        <Fuel className="h-5 w-5 text-primary" aria-hidden />
        <h1 className="text-lg font-bold text-ink">Топливо · {card.vehicle_id}</h1>
        <span className="text-sm text-muted">{card.model}</span>
      </header>

      {/* Шапка KPI: headline Δ ЗИС−карта + recon-бейдж + сводка периода */}
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex flex-wrap gap-x-8 gap-y-3">
            <Kpi
              label="Δ ЗИС − карта"
              value={fmtSignedL(card.volume_delta_zis_minus_card_l)}
              hint={`${card.period_start} … ${card.period_end}`}
            />
            <Kpi
              label="Объём ЗИС"
              value={fmtL(card.fuel_volume_zis_l)}
              hint={`заправок: ${card.refuel_count_zis}`}
            />
            <Kpi
              label="Объём по картам"
              value={fmtL(card.fuel_volume_card_l)}
              hint={`транзакций: ${card.transaction_count_card}`}
            />
          </div>
          <ReconBadge status={card.recon_status} />
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 border-t border-border pt-4 sm:grid-cols-3 lg:grid-cols-6">
          <Kpi label="Расход" value={fmtL(card.summary.fuel_spent_l)} />
          <Kpi
            label="Пробег"
            value={`${card.summary.total_mileage_km.toLocaleString('ru-RU', { maximumFractionDigits: 0 })} км`}
          />
          <Kpi
            label="Ср. расход"
            value={`${card.summary.average_consumption_l_per_100km.toLocaleString('ru-RU', { maximumFractionDigits: 1 })} л/100`}
          />
          <Kpi
            label="Ср. скорость"
            value={`${card.summary.average_speed_kmh.toLocaleString('ru-RU', { maximumFractionDigits: 0 })} км/ч`}
          />
          <Kpi label="Заправок" value={String(card.summary.fuelings_count)} />
          <Kpi label="Сливов" value={String(card.summary.defuelings_count)} />
        </div>
      </Card>

      {/* Таблица сверки транзакция ↔ событие датчика */}
      <Card className="p-0">
        <div className="flex items-center gap-2 px-4 pt-4">
          <Droplet size={15} className="text-muted" aria-hidden />
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
            Сверка карта ↔ датчик
          </h2>
        </div>
        <DataTable
          columns={RECON_COLUMNS}
          rows={card.reconciliation}
          rowKey={(r) => r.row_id}
          emptyLabel="Строк сверки за период нет"
        />
      </Card>

      {/* Список заправок/сливов */}
      <Card>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
          Заправки и сливы
        </h2>
        <EventsList events={card.events} />
      </Card>
    </div>
  )
}
