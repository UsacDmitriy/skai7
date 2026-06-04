import { useCallback, useState } from 'react'
import { Mic, Search, Sparkles, TriangleAlert, X } from 'lucide-react'
import * as client from '@/api/client'
import { ApiError } from '@/api/client'
import type {
  DriverReport,
  FleetByDriverRow,
  FleetReport,
  IncidentDetail,
  ReportKPI,
  Severity,
  ViolationRow,
} from '@/api/types'
import {
  Button,
  Card,
  type Column,
  DataTable,
  ScoreBar,
  SeverityBadge,
  VideoPlayer,
} from '@/components'

/**
 * f4 · Интерактивный отчёт (scaffold). Маршрут `/report` · референс `ui/05 Интерактивный отчёт/`.
 * NL-запрос → `client.queryReport(text)`; рендер DriverReport/FleetReport (KPI + DataTable).
 * Killer-feature (idea #2): клик по строке нарушения → выезжающая панель с VideoPlayer.
 * Голосовой ввод — кнопка-заглушка (# TODO Whisper, см. f2 client.transcribe).
 */

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: 'Критично',
  high: 'Высокий',
  medium: 'Средний',
  low: 'Низкий',
}

function isDriverReport(r: DriverReport | FleetReport): r is DriverReport {
  return 'violations' in r
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

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

// ── Колонки таблиц ────────────────────────────────────────────────────────────

const VIOLATION_COLUMNS: Column<ViolationRow>[] = [
  { id: 'ts', header: 'Время', cell: (r) => <span className="tabular-nums text-muted">{formatTime(r.ts)}</span>, sortable: true, sortValue: (r) => r.ts },
  { id: 'label', header: 'Нарушение', cell: (r) => <span className="font-medium text-ink">{r.alarm_label_ru}</span> },
  { id: 'severity', header: 'Severity', cell: (r) => <SeverityBadge severity={r.severity} label={SEVERITY_LABEL[r.severity]} /> },
  { id: 'gross', header: 'Грубое', align: 'center', cell: (r) => (r.is_gross ? <span className="text-critical-text">●</span> : <span className="text-muted">—</span>), sortable: true, sortValue: (r) => (r.is_gross ? 1 : 0) },
]

const DRIVER_COLUMNS: Column<FleetByDriverRow>[] = [
  { id: 'driver', header: 'Водитель', cell: (r) => <span className="font-medium text-ink">{r.driver.driver_name}</span> },
  { id: 'vehicle', header: 'ТС', cell: (r) => `${r.vehicle_model} · ${r.vehicle_plate}` },
  { id: 'risk', header: 'Риск', align: 'right', cell: (r) => <ScoreBar score={r.risk_score} className="w-28" />, sortable: true, sortValue: (r) => r.risk_score },
  { id: 'gross', header: 'Грубых', align: 'right', cell: (r) => <span className="tabular-nums">{r.gross}</span>, sortable: true, sortValue: (r) => r.gross },
  { id: 'total', header: 'Всего', align: 'right', cell: (r) => <span className="tabular-nums">{r.total}</span>, sortable: true, sortValue: (r) => r.total },
]

export default function Report() {
  const [text, setText] = useState('')
  const [report, setReport] = useState<DriverReport | FleetReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Выезжающая видео-панель (idea #2).
  const [videoIncident, setVideoIncident] = useState<IncidentDetail | null>(null)
  const [videoLoading, setVideoLoading] = useState(false)
  const [selectedRow, setSelectedRow] = useState<string | undefined>(undefined)

  const runQuery = useCallback(async () => {
    if (!text.trim()) return
    setLoading(true)
    setError(null)
    try {
      const { report } = await client.queryReport(text)
      setReport(report)
    } catch (e: unknown) {
      const msg = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Ошибка'
      setError(`NL-запрос недоступен (${msg}). Используйте быстрые отчёты ниже.`)
    } finally {
      setLoading(false)
    }
  }, [text])

  // Быстрые демо-отчёты (работают и на фикстурах — driverReport/fleetReport замоканы).
  const loadDriver = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setReport(await client.driverReport('А777ВВ 77'))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Ошибка')
    } finally {
      setLoading(false)
    }
  }, [])

  const loadFleet = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setReport(await client.fleetReport('drivers'))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Ошибка')
    } finally {
      setLoading(false)
    }
  }, [])

  const openVideo = useCallback((incidentId: string) => {
    setSelectedRow(incidentId)
    setVideoLoading(true)
    setVideoIncident(null)
    client
      .getIncident(incidentId)
      .then(setVideoIncident)
      .catch(() => setVideoIncident(null))
      .finally(() => setVideoLoading(false))
  }, [])

  return (
    <div className="relative mx-auto max-w-5xl space-y-4">
      {/* ── NL-запрос ───────────────────────────────────────────────────────── */}
      <Card>
        <h1 className="text-lg font-semibold text-ink">Интерактивный отчёт</h1>
        <p className="mt-0.5 text-sm text-muted">
          Запрос на естественном языке — например «дисциплина Иванова за неделю» или «грубые нарушения по парку».
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <div className="flex flex-1 items-center gap-2 rounded-md border border-border bg-surface px-3">
            <Search className="h-4 w-4 shrink-0 text-muted" aria-hidden />
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && runQuery()}
              placeholder="Сформулируйте запрос…"
              className="h-9 flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-muted"
            />
            {/* TODO Whisper: голосовой ввод через client.transcribe() (§7.4). */}
            <button
              type="button"
              title="Голосовой ввод (TODO Whisper)"
              className="grid h-7 w-7 place-items-center rounded text-muted hover:bg-bg hover:text-ink"
            >
              <Mic className="h-4 w-4" aria-hidden />
            </button>
          </div>
          <Button variant="primary" icon={Sparkles} loading={loading} onClick={runQuery}>
            Построить
          </Button>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted">
          Быстрые отчёты:
          <Button variant="secondary" onClick={loadDriver} className="h-7 px-2 text-xs">
            По водителю
          </Button>
          <Button variant="secondary" onClick={loadFleet} className="h-7 px-2 text-xs">
            По парку
          </Button>
        </div>
        {error && (
          <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-high-text">
            <TriangleAlert className="h-3.5 w-3.5" aria-hidden />
            {error}
          </p>
        )}
      </Card>

      {/* ── Результат ───────────────────────────────────────────────────────── */}
      {report && isDriverReport(report) && (
        <div className="space-y-4">
          <Card>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-ink">{report.driver.driver_name}</h2>
                <p className="text-sm text-muted">
                  {report.vehicle_model} · {report.vehicle_plate} · {report.mileage_km.toLocaleString('ru-RU')} км ·{' '}
                  {report.trips} поездок
                </p>
              </div>
              {report.disciplinary_warning && (
                <span className="inline-flex items-center gap-1.5 rounded-md bg-critical-bg px-3 py-1.5 text-xs font-semibold text-critical-text">
                  <TriangleAlert className="h-3.5 w-3.5" aria-hidden />
                  Дисциплинарное предупреждение
                </span>
              )}
            </div>
            <div className="mt-4">
              <KpiRow kpi={report.kpi} />
            </div>
          </Card>
          <Card className="p-0">
            <div className="border-b border-border px-4 py-3 text-sm font-semibold text-ink">
              Нарушения <span className="font-normal text-muted">— клик по строке открывает видео</span>
            </div>
            <DataTable
              columns={VIOLATION_COLUMNS}
              rows={report.violations}
              rowKey={(r) => r.id}
              selectedKey={selectedRow}
              onRowClick={(r) => openVideo(r.id)}
              emptyLabel="Нарушений нет"
            />
          </Card>
        </div>
      )}

      {report && !isDriverReport(report) && (
        <div className="space-y-4">
          <Card>
            <h2 className="text-base font-semibold text-ink">
              Парк · {report.vehicles_count} ТС
              <span className="ml-2 text-sm font-normal text-muted">
                {report.period.from} – {report.period.to}
              </span>
            </h2>
            <div className="mt-4">
              <KpiRow kpi={report.kpi} />
            </div>
          </Card>
          <Card className="p-0">
            <div className="border-b border-border px-4 py-3 text-sm font-semibold text-ink">
              Рейтинг водителей
            </div>
            <DataTable
              columns={DRIVER_COLUMNS}
              rows={report.by_drivers}
              rowKey={(r) => r.driver.driver_id}
            />
          </Card>
        </div>
      )}

      {!report && !loading && (
        <Card className="grid place-items-center py-16 text-center">
          <Sparkles className="h-10 w-10 text-border" aria-hidden />
          <p className="mt-2 text-sm text-muted">
            Постройте отчёт по NL-запросу или выберите быстрый отчёт выше.
          </p>
        </Card>
      )}

      {/* ── Выезжающая видео-панель (idea #2) ───────────────────────────────── */}
      {(videoIncident || videoLoading) && (
        <>
          <div
            className="fixed inset-0 z-30 bg-ink/30"
            onClick={() => {
              setVideoIncident(null)
              setSelectedRow(undefined)
            }}
            aria-hidden
          />
          <aside className="fixed right-0 top-0 z-40 flex h-full w-full max-w-md flex-col gap-4 overflow-y-auto border-l border-border bg-surface p-5 shadow-xl">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-ink">Видео нарушения</h3>
              <button
                type="button"
                onClick={() => {
                  setVideoIncident(null)
                  setSelectedRow(undefined)
                }}
                className="grid h-7 w-7 place-items-center rounded text-muted hover:bg-bg hover:text-ink"
                aria-label="Закрыть"
              >
                <X className="h-4 w-4" aria-hidden />
              </button>
            </div>
            {videoLoading && <p className="text-sm text-muted">Загрузка…</p>}
            {videoIncident && (
              <>
                <div>
                  <div className="text-sm font-medium text-ink">{videoIncident.alarm_label_ru}</div>
                  <div className="mt-0.5 text-xs text-muted">
                    {videoIncident.vehicle_plate} · {formatTime(videoIncident.ts)}
                  </div>
                </div>
                <VideoPlayer src={videoIncident.cam_front_url ?? undefined} />
                <VideoPlayer src={videoIncident.cam_dms_url ?? undefined} />
                <p className="text-xs text-muted">{videoIncident.evidence_summary}</p>
              </>
            )}
          </aside>
        </>
      )}
    </div>
  )
}
