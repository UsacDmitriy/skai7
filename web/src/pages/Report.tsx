import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  Archive,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock,
  ExternalLink,
  FlaskConical,
  GraduationCap,
  Inbox,
  Info,
  Lightbulb,
  LineChart,
  RotateCcw,
  Search,
  Sparkles,
  TrendingUp,
  TriangleAlert,
  Truck,
  Users,
  Video,
  X,
} from 'lucide-react'
import * as client from '@/api/client'
import { ApiError } from '@/api/client'
import { trackEvent } from '@/api/metrics'
import * as voice from '@/api/voice'
import type {
  CoachingAssignment,
  CoachingCard,
  CoachingStatus,
  DriverReport,
  FleetByDriverRow,
  FleetByVehicleRow,
  FleetReport,
  IncidentDetail,
  QueryResult,
  ReportKPI,
  RiskForecast,
  Severity,
  Source,
  ViolationRow,
} from '@/api/types'
import { ForecastSparkline } from '@/components/ai/ForecastSparkline'
import { RiskWaterfall } from '@/components/ai/RiskWaterfall'
import {
  Button,
  Card,
  type Column,
  DataTable,
  ScoreBar,
  SeverityBadge,
  VideoPlayer,
  VoiceButton,
  type VoiceButtonState,
  ConfirmationModal,
} from '@/components'
import { SabotageWidget } from '@/components/SabotageWidget'

/**
 * f7 · Аналитика + голос (`/report`). Полная версия, замещает scaffold f4 (§7.7).
 * Поток (идея #2): VoiceButton (d5) → transcribe → текст → queryReport → ConfirmationModal (d5)
 * → дашборд (DriverReport В-1 / FleetReport В-2). Killer-feature (§6): клик по нарушению →
 * выезжающая видео-панель, канал по типу (DMS→ch5 / ADAS→ch1), src — всегда client.videoUrl
 * (анти-регресс DEF-3, сырой cam_*_url — лишь индикатор наличия + выбор канала).
 *
 * Полиш P1: 4 состояния каждого асинка (idle/loading/ready/error+retry), shareable deep-link
 * (`?q=&sel=`), focus-trap/Esc/клавиатура видео-панели, пагинация таблицы (≥50), честная
 * деградация голоса (текст всегда альтернатива), фикстуры (`VITE_USE_FIXTURES=true`).
 */

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: 'Критично',
  high: 'Высокий',
  medium: 'Средний',
  low: 'Низкий',
}

/** Порог пагинации таблицы нарушений (полиш §5). */
const PAGE_SIZE = 50
/** Порог низкой уверенности STT → подсветить и предложить правку текста. */
const LOW_CONFIDENCE = 0.7

function isDriverReport(r: DriverReport | FleetReport): r is DriverReport {
  return 'violations' in r
}

function humanError(e: unknown): string {
  if (e instanceof ApiError) return e.message
  if (e instanceof Error) return e.message
  return 'Неизвестная ошибка'
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

// ── Killer-feature: маршрутизация канала видео (§6, DEF-3) ─────────────────────

type VideoChannel15 = 1 | 5

/**
 * Источник видео для плеера. cam_*_url — лишь индикатор наличия + выбор канала;
 * сам `src` — ВСЕГДА API-эндпоинт `client.videoUrl(id, channel)` (DEF-3, barrier-1 smoke x3:
 * прямой биндинг сырого пути → 404). Маршрутизация СТРОГО по типу (§6, line 114):
 * DMS→ch5 (`cam_dms_url`), ADAS→ch1 (`cam_front_url`), без кросс-фолбэка между ними.
 * COMBINED/TELEMATICS/неизвестно — нет жёсткого канала, берём фактически доступную камеру.
 */
function resolveVideo(inc: IncidentDetail, source: Source | null): { src?: string; channel?: VideoChannel15 } {
  if (inc.video_available === false) return {}
  // DMS / DIAGNOSTIC → строго ch5.
  if (source === 'DMS' || source === 'DIAGNOSTIC') {
    return inc.cam_dms_url ? { src: client.videoUrl(inc.id, 5), channel: 5 } : {}
  }
  // ADAS → строго ch1.
  if (source === 'ADAS') {
    return inc.cam_front_url ? { src: client.videoUrl(inc.id, 1), channel: 1 } : {}
  }
  // Прочее: по наличию — ADAS-фронт приоритетнее DMS-салона.
  if (inc.cam_front_url) return { src: client.videoUrl(inc.id, 1), channel: 1 }
  if (inc.cam_dms_url) return { src: client.videoUrl(inc.id, 5), channel: 5 }
  return {}
}

// ── KPI ───────────────────────────────────────────────────────────────────────

function KpiTile({ label, value, accent }: { label: string; value: number; accent?: string }) {
  return (
    <div className="rounded-md border border-border bg-surface px-4 py-3">
      <div className="text-[11px] uppercase tracking-wide text-muted">{label}</div>
      <div className={`mt-1 text-2xl font-bold tabular-nums ${accent ?? 'text-ink'}`}>{value}</div>
    </div>
  )
}

function KpiRow({ kpi }: { kpi: ReportKPI }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <KpiTile label="Всего" value={kpi.total} />
      <KpiTile label="ВА видео-детекции" value={kpi.video_da} />
      <KpiTile label="Телематика" value={kpi.telematics} />
      <KpiTile label="Грубых" value={kpi.gross} accent="text-critical-text" />
    </div>
  )
}

