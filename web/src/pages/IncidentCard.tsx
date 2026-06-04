import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  AlertTriangle,
  Archive,
  CheckCircle2,
  ClipboardList,
  MapPin,
  OctagonX,
  Phone,
  ShieldCheck,
  VideoOff,
} from 'lucide-react'
import * as client from '@/api/client'
import { ApiError } from '@/api/client'
import type {
  ActionType,
  Camera,
  CameraStatus,
  IncidentDetail,
  Severity,
  Source,
  Status,
  VideoChannel,
} from '@/api/types'
import {
  Button,
  Card,
  ScoreBar,
  SeverityBadge,
  TelemetryChart,
  VideoPlayer,
} from '@/components'
import { cn } from '@/components/ui/cn'

/**
 * f4 · Карточка инцидента (P0, сквозной flow на f2-клиенте).
 * Маршрут `/incidents/:id` · контракт §3 · референс `ui/03 Карточка инцидента/`.
 *
 * Ключевой демо-эффект (idea #1, §6): синхронизация видео↔телеметрия.
 * `currentSec` (из VideoPlayer.onTimeUpdate переднего плеера) проецируется в
 * `playheadOffset` графика; клик по графику → общий `seekTo` на обоих плеерах.
 */

// ── Словари маппинга enum → ярлык (контракт §3.1) ─────────────────────────────

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: 'Критично',
  high: 'Высокий',
  medium: 'Средний',
  low: 'Низкий',
}

/** COMBINED → «Оба источника», DIAGNOSTIC → диагностика (contract-change #1). */
const SOURCE_LABEL: Record<Source, string> = {
  DMS: 'DMS · видеоаналитика салона',
  ADAS: 'ADAS · фронтальная',
  TELEMATICS: 'Телематика',
  COMBINED: 'Оба источника (DMS + телематика)',
  DIAGNOSTIC: '⚙ Диагностика (камера офлайн)',
}

const STATUS_LABEL: Record<Status, string> = {
  active: 'Активен',
  in_progress: 'В работе',
  validated: 'Подтверждён',
  closed: 'Закрыт',
}

const CAMERA_STATUS: Record<CameraStatus, { label: string; dot: string; text: string }> = {
  online: { label: 'Онлайн', dot: 'bg-ok', text: 'text-ok-text' },
  offline: { label: 'Офлайн', dot: 'bg-critical', text: 'text-critical-text' },
  warning: { label: 'Нестабильна', dot: 'bg-warning', text: 'text-warning-text' },
}

// ── Форматтеры ────────────────────────────────────────────────────────────────

function formatDateTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

// ── Описание панели действий (idea-агностично, из контракта §3.4) ─────────────

type ActionSpec = {
  action: ActionType
  label: string
  variant: 'primary' | 'secondary' | 'danger'
  icon: typeof CheckCircle2
}

const ACTIONS: ActionSpec[] = [
  { action: 'mark_reviewed', label: 'Проверено', variant: 'secondary', icon: CheckCircle2 },
  { action: 'create_task', label: 'Создать заявку', variant: 'primary', icon: ClipboardList },
  { action: 'call_driver', label: 'Позвонить водителю', variant: 'secondary', icon: Phone },
  { action: 'validate', label: 'Валидация', variant: 'primary', icon: ShieldCheck },
  { action: 'stop_vehicle', label: 'Стоп ТС', variant: 'danger', icon: OctagonX },
]

// ── Подкомпоненты ─────────────────────────────────────────────────────────────

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <div className="text-[11px] uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-0.5 truncate text-sm font-medium text-ink">{children}</div>
    </div>
  )
}

function CameraRow({ cam }: { cam: Camera }) {
  const meta = CAMERA_STATUS[cam.status]
  const window =
    cam.status !== 'online' && (cam.offline_from || cam.offline_to)
      ? `${formatTime(cam.offline_from)} – ${cam.offline_to ? formatTime(cam.offline_to) : 'сейчас'}`
      : null
  return (
    <div className="flex items-center justify-between gap-2 border-b border-border py-2 last:border-0">
      <span className="truncate text-sm text-ink">{cam.label}</span>
      <span className={cn('inline-flex shrink-0 items-center gap-1.5 text-xs font-medium', meta.text)}>
        {window && <span className="tabular-nums text-muted">{window}</span>}
        <span className={cn('h-1.5 w-1.5 rounded-full', meta.dot)} aria-hidden />
        {meta.label}
      </span>
    </div>
  )
}

// ── Экран ─────────────────────────────────────────────────────────────────────

