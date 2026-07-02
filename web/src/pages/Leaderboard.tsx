import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Inbox, Info, Leaf, RotateCw, Trophy, TriangleAlert } from 'lucide-react'
import { Card } from '@/components'
import { cn } from '@/components/ui/cn'
import { getLeaderboard } from '@/api/client'
import type { DriverScore } from '@/api/types'
import { useAsyncLoad } from '@/state/useAsyncLoad'

/**
 * f28 · Лидерборд водителей (`/leaderboard`, фичи #25/#26, §13.2/§13.3). Против
 * `00-CONTRACT.md` §13.0–§13.4. Руководитель видит рейтинг одним списком (видео +
 * телематика в одном `unified_score`) и «зелёную зону» (паттерн Netradyne GreenZone).
 *
 * Данные детерминированы (§13.0) — без AI/сети. Дисклеймер периода обязателен
 * (§13.0): датасет покрывает мало дней, число рядом с любым score честно ограничено.
 * Клик/Enter по строке → отчёт водителя (`/report?q=<driver>`, как drill в FleetDashboard).
 * A11y: место и green-zone — не только цветом (ранг-число + иконка/текст); таблица с
 * заголовками; строки фокусируемы и открываются с клавиатуры.
 */

// ── Период покрытия для дисклеймера (§13.0): одно значение на весь лидерборд ────
/** Период покрытия датасета (§13.0) — согласован с фикстурами/бэкендом positive-score. */
const PERIOD_DAYS = 18

function periodDays(rows: DriverScore[]): number | null {
  // DriverScore не несёт period_days (это поле PositiveScore §13.1) — лидерборд
  // показывает общий дисклеймер с числом дней покрытия датасета.
  return rows.length > 0 ? PERIOD_DAYS : null
}

// ── Состояние загрузки ──────────────────────────────────────────────────────────
function TableSkeleton() {
  return (
    <div className="space-y-2 p-4" aria-hidden>
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="h-10 w-full animate-pulse rounded bg-border/60" />
      ))}
    </div>
  )
}

/** Бейдж «зелёная зона»: иконка + текст (a11y — не только цветом, §13.3/§13.7). */
function GreenZoneBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-lg bg-ok-bg px-2 py-0.5 text-xs font-medium text-ok-text">
      <Leaf className="h-3.5 w-3.5" aria-hidden />
      зелёная зона
    </span>
  )
}

/** Мини-разбивка unified: риск-компонент vs позитив-компонент (§13.2). */
function ScoreBreakdown({ row }: { row: DriverScore }) {
  return (
    <span className="inline-flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs tabular-nums text-muted">
      <span title="Риск-компонент = 0.6·(100 − средний риск)">
        риск {row.risk_component.toFixed(1)}
      </span>
      <span aria-hidden>·</span>
      <span title="Позитив-компонент = 0.4·позитивный скоринг">
        позитив {row.positive_component.toFixed(1)}
      </span>
    </span>
  )
}