// ── Скелеты (loading) ─────────────────────────────────────────────────────────

function Bar({ className }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-border/60 ${className ?? ''}`} />
}

function DashboardSkeleton() {
  return (
    <div className="space-y-4" aria-hidden>
      <Card>
        <Bar className="h-5 w-48" />
        <Bar className="mt-2 h-4 w-72" />
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Bar key={i} className="h-16" />
          ))}
        </div>
      </Card>
      <Card className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Bar key={i} className="h-8 w-full" />
        ))}
      </Card>
    </div>
  )
}

// ── Блок ошибки с ретраем (4 состояния, полиш §1) ─────────────────────────────

function ErrorBlock({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <Card className="flex flex-col items-center gap-3 py-10 text-center">
      <TriangleAlert className="h-8 w-8 text-high-text" aria-hidden />
      <p className="max-w-sm text-sm text-muted">{message}</p>
      <Button variant="secondary" icon={RotateCcw} onClick={onRetry}>
        Повторить
      </Button>
    </Card>
  )
}

// ── Колонки таблиц ────────────────────────────────────────────────────────────

const VIOLATION_COLUMNS: Column<ViolationRow>[] = [
  { id: 'ts', header: 'Время', cell: (r) => <span className="tabular-nums text-muted">{formatTime(r.ts)}</span>, sortable: true, sortValue: (r) => r.ts },
  { id: 'label', header: 'Нарушение', cell: (r) => <span className="font-medium text-ink">{r.alarm_label_ru}</span> },
  { id: 'severity', header: 'Severity', cell: (r) => <SeverityBadge severity={r.severity} label={SEVERITY_LABEL[r.severity]} /> },
  { id: 'gross', header: 'Грубое', align: 'center', cell: (r) => (r.is_gross ? <span className="text-critical-text" title="Грубое нарушение">●</span> : <span className="text-muted">—</span>), sortable: true, sortValue: (r) => (r.is_gross ? 1 : 0) },
  { id: 'video', header: '', align: 'center', cell: () => <Video className="inline h-4 w-4 text-muted" aria-hidden /> },
  // w3-12 · кросс-врезка: нарушение → карточка инцидента. stopPropagation сохраняет
  // killer-feature (клик по строке открывает инлайн-видео, ссылка — аддитивна).
  {
    id: 'open',
    header: '',
    align: 'center',
    cell: (r) => (
      <Link
        to={`/incidents/${r.id}`}
        onClick={(e) => e.stopPropagation()}
        aria-label="Открыть карточку инцидента"
        title="Открыть карточку инцидента"
        className="inline-grid h-7 w-7 place-items-center rounded text-muted transition-colors hover:bg-bg hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        <ExternalLink className="h-4 w-4" aria-hidden />
      </Link>
    ),
  },
]

const FLEET_DRIVER_COLUMNS: Column<FleetByDriverRow>[] = [
  { id: 'driver', header: 'Водитель', cell: (r) => <span className="font-medium text-ink">{r.driver.driver_name}</span> },
  { id: 'vehicle', header: 'ТС', cell: (r) => `${r.vehicle_model} · ${r.vehicle_plate}` },
  { id: 'risk', header: 'Риск', align: 'right', cell: (r) => <ScoreBar score={r.risk_score} className="w-28" />, sortable: true, sortValue: (r) => r.risk_score },
  { id: 'gross', header: 'Грубых', align: 'right', cell: (r) => <span className="tabular-nums">{r.gross}</span>, sortable: true, sortValue: (r) => r.gross },
  { id: 'total', header: 'Всего', align: 'right', cell: (r) => <span className="tabular-nums">{r.total}</span>, sortable: true, sortValue: (r) => r.total },
]

const FLEET_VEHICLE_COLUMNS: Column<FleetByVehicleRow>[] = [
  { id: 'plate', header: 'ТС', cell: (r) => <span className="font-medium text-ink">{r.vehicle_model} · {r.plate}</span> },
  { id: 'driver', header: 'Осн. водитель', cell: (r) => r.main_driver },
  { id: 'cams', header: 'Камеры', align: 'center', cell: (r) => <span className="tabular-nums text-muted">{r.cameras_ok}</span> },
  { id: 'risk', header: 'Риск', align: 'right', cell: (r) => <ScoreBar score={r.risk_score} className="w-28" />, sortable: true, sortValue: (r) => r.risk_score },
  { id: 'gross', header: 'Грубых', align: 'right', cell: (r) => <span className="tabular-nums">{r.gross}</span>, sortable: true, sortValue: (r) => r.gross },
  { id: 'total', header: 'Всего', align: 'right', cell: (r) => <span className="tabular-nums">{r.total}</span>, sortable: true, sortValue: (r) => r.total },
]

// ── Таблица нарушений: пагинация (≥50) + клавиатура (стрелки/Enter) ────────────

function ViolationsTable({
  rows,
  selectedId,
  onOpen,
  onCursor,
}: {
  rows: ViolationRow[]
  selectedId?: string
  onOpen: (row: ViolationRow) => void
  onCursor: (id: string) => void
}) {
  const [page, setPage] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const pageCount = Math.max(1, Math.ceil(rows.length / PAGE_SIZE))
  const paged = rows.length > PAGE_SIZE ? rows.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE) : rows

  // Активная строка всегда в видимой зоне (полиш §3).
  useEffect(() => {
    if (!selectedId) return
    containerRef.current?.querySelector('tr.bg-primary-50')?.scrollIntoView({ block: 'nearest' })
  }, [selectedId])

  // Навигация стрелками + Enter открывает видео (полиш §4).
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!paged.length) return
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp' && e.key !== 'Enter') return
    e.preventDefault()
    const idx = paged.findIndex((r) => r.id === selectedId)
    if (e.key === 'Enter') {
      const row = paged[idx] ?? paged[0]
      onOpen(row)
      return
    }
    const next = e.key === 'ArrowDown' ? Math.min(paged.length - 1, idx < 0 ? 0 : idx + 1) : Math.max(0, idx <= 0 ? 0 : idx - 1)
    onCursor(paged[next].id)
  }

  return (
    <div ref={containerRef}>
      <div
        tabIndex={0}
        role="grid"
        aria-label="Нарушения водителя, навигация стрелками, Enter открывает видео"
        onKeyDown={onKeyDown}
        className="rounded-md outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        <DataTable
          columns={VIOLATION_COLUMNS}
          rows={paged}
          rowKey={(r) => r.id}
          selectedKey={selectedId}
          onRowClick={onOpen}
          emptyLabel="Нарушений за период не найдено"
        />
      </div>
      {rows.length > PAGE_SIZE && (
        <div className="flex items-center justify-end gap-2 border-t border-border px-4 py-2 text-xs text-muted">
          <span className="tabular-nums">Стр. {page + 1} / {pageCount}</span>
          <Button variant="secondary" icon={ChevronLeft} disabled={page === 0} onClick={() => setPage((p) => p - 1)} className="h-7 w-7 px-0" aria-label="Назад" />
          <Button variant="secondary" icon={ChevronRight} disabled={page >= pageCount - 1} onClick={() => setPage((p) => p + 1)} className="h-7 w-7 px-0" aria-label="Вперёд" />
        </div>
      )}
    </div>
  )
}

// ── Видео-панель (killer-feature, §6) — focus-trap / Esc / a11y ────────────────

function VideoPanel({
  state,
  incident,
  source,
  error,
  onClose,
  onRetry,
}: {
  state: 'loading' | 'ready' | 'error'
  incident: IncidentDetail | null
  source: Source | null
  error: string | null
  onClose: () => void
  onRetry: () => void
}) {
  const panelRef = useRef<HTMLDivElement>(null)
  const [archiveRequested, setArchiveRequested] = useState(false)

  // Focus-trap + Esc + автофокус при открытии (полиш §4, §a11y).
  useEffect(() => {
    const panel = panelRef.current
    if (!panel) return
    const opener = document.activeElement as HTMLElement | null
    const focusables = () =>
      Array.from(
        panel.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, video, [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((el) => !el.hasAttribute('disabled'))
    panel.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
        return
      }
      if (e.key !== 'Tab') return
      const items = focusables()
      if (!items.length) return
      const first = items[0]
      const last = items[items.length - 1]
      const active = document.activeElement
      if (e.shiftKey && active === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && active === last) {
        e.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      opener?.focus?.()
    }
  }, [onClose])

  const video = useMemo(() => (incident ? resolveVideo(incident, source) : {}), [incident, source])

  const requestArchive = useCallback(() => {
    if (!incident) return
    setArchiveRequested(true)
    client
      .postAction({ incident_id: incident.id, action: 'request_archive', comment: 'Запрос архива из отчёта' })
      .catch(() => setArchiveRequested(false))
  }, [incident])

  return (
    <>
      <div className="fixed inset-0 z-30 bg-ink/30" onClick={onClose} aria-hidden />
      <aside
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label="Видео нарушения"
        tabIndex={-1}
        className="fixed right-0 top-0 z-40 flex h-full w-full max-w-md flex-col gap-4 overflow-y-auto border-l border-border bg-surface p-5 shadow-xl outline-none"
      >
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-ink">Видео нарушения</h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Закрыть"
            className="grid h-7 w-7 place-items-center rounded text-muted hover:bg-bg hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>

        {state === 'loading' && (
          <>
            <Bar className="h-4 w-40" />
            <Bar className="aspect-video w-full" />
          </>
        )}

        {state === 'error' && (
          <div className="flex flex-col items-center gap-3 py-8 text-center">
            <TriangleAlert className="h-7 w-7 text-high-text" aria-hidden />
            <p className="text-sm text-muted">{error ?? 'Не удалось загрузить инцидент.'}</p>
            <Button variant="secondary" icon={RotateCcw} onClick={onRetry}>
              Повторить
            </Button>
          </div>
        )}

        {state === 'ready' && incident && (
          <>
            <div>
              <div className="text-sm font-medium text-ink">{incident.alarm_label_ru}</div>
              <div className="mt-0.5 text-xs text-muted">
                {incident.vehicle_plate} · {formatTime(incident.ts)}
                {video.channel != null && (
                  <span className="ml-1 rounded bg-bg px-1.5 py-0.5 tabular-nums">
                    {video.channel === 5 ? 'DMS · ch5' : 'ADAS · ch1'}
                  </span>
                )}
              </div>
            </div>

            <VideoPlayer src={video.src} />

            {!video.src && (
              <div className="rounded-md border border-border bg-bg p-4 text-center text-sm text-muted">
                <p>Видео по этому нарушению недоступно.</p>
                <Button
                  variant="secondary"
                  icon={Archive}
                  onClick={requestArchive}
                  disabled={archiveRequested}
                  className="mt-3"
                >
                  {archiveRequested ? 'Запрос отправлен' : 'Запросить архив'}
                </Button>
              </div>
            )}

            {incident.evidence_summary && <p className="text-xs text-muted">{incident.evidence_summary}</p>}

            {/* f20 · explainability (§8.8): почему такой риск у нарушения — waterfall вкладов. */}
            <RiskWaterfall id={incident.id} />
          </>
        )}
      </aside>
    </>
  )
}

// ── Прогноз риска + рекомендации (f16, идея #12, §8.4) ────────────────────────
// Аддитивный блок: спарклайн тренда (d7) + коридор + аномалия + список рекомендаций.
// Метрики b25: показ → recommendation_shown, принятие → recommendation_accepted
// (эмиттер b25; без сети — no-op). Питает recommendation_acceptance (§8.7).

function ForecastCard({
  plate,
  title = 'Прогноз риска',
  subtitle,
}: {
  plate: string
  title?: string
  subtitle?: string
}) {
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [forecast, setForecast] = useState<RiskForecast | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [accepted, setAccepted] = useState<Set<number>>(new Set())

  const load = useCallback(() => {
    setState('loading')
    setError(null)
    setForecast(null)
    setAccepted(new Set())
    client
      .getForecast(plate)
      .then((f) => {
        setForecast(f)
        setState('ready')
      })
      .catch((e: unknown) => {
        setError(humanError(e))
        setState('error')
      })
  }, [plate])

  useEffect(() => {
    load()
  }, [load])

  // b25 · показ рекомендаций → recommendation_shown (один раз на загрузку прогноза).
  useEffect(() => {
    if (state === 'ready' && forecast && forecast.recommendations.length > 0) {
      trackEvent('recommendation_shown', { plate, count: forecast.recommendations.length })
    }
  }, [state, forecast, plate])

  const acceptRec = useCallback(
    (idx: number, text: string) => {
      setAccepted((prev) => {
        if (prev.has(idx)) return prev
        const next = new Set(prev)
        next.add(idx)
        // b25 · принятие рекомендации → recommendation_accepted.
        trackEvent('recommendation_accepted', { plate, recommendation: text })
        return next
      })
    },
    [plate],
  )

  const isEmpty =
    state === 'ready' &&
    forecast != null &&
    forecast.trend.length === 0 &&
    forecast.recommendations.length === 0

  return (
    <Card className="p-0">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-ink">
          <TrendingUp className="h-4 w-4 text-primary" aria-hidden />
          {title}
          {subtitle && <span className="font-normal text-muted">— {subtitle}</span>}
        </div>
        {state === 'ready' && forecast?.anomaly && (
          <span className="inline-flex items-center gap-1.5 rounded-md bg-critical-bg px-2.5 py-1 text-xs font-semibold text-critical-text">
            <TriangleAlert className="h-3.5 w-3.5" aria-hidden />
            Аномалия в тренде
          </span>
        )}
      </div>

      <div className="p-4">
        {state === 'loading' && (
          <div aria-hidden className="space-y-3">
            <Bar className="h-14 w-full" />
            <Bar className="h-4 w-3/4" />
            <Bar className="h-4 w-2/3" />
          </div>
        )}

        {state === 'error' && (
          <div className="flex flex-col items-center gap-3 py-6 text-center">
            <TriangleAlert className="h-7 w-7 text-high-text" aria-hidden />
            <p className="text-sm text-muted">{error ?? 'Не удалось загрузить прогноз.'}</p>
            <Button variant="secondary" icon={RotateCcw} onClick={load}>
              Повторить
            </Button>
          </div>
        )}

        {isEmpty && (
          <div className="flex flex-col items-center gap-2 py-8 text-center text-muted">
            <LineChart className="h-8 w-8" aria-hidden />
            <p className="text-sm">
              Прогноз недоступен{forecast?.anomaly_reason ? ` — ${forecast.anomaly_reason}` : '.'}
            </p>
          </div>
        )}

        {state === 'ready' && forecast && !isEmpty && (
          <div className="space-y-4">
            {forecast.trend.length > 0 ? (
              <div>
                <div className="mb-1 text-[11px] uppercase tracking-wide text-muted">
                  Тренд событий + доверительный коридор
                </div>
                <ForecastSparkline trend={forecast.trend} anomaly={forecast.anomaly} />
              </div>
            ) : (
              forecast.anomaly_reason && (
                <p className="inline-flex items-center gap-1.5 text-xs text-muted">
                  <Info className="h-3.5 w-3.5" aria-hidden />
                  {forecast.anomaly_reason}
                </p>
              )
            )}

            {forecast.narrative && <p className="text-sm text-muted">{forecast.narrative}</p>}

            {forecast.recommendations.length > 0 && (
              <div>
                <div className="mb-2 flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-muted">
                  <Lightbulb className="h-3.5 w-3.5" aria-hidden />
                  Рекомендации
                </div>
                <ul className="space-y-1.5">
                  {forecast.recommendations.map((rec, i) => {
                    const isAccepted = accepted.has(i)
                    return (
                      <li
                        key={i}
                        className="flex items-start justify-between gap-3 rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink"
                      >
                        <span className="flex-1">{rec}</span>
                        <button
                          type="button"
                          onClick={() => acceptRec(i, rec)}
                          disabled={isAccepted}
                          aria-label={isAccepted ? 'Рекомендация принята' : 'Принять рекомендацию'}
                          className={`inline-flex shrink-0 items-center gap-1 rounded px-2 py-1 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                            isAccepted
                              ? 'cursor-default text-ok-text'
                              : 'text-primary hover:bg-primary-50'
                          }`}
                        >
                          <Check className="h-3.5 w-3.5" aria-hidden />
                          {isAccepted ? 'Принято' : 'Принять'}
                        </button>
                      </li>
                    )
                  })}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}

// ── f27 · Секция «Обучение водителя» (фича #24, §12.4) ────────────────────────
// Цикл обучения по инцидентам: курс → тест (порог 18/20) → повтор за 30 дней.
// Данные СИНТЕТИЧЕСКИЕ (датасета обучения нет) → обязательный бейдж демо (§12.0).
// Состояния: loading/error — секцию тихо скрыть (отчёт не ломать); пустые
// назначения — «обучение не назначалось» (пустота информативна, секцию не прятать).

const COACHING_STATUS: Record<
  CoachingStatus,
  { label: string; icon: typeof Check; cls: string }
> = {
  passed: { label: 'Сдан', icon: Check, cls: 'bg-ok-bg text-ok-text' },
  failed: { label: 'Провален', icon: X, cls: 'bg-critical-bg text-critical-text' },
  incomplete: { label: 'Не завершён', icon: Clock, cls: 'bg-warning-bg text-warning-text' },
}

/** ratio ∈ [0,1] → целые проценты (KPI обучения, §12.3). */
function ratioPct(ratio: number): number {
  return Math.round(ratio * 100)
}

/** Статус-чип: иконка + текст (a11y — не только цветом, §12.4/§31). */
function CoachingStatusChip({ status }: { status: CoachingStatus }) {
  const s = COACHING_STATUS[status]
  const Icon = s.icon
  return (
    <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium ${s.cls}`}>
      <Icon className="h-3.5 w-3.5" aria-hidden />
      {s.label}
    </span>
  )
}

