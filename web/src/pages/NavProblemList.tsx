import { useCallback, useEffect, useState } from 'react'
import { Inbox, Navigation2, Radio, RotateCcw, TriangleAlert, Unlink, Video } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button, Card } from '@/components'
import { listNavProblems } from '@/api/client'
import type { NavProblemVehicle } from '@/api/types'

/**
 * w3-11 · Список проблемных навигационных треков (`/navigation`). Против §9.2/§9.4.
 *
 * `listNavProblems()`: карточки с человеческим `problem_description` и gap-статами;
 * кнопка «Открыть РЭБ» → `/reb/:reb_link_id` (вход в уже существующий §7.4-экран).
 * unmatched-ТС (`reb_link_id=null`) показан (у него реальная проблема), но кнопка
 * РЭБ disabled (§9.5) — не прячем «тёмные» данные.
 */

/** Длительность без сигнала: «1 ч 30 мин» / «31 мин» / «45 с». */
function fmtDuration(sec: number): string {
  const total = Math.max(0, Math.round(sec))
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  if (h > 0) return `${h} ч ${m} мин`
  if (m > 0) return `${m} мин`
  return `${total} с`
}

// ── Состояние загрузки ────────────────────────────────────────────────────────

function ListSkeleton() {
  return (
    <div className="space-y-3" aria-hidden>
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="h-28 w-full animate-pulse rounded-md bg-border/60" />
      ))}
    </div>
  )
}

// ── Карточка проблемного ТС ───────────────────────────────────────────────────

function ProblemCard({ row }: { row: NavProblemVehicle }) {
  const navigate = useNavigate()
  const matched = row.match_status === 'matched' && row.reb_link_id != null
  const title = row.vehicle_label ?? row.plate ?? 'ТС не сматчено со справочником'

  return (
    <Card className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0 flex-1 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <Navigation2 size={16} className="text-primary" aria-hidden />
          <span className="font-semibold text-ink">{title}</span>
          {row.brand ? <span className="text-sm text-muted">{row.brand}</span> : null}
          {row.in_video_fleet ? (
            <span className="inline-flex items-center gap-1 rounded bg-primary-50 px-1.5 py-0.5 text-[11px] font-medium text-primary">
              <Video size={11} aria-hidden />в видеопарке
            </span>
          ) : null}
          {!matched ? (
            <span className="inline-flex items-center gap-1 rounded-xl bg-bg px-2 py-0.5 text-[11px] font-medium text-muted ring-1 ring-border">
              <Unlink size={11} aria-hidden />
              не сматчено
            </span>
          ) : null}
        </div>

        <p className="text-sm text-ink">{row.problem_description}</p>

        <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
          <span>
            Разрывов GPS: <span className="font-medium tabular-nums text-ink">{row.gap_count}</span>
          </span>
          <span>
            Периодов: <span className="font-medium tabular-nums text-ink">{row.total_periods}</span>
          </span>
          <span>
            Без сигнала:{' '}
            <span className="font-medium tabular-nums text-ink">
              {fmtDuration(row.total_gap_duration_sec)}
            </span>
          </span>
        </div>
      </div>

      <div className="shrink-0">
        {matched ? (
          <Button
            variant="secondary"
            icon={Radio}
            onClick={() => navigate(`/reb/${encodeURIComponent(row.reb_link_id as string)}`)}
          >
            Открыть РЭБ
          </Button>
        ) : (
          <Button
            variant="secondary"
            icon={Radio}
            disabled
            title="ТС не сматчено — привязка к РЭБ недоступна"
          >
            РЭБ недоступен
          </Button>
        )}
      </div>
    </Card>
  )
}

// ── Экран ─────────────────────────────────────────────────────────────────────

export default function NavProblemList() {
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [rows, setRows] = useState<NavProblemVehicle[]>([])
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    setState('loading')
    setError(null)
    listNavProblems()
      .then((data) => {
        setRows(data)
        setState('ready')
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Не удалось загрузить список проблем навигации.')
        setState('error')
      })
  }, [])

  useEffect(load, [load])

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-lg font-bold text-ink">Навигация · проблемные треки</h1>
        <p className="text-sm text-muted">
          ТС с разрывами GPS-сигнала. «Открыть РЭБ» ведёт к восстановлению трека и соседним
          видеокадрам; несматченные ТС показаны, но без привязки к РЭБ.
        </p>
      </header>

      {state === 'loading' ? (
        <ListSkeleton />
      ) : state === 'error' ? (
        <Card className="flex flex-col items-center gap-3 py-12 text-center">
          <TriangleAlert className="h-8 w-8 text-high-text" aria-hidden />
          <p className="max-w-sm text-sm text-muted">
            {error ?? 'Не удалось загрузить список проблем навигации.'}
          </p>
          <Button variant="secondary" icon={RotateCcw} onClick={load}>
            Повторить
          </Button>
        </Card>
      ) : rows.length === 0 ? (
        <Card className="flex flex-col items-center gap-2 py-16 text-center text-muted">
          <Inbox className="h-8 w-8" aria-hidden />
          <p className="text-sm">Проблемных треков нет</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {rows.map((row, i) => (
            <ProblemCard key={row.reb_link_id ?? row.plate ?? `unmatched-${i}`} row={row} />
          ))}
        </div>
      )}
    </div>
  )
}