// ── Экран ──────────────────────────────────────────────────────────────────────
export default function Leaderboard() {
  const navigate = useNavigate()
  const { state, data, error, reload } = useAsyncLoad(getLeaderboard, {
    errorMessage: 'Не удалось загрузить рейтинг.',
  })
  const rows = data ?? []

  // Клик по строке → отчёт водителя (тот же механизм, что drill в FleetDashboard).
  const openDriver = useCallback(
    (row: DriverScore) => navigate(`/report?q=${encodeURIComponent(row.driver_name)}`),
    [navigate],
  )

  const days = periodDays(rows)

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-lg font-bold text-ink">
            <Trophy className="h-5 w-5 text-primary" aria-hidden />
            Рейтинг водителей
          </h1>
          <p className="text-sm text-muted">
            Единая оценка видео и телематики в одном числе; «зелёная зона» — признание
            хорошего вождения, а не только нарушений.
          </p>
        </div>
      </header>

      {/* Дисклеймер периода — обязателен (§13.0): датасет покрывает мало дней. */}
      {days != null && (
        <p className="inline-flex items-center gap-1.5 rounded-lg bg-warning-bg px-3 py-1.5 text-xs font-medium text-warning-text">
          <Info className="h-3.5 w-3.5" aria-hidden />
          Оценки за период {days} дн. — датасет покрывает ограниченное окно.
        </p>
      )}

      <Card className="p-0">
        {state === 'loading' ? (
          <TableSkeleton />
        ) : state === 'error' ? (
          <div className="flex flex-col items-center gap-3 py-12 text-center">
            <TriangleAlert className="h-8 w-8 text-high-text" aria-hidden />
            <p className="max-w-sm text-sm text-muted">{error ?? 'Не удалось загрузить рейтинг.'}</p>
            <button
              type="button"
              onClick={reload}
              className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-1.5 text-sm font-medium text-ink transition-colors hover:border-primary hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            >
              <RotateCw className="h-4 w-4" aria-hidden />
              Повторить
            </button>
          </div>
        ) : rows.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-16 text-center text-muted">
            <Inbox className="h-8 w-8" aria-hidden />
            <p className="text-sm">Нет водителей для рейтинга</p>
          </div>
        ) : (
          <LeaderboardTable rows={rows} onRowClick={openDriver} />
        )}
      </Card>
    </div>
  )
}

// ── Таблица ──────────────────────────────────────────────────────────────────
function LeaderboardTable({
  rows,
  onRowClick,
}: {
  rows: DriverScore[]
  onRowClick: (row: DriverScore) => void
}) {
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b-2 border-border bg-bg text-left">
          <Th align="center">Место</Th>
          <Th>Водитель</Th>
          <Th>ТС</Th>
          <Th align="right">Оценка</Th>
          <Th>Разбивка</Th>
          <Th align="center">Зона</Th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <LeaderboardRow
            key={row.vehicle_plate}
            row={row}
            rank={i + 1}
            onClick={() => onRowClick(row)}
          />
        ))}
      </tbody>
    </table>
  )
}

function LeaderboardRow({
  row,
  rank,
  onClick,
}: {
  row: DriverScore
  rank: number
  onClick: () => void
}) {
  return (
    <tr
      role="button"
      tabIndex={0}
      aria-label={`Место ${rank}, ${row.driver_name}, оценка ${row.unified_score}${row.green_zone ? ', зелёная зона' : ''}`}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick()
        }
      }}
      className="cursor-pointer border-b border-border transition-colors hover:bg-bg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary"
    >
      {/* Место — число (a11y: ранг не только цветом/порядком), топ-3 акцентом. */}
      <td className="px-3 py-2 text-center">
        <span
          className={cn(
            'inline-grid h-7 w-7 place-items-center rounded-full text-xs font-bold tabular-nums',
            rank <= 3 ? 'bg-primary-50 text-primary' : 'text-muted',
          )}
        >
          {rank}
        </span>
      </td>
      <td className="px-3 py-2 font-medium text-ink">{row.driver_name}</td>
      <td className="whitespace-nowrap px-3 py-2 tabular-nums text-muted">{row.vehicle_plate}</td>
      {/* unified_score — крупно (§13.3). */}
      <td className="px-3 py-2 text-right">
        <span className="text-xl font-bold tabular-nums text-ink">{row.unified_score}</span>
      </td>
      <td className="px-3 py-2">
        <ScoreBreakdown row={row} />
      </td>
      <td className="px-3 py-2 text-center">
        {row.green_zone ? <GreenZoneBadge /> : <span className="text-muted" aria-hidden>—</span>}
      </td>
    </tr>
  )
}

function Th({
  children,
  align = 'left',
}: {
  children: React.ReactNode
  align?: 'left' | 'right' | 'center'
}) {
  return (
    <th
      scope="col"
      className={cn(
        'px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted',
        align === 'right' && 'text-right',
        align === 'center' && 'text-center',
      )}
    >
      {children}
    </th>
  )
}