function CoachingKpiChip({ label, value, danger }: { label: string; value: number; danger?: boolean }) {
  return (
    <div className={`rounded-md border px-3 py-2 ${danger ? 'border-critical-border bg-critical-bg' : 'border-border bg-surface'}`}>
      <div className="text-[11px] uppercase tracking-wide text-muted">{label}</div>
      <div className={`mt-0.5 text-lg font-bold tabular-nums ${danger ? 'text-critical-text' : 'text-ink'}`}>
        {value}%
      </div>
    </div>
  )
}

const COACHING_COLUMNS: Column<CoachingAssignment>[] = [
  {
    id: 'course',
    header: 'Курс',
    cell: (r) => (
      <div>
        <div className="font-medium text-ink">{r.course_title_ru}</div>
        <div className="text-[11px] tabular-nums text-muted">{r.course_id}</div>
      </div>
    ),
  },
  {
    id: 'period',
    header: 'Назначено / дедлайн',
    cell: (r) => (
      <span className="tabular-nums text-muted">
        {formatTime(r.assigned_at)} → {formatTime(r.due_at)}
      </span>
    ),
  },
  {
    id: 'score',
    header: 'Балл',
    align: 'center',
    cell: (r) => <span className="tabular-nums text-ink">{r.test_score}/20</span>,
  },
  { id: 'status', header: 'Статус', cell: (r) => <CoachingStatusChip status={r.status} /> },
  {
    id: 'repeat',
    header: 'Повтор за 30 дней',
    align: 'center',
    cell: (r) =>
      r.repeat_within_30d ? (
        <span
          className="inline-flex items-center gap-1 text-critical-text"
          title="Повторное нарушение того же типа в окне ±30 дней"
        >
          <TriangleAlert className="h-3.5 w-3.5" aria-hidden /> Да
        </span>
      ) : (
        <span className="text-muted" aria-label="Без повтора">—</span>
      ),
  },
]