export default function IncidentCard() {
  const { id = '' } = useParams<{ id: string }>()

  const [incident, setIncident] = useState<IncidentDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<{ status?: number; message: string } | null>(null)

  // Рантайм-статус (обновляется ответом POST /actions) поверх загруженного.
  const [statusOverride, setStatusOverride] = useState<Status | null>(null)
  const [pending, setPending] = useState<ActionType | null>(null)
  const [actionFeedback, setActionFeedback] = useState<string | null>(null)

  // Синхронизация видео↔телеметрия (idea #1).
  const [currentSec, setCurrentSec] = useState(0)
  const [seekSec, setSeekSec] = useState<number | undefined>(undefined)
  const chartBoxRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError(null)
    setIncident(null)
    setStatusOverride(null)
    setActionFeedback(null)
    client
      .getIncident(id)
      .then((data) => {
        if (alive) setIncident(data)
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

  // Окно телеметрии: [min..max] ts_offset — основа маппинга видео↔график.
  const span = useMemo(() => {
    const offsets = incident?.telemetry.map((p) => p.ts_offset) ?? []
    const min = offsets.length ? Math.min(...offsets) : 0
    const max = offsets.length ? Math.max(...offsets) : 0
    return { min, max, range: Math.max(1, max - min) }
  }, [incident])

  // Жёлтая метка события (t=0) в % длины ролика — для VideoPlayer.eventMarkerPct.
  const eventMarkerPct = useMemo(
    () => ((0 - span.min) / span.range) * 100,
    [span],
  )

  // Видео currentTime (сек от начала окна) → ts_offset графика.
  const playheadOffset = span.min + currentSec

  // Клик по графику → ts_offset → сек от начала окна → общий seekTo обоих плееров.
  const handleChartSeek = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const box = chartBoxRef.current
      if (!box) return
      const rect = box.getBoundingClientRect()
      const ratio = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width))
      const offset = span.min + ratio * span.range
      setSeekSec(offset - span.min)
    },
    [span],
  )

  const runAction = useCallback(
    async (action: ActionType) => {
      if (!incident) return
      setPending(action)
      setActionFeedback(null)
      try {
        const res = await client.postAction({ incident_id: incident.id, action, comment: '' })
        if (res.status) setStatusOverride(res.status)
        const label = ACTIONS.find((a) => a.action === action)?.label ?? action
        setActionFeedback(`Действие «${label}» отправлено${res.status ? ` · статус: ${STATUS_LABEL[res.status]}` : ''}`)
      } catch (e: unknown) {
        const msg = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Ошибка'
        setActionFeedback(`Не удалось выполнить действие: ${msg}`)
      } finally {
        setPending(null)
      }
    },
    [incident],
  )

  // ── Состояния loading / error / 404 ─────────────────────────────────────────
  if (loading) {
    return (
      <div className="grid h-full place-items-center">
        <div className="flex items-center gap-3 text-muted">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-border border-t-primary" />
          Загрузка инцидента…
        </div>
      </div>
    )
  }

  if (error || !incident) {
    const is404 = error?.status === 404
    return (
      <div className="grid h-full place-items-center">
        <Card className="max-w-md text-center">
          <AlertTriangle className="mx-auto h-8 w-8 text-high" aria-hidden />
          <h2 className="mt-3 text-lg font-semibold text-ink">
            {is404 ? 'Инцидент не найден' : 'Ошибка загрузки'}
          </h2>
          <p className="mt-1 text-sm text-muted">
            {is404 ? `Инцидент «${id}» не существует.` : error?.message}
          </p>
        </Card>
      </div>
    )
  }

  const inc = incident
  const status = statusOverride ?? inc.status
  const sensorNote =
    !inc.video_available && inc.sensor_active_after_sec != null
      ? `DMS-сенсор работал ещё +${inc.sensor_active_after_sec} сек после ухода камеры в offline`
      : null
  const offlineCam = inc.cameras.find((c) => c.status !== 'online' && c.offline_from)

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      {/* ── Топбар инцидента ────────────────────────────────────────────────── */}
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 space-y-2">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-xl font-semibold text-ink">{inc.alarm_label_ru}</h1>
              <SeverityBadge severity={inc.severity} label={SEVERITY_LABEL[inc.severity]} />
              <span className="rounded-md bg-bg px-2 py-0.5 text-xs font-medium text-muted">
                {STATUS_LABEL[status]}
              </span>
            </div>
            <div className="text-sm text-muted">{SOURCE_LABEL[inc.source]}</div>
          </div>
          <div className="w-48 shrink-0">
            <div className="text-[11px] uppercase tracking-wide text-muted">Риск-скор</div>
            <ScoreBar score={inc.risk_score} className="mt-1" />
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4 border-t border-border pt-4 sm:grid-cols-3 lg:grid-cols-4">
          <Field label="ТС">
            {inc.vehicle_model} · {inc.vehicle_plate}
          </Field>
          <Field label="Водитель">{inc.driver}</Field>
          <Field label="Регион">{inc.driver_region}</Field>
          <Field label="Safety-score водителя">
            <span className="tabular-nums">{inc.driver_safety_score}</span> / 100
          </Field>
          <Field label="Время события">{formatDateTime(inc.ts)}</Field>
          <Field label="Скорость">
            {inc.speed_kmh} км/ч{' '}
            <span className="text-muted">(лимит {inc.speed_limit_kmh})</span>
          </Field>
          <div className="col-span-2 min-w-0">
            <div className="text-[11px] uppercase tracking-wide text-muted">Адрес</div>
            <div className="mt-0.5 flex items-center gap-1 truncate text-sm font-medium text-ink">
              <MapPin className="h-3.5 w-3.5 shrink-0 text-muted" aria-hidden />
              {inc.address ?? '—'}
            </div>
          </div>
        </div>
      </Card>

      {/* ── Блок причины ────────────────────────────────────────────────────── */}
      <Card>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Причина</h2>
        <p className="mt-2 text-sm leading-relaxed text-ink">{inc.evidence_summary}</p>
        {inc.event_version && (
          <div className="mt-3 rounded-md border border-border bg-bg px-3 py-2">
            <div className="text-xs text-muted">
              Версия события · уверенность{' '}
              <span className="font-semibold tabular-nums text-ink">{inc.confidence}%</span>
            </div>
            <p className="mt-0.5 text-sm text-ink">{inc.event_version}</p>
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* ── Видео + телеметрия ────────────────────────────────────────────── */}
        <div className="space-y-4 lg:col-span-2">
          <Card>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
              Видеодоказательства
            </h2>

            {inc.video_available ? (
              <>
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <div className="space-y-1">
                    <VideoPlayer
                      src={inc.cam_front_url ? client.videoUrl(inc.id, 1) : undefined}
                      eventMarkerPct={eventMarkerPct}
                      onTimeUpdate={setCurrentSec}
                      seekTo={seekSec}
                    />
                    <span className="text-xs text-muted">ADAS · фронтальная</span>
                  </div>
                  <div className="space-y-1">
                    <VideoPlayer
                      src={inc.cam_dms_url ? client.videoUrl(inc.id, 5) : undefined}
                      eventMarkerPct={eventMarkerPct}
                      seekTo={seekSec}
                    />
                    <span className="text-xs text-muted">DMS · салон</span>
                  </div>
                </div>
                {inc.cam_extra.length > 0 && (
                  <div className="mt-3">
                    <div className="mb-1 text-xs font-medium text-muted">Другие камеры</div>
                    <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                      {inc.cam_extra.map((cam) => (
                        <div key={cam.channel} className="space-y-1">
                          <VideoPlayer
                            src={client.videoUrl(inc.id, cam.channel as VideoChannel)}
                            seekTo={seekSec}
                          />
                          <span className="text-xs text-muted">Канал {cam.channel}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="flex flex-col items-center justify-center gap-3 rounded-md border border-dashed border-border bg-bg py-10 text-center">
                <VideoOff className="h-8 w-8 text-muted" aria-hidden />
                <div>
                  <div className="text-sm font-medium text-ink">Видео недоступно</div>
                  <p className="mt-1 max-w-sm text-xs text-muted">
                    Камера не передала запись в архив.
                    {offlineCam &&
                      ` Окно offline: ${formatTime(offlineCam.offline_from)} – ${
                        offlineCam.offline_to ? formatTime(offlineCam.offline_to) : 'сейчас'
                      }.`}
                  </p>
                  {sensorNote && (
                    <p className="mt-1 max-w-sm text-xs font-medium text-high-text">{sensorNote}</p>
                  )}
                </div>
                <Button
                  variant="secondary"
                  icon={Archive}
                  loading={pending === 'request_archive'}
                  onClick={() => runAction('request_archive')}
                >
                  Запросить архив
                </Button>
              </div>
            )}
          </Card>

          <Card>
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
                Телеметрия
              </h2>
              <span className="text-xs text-muted">
                клик по графику — перемотка обоих плееров
              </span>
            </div>
            {/* Оверлей-клик: вычисляет ts_offset из позиции курсора, не трогая d2-примитив. */}
            <div ref={chartBoxRef} onClick={handleChartSeek} className="cursor-crosshair">
              <TelemetryChart data={inc.telemetry} playheadOffset={playheadOffset} />
            </div>
            <p className="mt-2 text-xs text-muted">
              Жёлтая пунктирная вертикаль — маркер события (t=0). Синяя — текущее время видео.
            </p>
          </Card>
        </div>

        {/* ── Камеры + действия ──────────────────────────────────────────────── */}
        <div className="space-y-4">
          <Card>
            <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-muted">
              Камеры
            </h2>
            {inc.cameras.map((cam) => (
              <CameraRow key={cam.id} cam={cam} />
            ))}
          </Card>

          <Card>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
              Действия
            </h2>
            <div className="flex flex-col gap-2">
              {ACTIONS.map((a) => (
                <Button
                  key={a.action}
                  variant={a.variant}
                  icon={a.icon}
                  loading={pending === a.action}
                  disabled={pending != null && pending !== a.action}
                  onClick={() => runAction(a.action)}
                  className="w-full justify-start"
                >
                  {a.label}
                </Button>
              ))}
              {!inc.video_available && (
                <Button
                  variant="secondary"
                  icon={Archive}
                  loading={pending === 'request_archive'}
                  disabled={pending != null && pending !== 'request_archive'}
                  onClick={() => runAction('request_archive')}
                  className="w-full justify-start"
                >
                  Запросить архив
                </Button>
              )}
            </div>
            {actionFeedback && (
              <p className="mt-3 rounded-md bg-bg px-3 py-2 text-xs text-ink">{actionFeedback}</p>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