function CoachingSection({ plate }: { plate: string }) {
  const navigate = useNavigate()
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [card, setCard] = useState<CoachingCard | null>(null)

  useEffect(() => {
    let active = true
    setState('loading')
    setCard(null)
    client
      .getCoaching(plate)
      .then((c) => {
        if (!active) return
        setCard(c)
        setState('ready')
      })
      .catch(() => {
        if (active) setState('error')
      })
    return () => {
      active = false
    }
  }, [plate])

  // loading / error — секцию тихо скрыть (§12.4: отчёт не ломать).
  if (state !== 'ready' || !card) return null

  const { kpi, assignments } = card
  return (
    <Card className="p-0">
      <div className="flex flex-wrap items-center gap-2 border-b border-border px-4 py-3">
        <GraduationCap className="h-4 w-4 text-primary" aria-hidden />
        <h3 className="text-sm font-semibold text-ink">Обучение водителя</h3>
        {/* Бейдж синтетики — обязателен (§12.0), warning-тон, рядом с заголовком. */}
        {card.synthetic && (
          <span className="inline-flex items-center gap-1 rounded bg-warning-bg px-2 py-0.5 text-xs font-medium text-warning-text">
            <FlaskConical className="h-3.5 w-3.5" aria-hidden />
            синтетические данные (демо)
          </span>
        )}
      </div>

      <div className="space-y-4 p-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <CoachingKpiChip label="Завершение" value={ratioPct(kpi.completion_rate)} />
          <CoachingKpiChip label="Сдача теста" value={ratioPct(kpi.pass_rate)} />
          <CoachingKpiChip
            label="Повторные нарушения"
            value={ratioPct(kpi.repeat_violation_rate)}
            danger={kpi.repeat_violation_rate > 0}
          />
        </div>

        {assignments.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-8 text-center text-muted">
            <Inbox className="h-7 w-7" aria-hidden />
            <p className="text-sm">Обучение не назначалось</p>
          </div>
        ) : (
          <DataTable
            columns={COACHING_COLUMNS}
            rows={assignments}
            rowKey={(r) => r.assignment_id}
            onRowClick={(r) => navigate(`/incidents/${r.incident_id}`)}
            emptyLabel="Обучение не назначалось"
          />
        )}
      </div>
    </Card>
  )
}

// ── Дашборды ──────────────────────────────────────────────────────────────────

function DriverDashboard({
  report,
  selectedId,
  onOpen,
  onCursor,
}: {
  report: DriverReport
  selectedId?: string
  onOpen: (row: ViolationRow) => void
  onCursor: (id: string) => void
}) {
  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-ink">{report.driver.driver_name}</h2>
            <p className="text-sm text-muted">
              {report.vehicle_model} · {report.vehicle_plate} · {report.mileage_km.toLocaleString('ru-RU')} км ·{' '}
              {report.trips} рейсов · рейтинг{' '}
              <span className="font-medium tabular-nums text-ink">{report.driver.safety_score}</span>
            </p>
          </div>
          {report.disciplinary_warning && (
            <span className="inline-flex items-center gap-1.5 rounded-md bg-critical-bg px-3 py-1.5 text-xs font-semibold text-critical-text">
              <TriangleAlert className="h-3.5 w-3.5" aria-hidden />
              Дисциплинарное взыскание
            </span>
          )}
        </div>
        <div className="mt-4">
          <KpiRow kpi={report.kpi} />
        </div>
      </Card>

      {/* f16 · прогноз риска + рекомендации (идея #12) */}
      <ForecastCard plate={report.vehicle_plate} />

      <Card className="p-0">
        <div className="border-b border-border px-4 py-3 text-sm font-semibold text-ink">
          Нарушения <span className="font-normal text-muted">— клик/Enter по строке открывает видео</span>
        </div>
        {report.violations.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-12 text-center text-muted">
            <Inbox className="h-8 w-8" aria-hidden />
            <p className="text-sm">Нарушений за период не найдено</p>
          </div>
        ) : (
          <ViolationsTable rows={report.violations} selectedId={selectedId} onOpen={onOpen} onCursor={onCursor} />
        )}
      </Card>

      {/* f27 · секция «Обучение водителя» (§12.4) — после KPI-блоков; синтетика-демо. */}
      <CoachingSection plate={report.vehicle_plate} />
    </div>
  )
}

function FleetDashboard({
  report,
  view,
  onView,
  onDrill,
}: {
  report: FleetReport
  view: 'drivers' | 'vehicles'
  onView: (v: 'drivers' | 'vehicles') => void
  // w3-12 · drill строки парка → отчёт по водителю (re-query через runQuery).
  onDrill: (driverName: string) => void
}) {
  const empty = view === 'drivers' ? report.by_drivers.length === 0 : report.by_vehicles.length === 0
  // f16 · сводный прогноз/интервенции — фокус на ТС с наибольшим риском по парку.
  const topVehicle = useMemo(() => {
    if (report.by_vehicles.length === 0) return null
    return report.by_vehicles.reduce((max, r) => (r.risk_score > max.risk_score ? r : max))
  }, [report.by_vehicles])
  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-ink">
            Парк · {report.vehicles_count} ТС
            <span className="ml-2 text-sm font-normal text-muted">
              {formatDate(report.period.from)} – {formatDate(report.period.to)}
            </span>
          </h2>
          {/* Toggle «По водителям | По ТС» (ReportQuery.view) */}
          <div className="inline-flex rounded-md border border-border p-0.5" role="group" aria-label="Представление парка">
            <button
              type="button"
              onClick={() => onView('drivers')}
              aria-pressed={view === 'drivers'}
              className={`inline-flex items-center gap-1.5 rounded px-3 py-1 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${view === 'drivers' ? 'bg-primary text-white' : 'text-muted hover:text-ink'}`}
            >
              <Users className="h-3.5 w-3.5" aria-hidden /> По водителям
            </button>
            <button
              type="button"
              onClick={() => onView('vehicles')}
              aria-pressed={view === 'vehicles'}
              className={`inline-flex items-center gap-1.5 rounded px-3 py-1 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${view === 'vehicles' ? 'bg-primary text-white' : 'text-muted hover:text-ink'}`}
            >
              <Truck className="h-3.5 w-3.5" aria-hidden /> По ТС
            </button>
          </div>
        </div>
        <div className="mt-4">
          <KpiRow kpi={report.kpi} />
        </div>
      </Card>

      {/* f16 · сводный прогноз/интервенции по самому рискованному ТС парка */}
      {topVehicle && (
        <ForecastCard
          plate={topVehicle.plate}
          title="Сводный прогноз парка"
          subtitle={`фокус: ${topVehicle.vehicle_model} · ${topVehicle.plate} (риск ${topVehicle.risk_score})`}
        />
      )}

      <Card className="p-0">
        <div className="border-b border-border px-4 py-3 text-sm font-semibold text-ink">
          {view === 'drivers' ? 'Рейтинг водителей' : 'Рейтинг ТС'}
          <span className="font-normal text-muted"> — клик по строке открывает отчёт водителя</span>
        </div>
        {empty ? (
          <div className="flex flex-col items-center gap-2 py-12 text-center text-muted">
            <Inbox className="h-8 w-8" aria-hidden />
            <p className="text-sm">Данных за период нет</p>
          </div>
        ) : view === 'drivers' ? (
          <DataTable
            columns={FLEET_DRIVER_COLUMNS}
            rows={report.by_drivers}
            rowKey={(r) => r.driver.driver_id}
            onRowClick={(r) => onDrill(r.driver.driver_name)}
          />
        ) : (
          <DataTable
            columns={FLEET_VEHICLE_COLUMNS}
            rows={report.by_vehicles}
            rowKey={(r) => r.plate}
            onRowClick={(r) => onDrill(r.main_driver)}
          />
        )}
      </Card>
    </div>
  )
}

// ── Экран ─────────────────────────────────────────────────────────────────────

export default function Report() {
  const [searchParams, setSearchParams] = useSearchParams()

  const [text, setText] = useState('')
  const [voiceState, setVoiceState] = useState<VoiceButtonState>('idle')
  const [sttError, setSttError] = useState<string | null>(null)
  const [lowConfidence, setLowConfidence] = useState(false)

  const [queryLoading, setQueryLoading] = useState(false)
  const [queryError, setQueryError] = useState<string | null>(null)
  const [pending, setPending] = useState<QueryResult | null>(null)
  const [modalOpen, setModalOpen] = useState(false)

  const [result, setResult] = useState<QueryResult | null>(null)
  const [fleetView, setFleetView] = useState<'drivers' | 'vehicles'>('drivers')

  const [videoSel, setVideoSel] = useState<{ id: string; source: Source | null } | null>(null)
  const [videoState, setVideoState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [videoIncident, setVideoIncident] = useState<IncidentDetail | null>(null)
  const [videoError, setVideoError] = useState<string | null>(null)

  const inputRef = useRef<HTMLInputElement>(null)
  // Голос реален только в защищённом контексте (https/localhost) с поддержкой getUserMedia.
  const voiceAvailable =
    typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia && (typeof window === 'undefined' || window.isSecureContext)

  const report = result?.report ?? null

  // ── Запись на доступ к URL (shareable deep-link, полиш §2) ──────────────────
  const writeParams = useCallback(
    (patch: { q?: string | null; sel?: string | null }) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          if (patch.q !== undefined) {
            if (patch.q) next.set('q', patch.q)
            else next.delete('q')
          }
          if (patch.sel !== undefined) {
            if (patch.sel) next.set('sel', patch.sel)
            else next.delete('sel')
          }
          return next
        },
        { replace: true },
      )
    },
    [setSearchParams],
  )

  // ── Видео-панель (killer-feature) ───────────────────────────────────────────
  const openVideo = useCallback(
    (row: { id: string; source: Source | null }) => {
      setVideoSel(row)
      setVideoState('loading')
      setVideoIncident(null)
      setVideoError(null)
      writeParams({ sel: row.id })
      client
        .getIncident(row.id)
        .then((inc) => {
          setVideoIncident(inc)
          setVideoState('ready')
        })
        .catch((e: unknown) => {
          setVideoError(humanError(e))
          setVideoState('error')
        })
    },
    [writeParams],
  )

  const closeVideo = useCallback(() => {
    setVideoSel(null)
    setVideoIncident(null)
    setVideoState('loading')
    writeParams({ sel: null })
  }, [writeParams])

  // ── NLU-запрос ──────────────────────────────────────────────────────────────
  const runQuery = useCallback(
    async (raw: string, opts?: { auto?: boolean }): Promise<QueryResult | null> => {
      const value = raw.trim()
      if (!value) return null
      setQueryLoading(true)
      setQueryError(null)
      setModalOpen(false)
      try {
        const res = await voice.queryReport(value)
        if (opts?.auto) {
          // Deep-link / детерминизм демо: сразу строим дашборд без модалки.
          setResult(res)
          setFleetView(res.query.view ?? 'drivers')
          setPending(null)
          writeParams({ q: value })
        } else {
          setPending(res)
          setModalOpen(true)
        }
        return res
      } catch (e: unknown) {
        setQueryError(`Запрос не распознан (${humanError(e)}). Исправьте формулировку и повторите.`)
        return null
      } finally {
        setQueryLoading(false)
      }
    },
    [writeParams],
  )

  const confirmQuery = useCallback(() => {
    if (!pending) return
    setResult(pending)
    setFleetView(pending.query.view ?? 'drivers')
    setModalOpen(false)
    setPending(null)
    writeParams({ q: text.trim() })
  }, [pending, text, writeParams])

  const editQuery = useCallback(() => {
    setModalOpen(false)
    setPending(null)
    inputRef.current?.focus()
  }, [])

  // w3-12 · drill строки парка → отчёт по водителю (re-query через существующий runQuery).
  const drillFleet = useCallback(
    (driverName: string) => {
      if (!driverName) return
      setText(driverName)
      void runQuery(driverName, { auto: true })
    },
    [runQuery],
  )

  // ── Голос → текст ────────────────────────────────────────────────────────────
  const onRecorded = useCallback(async (blob: Blob) => {
    setVoiceState('processing')
    setSttError(null)
    setLowConfidence(false)
    try {
      const t = await voice.transcribe(blob)
      setText(t.text)
      setLowConfidence(t.confidence < LOW_CONFIDENCE)
    } catch (e: unknown) {
      setSttError(`Распознавание недоступно (${humanError(e)}). Введите запрос текстом.`)
    } finally {
      setVoiceState('idle')
    }
  }, [])

  // ── Восстановление состояния из deep-link (один раз при монтировании) ────────
  const restoredRef = useRef(false)
  useEffect(() => {
    if (restoredRef.current) return
    restoredRef.current = true
    const q0 = searchParams.get('q')
    const sel0 = searchParams.get('sel')
    if (!q0) return
    setText(q0)
    void runQuery(q0, { auto: true }).then((res) => {
      if (!sel0 || !res) return
      const r = res.report
      const row = isDriverReport(r) ? r.violations.find((v) => v.id === sel0) : undefined
      openVideo({ id: sel0, source: row?.source ?? null })
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const showSkeleton = queryLoading && !result
  const showHero = !result && !queryLoading && !queryError

  return (
    <div className="relative mx-auto max-w-5xl space-y-4">
      {/* ── Голос + NL-запрос ─────────────────────────────────────────────────── */}
      <Card>
        <h1 className="text-lg font-semibold text-ink">Голосовая аналитика</h1>
        <p className="mt-0.5 text-sm text-muted">
          Надиктуйте или введите запрос — например «дисциплина Иванова за неделю» или «грубые нарушения по парку».
        </p>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          {voiceAvailable && (
            <VoiceButton
              state={voiceState}
              onRecorded={onRecorded}
              onStart={() => setVoiceState('recording')}
              disabled={queryLoading}
            />
          )}

          <div className="flex min-w-[16rem] flex-1 items-center gap-2 rounded-md border border-border bg-surface px-3 focus-within:border-primary">
            <Search className="h-4 w-4 shrink-0 text-muted" aria-hidden />
            <input
              ref={inputRef}
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && runQuery(text)}
              placeholder="Сформулируйте запрос…"
              aria-label="Текст запроса"
              className="h-10 flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-muted"
            />
          </div>

          <Button variant="primary" icon={Sparkles} loading={queryLoading} onClick={() => runQuery(text)} disabled={!text.trim()}>
            Построить
          </Button>
        </div>

        {/* Честная деградация голоса (полиш §6) */}
        {!voiceAvailable && (
          <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-muted">
            <Info className="h-3.5 w-3.5" aria-hidden />
            Голосовой ввод недоступен (нужен микрофон и защищённое соединение). Введите запрос текстом — это полноценная альтернатива.
          </p>
        )}
        {sttError && (
          <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-high-text">
            <TriangleAlert className="h-3.5 w-3.5" aria-hidden />
            {sttError}
          </p>
        )}
        {lowConfidence && !sttError && (
          <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-high-text">
            <Info className="h-3.5 w-3.5" aria-hidden />
            Низкая уверенность распознавания — проверьте и при необходимости отредактируйте текст.
          </p>
        )}
      </Card>

      {/* ── Состояния дашборда: loading / error / ready / idle ────────────────── */}
      {showSkeleton && <DashboardSkeleton />}

      {queryError && !queryLoading && (
        <ErrorBlock message={queryError} onRetry={() => runQuery(text)} />
      )}

      {report && !queryLoading && (
        isDriverReport(report) ? (
          <DriverDashboard
            report={report}
            selectedId={videoSel?.id}
            onOpen={(row) => openVideo({ id: row.id, source: row.source })}
            onCursor={(id) => setVideoSel({ id, source: report.violations.find((v) => v.id === id)?.source ?? null })}
          />
        ) : (
          <FleetDashboard report={report} view={fleetView} onView={setFleetView} onDrill={drillFleet} />
        )
      )}

      {showHero && (
        <Card className="grid place-items-center py-16 text-center">
          <Sparkles className="h-10 w-10 text-border" aria-hidden />
          <p className="mt-2 max-w-sm text-sm text-muted">
            Постройте отчёт голосом или текстом. По нарушению водителя клик откроет видео справа.
          </p>
        </Card>
      )}

      {/* ── Секция «Саботаж» (f12, идея #9) ───────────────────────────────────── */}
      <div className="border-t border-border pt-4">
        <SabotageWidget variant="full" />
      </div>

      {/* ── Подтверждение разбора NLU (d5) ────────────────────────────────────── */}
      {pending && (
        <ConfirmationModal
          open={modalOpen}
          query={pending.query}
          onConfirm={confirmQuery}
          onEdit={editQuery}
          onClose={editQuery}
        />
      )}

      {/* ── Killer-feature: видео справа (§6) ──────────────────────────────────── */}
      {videoSel && (
        <VideoPanel
          state={videoState}
          incident={videoIncident}
          source={videoSel.source}
          error={videoError}
          onClose={closeVideo}
          onRetry={() => openVideo(videoSel)}
        />
      )}
    </div>
  )
}
