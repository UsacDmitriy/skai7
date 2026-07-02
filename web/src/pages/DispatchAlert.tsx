import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  AlertTriangle,
  Archive,
  CheckCircle2,
  ClipboardList,
  Phone,
  VideoOff,
  X,
} from 'lucide-react'
import * as client from '@/api/client'
import { ApiError } from '@/api/client'
import type { DispatchAlert as DispatchAlertData } from '@/api/types'
import { Button, SeverityBadge, TelemetryChart, VideoPlayer } from '@/components'
import { cn } from '@/components/ui/cn'

/**
 * f9 · Dispatch Alert (идея #5) — overlay-модал критического алярма.
 *
 * При `auto_request_video=true` система сама запросила видео; диспетчер получает
 * алерт поверх рабочего экрана (фон не размонтируется — см. App.tsx overlay-route):
 * видео ±15 с + телеметрия момента + 3 быстрых действия. Закрытие всегда
 * возвращает на фоновый маршрут. Время берётся из `requested_at`/`ts` (без `Date.now()`).
 */

// Таймзона парка (как в f14/IncidentCard) — единый формат времени, без Date.now() в логике.
const PARK_TZ = (import.meta.env.VITE_PARK_TIMEZONE as string | undefined) ?? 'UTC'

function formatDateTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: PARK_TZ,
  })
}

/** Состояния кнопки «Позвонить водителю». */
type CallState = 'idle' | 'connecting' | 'active'

const CALL_LABEL: Record<CallState, string> = {
  idle: 'Позвонить водителю',
  connecting: 'Соединение…',
  active: 'На связи',
}

function SkeletonBox({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded bg-border', className)} />
}

export default function DispatchAlert() {
  const { id = '' } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const hasBackground = Boolean(
    (location.state as { backgroundLocation?: unknown } | null)?.backgroundLocation,
  )

  const [alert, setAlert] = useState<DispatchAlertData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<{ status?: number; message: string } | null>(null)

  const [callState, setCallState] = useState<CallState>('idle')
  const [taskPending, setTaskPending] = useState(false)
  const [feedback, setFeedback] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null)

  const dialogRef = useRef<HTMLDivElement>(null)
  const closingRef = useRef(false)
  const timerRef = useRef<number>()

  // ── Возврат фокуса на триггер после закрытия модала (a11y) ───────────────────
  useEffect(() => {
    const trigger = document.activeElement as HTMLElement | null
    // Блокируем скролл фона, не размонтируя его.
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prevOverflow
      trigger?.focus?.()
    }
  }, [])

  // ── Загрузка алерта ──────────────────────────────────────────────────────────
  const load = useCallback(() => {
    let alive = true
    setLoading(true)
    setError(null)
    setAlert(null)
    client
      .getAlert(id)
      .then((data) => {
        if (alive) setAlert(data)
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

  useEffect(() => load(), [load])

  // Сброс локальных состояний при смене алерта (id): иначе callState/taskPending/
  // feedback залипают со старого алерта, если модал переоткрыт на другой id.
  useEffect(() => {
    setCallState('idle')
    setTaskPending(false)
    setFeedback(null)
  }, [id])

  // Очистка отложенного закрытия (createTask) при размонтировании: иначе
  // goBackground сработает после unmount → «мигрирующая» навигация + setState.
  useEffect(() => () => {
    if (timerRef.current) clearTimeout(timerRef.current)
  }, [])

  // Автофокус на первой кнопке после загрузки контента (Button не forwardRef —
  // целевую кнопку помечаем `data-autofocus`, иначе берём первую в DOM).
  useEffect(() => {
    if (loading) return
    const root = dialogRef.current
    if (!root) return
    const target =
      root.querySelector<HTMLElement>('[data-autofocus]:not([disabled])') ??
      root.querySelector<HTMLElement>('button:not([disabled])')
    target?.focus()
  }, [loading, error, alert])

  // ── Закрытие: всегда возврат на фоновый маршрут ──────────────────────────────
  const goBackground = useCallback(() => {
    if (hasBackground) navigate(-1)
    else navigate('/', { replace: true })
  }, [hasBackground, navigate])

  /** «Всё в порядке» / Esc / клик по фону — mark_reviewed (best-effort) + закрыть. */
  const dismiss = useCallback(() => {
    if (closingRef.current) return
    closingRef.current = true
    if (alert?.incident) {
      void client
        .postAction({ incident_id: alert.incident.id, action: 'validate', comment: '' })
        .catch(() => {})
    }
    goBackground()
  }, [alert, goBackground])

  // ── Действие: позвонить водителю (idle → connecting → active) ────────────────
  const callDriver = useCallback(async () => {
    if (!alert?.incident || callState !== 'idle') return
    setCallState('connecting')
    setFeedback(null)
    try {
      await client.postAction({
        incident_id: alert.incident.id,
        action: 'call_driver',
        comment: '',
      })
      setCallState('active')
    } catch (e: unknown) {
      setCallState('idle')
      const msg = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Ошибка'
      setFeedback({ kind: 'err', text: `Не удалось соединиться: ${msg}` })
    }
  }, [alert, callState])

  // ── Действие: создать заявку → тост + закрыть ────────────────────────────────
  const createTask = useCallback(async () => {
    if (!alert?.incident || taskPending) return
    setTaskPending(true)
    setFeedback(null)
    try {
      await client.postAction({
        incident_id: alert.incident.id,
        action: 'create_task',
        comment: '',
      })
      setFeedback({ kind: 'ok', text: 'Заявка создана' })
      closingRef.current = true
      // Дать прочитать тост, затем закрыть (setTimeout — UX-задержка, не вычисление времени).
      // Таймер в ref → очищается на unmount (см. эффект выше).
      timerRef.current = window.setTimeout(goBackground, 1100)
    } catch (e: unknown) {
      setTaskPending(false)
      const msg = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Ошибка'
      setFeedback({ kind: 'err', text: `Не удалось создать заявку: ${msg}` })
    }
  }, [alert, taskPending, goBackground])

  const onArchive = useCallback(async () => {
    if (!alert?.incident) return
    setFeedback(null)
    try {
      await client.postAction({
        incident_id: alert.incident.id,
        action: 'request_archive',
        comment: '',
      })
      setFeedback({ kind: 'ok', text: 'Запрос архива отправлен' })
    } catch (e: unknown) {
      const msg = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Ошибка'
      setFeedback({ kind: 'err', text: `Не удалось запросить архив: ${msg}` })
    }
  }, [alert])

  // ── Клавиатура: Esc = «Всё в порядке», Tab = фокус-трап ──────────────────────
  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        dismiss()
        return
      }
      if (e.key !== 'Tab') return
      const root = dialogRef.current
      if (!root) return
      const focusables = Array.from(
        root.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((el) => !el.hasAttribute('disabled') && el.tabIndex !== -1)
      if (focusables.length === 0) return
      const first = focusables[0]
      const last = focusables[focusables.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    },
    [dismiss],
  )

  // ── Позиция маркера t=0 для видео (из телеметрии момента) ─────────────────────
  const eventMarkerPct = useMemo(() => {
    const offsets = alert?.incident.telemetry.map((p) => p.ts_offset) ?? []
    if (offsets.length === 0) return undefined
    const min = Math.min(...offsets)
    const max = Math.max(...offsets)
    const range = Math.max(1, max - min)
    return ((0 - min) / range) * 100
  }, [alert])

  // ── Каркас оверлея (общий для loading/error/content) ─────────────────────────
  const titleId = 'dispatch-alert-title'

  function Overlay({ children }: { children: React.ReactNode }) {
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        onKeyDown={onKeyDown}
      >
        {/* Полупрозрачное затемнение — фон под ним виден; клик = «Всё в порядке». */}
        <div
          className="absolute inset-0 bg-ink/50"
          aria-hidden
          onClick={dismiss}
        />
        <div
          ref={dialogRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          className="relative z-10 max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-xl border border-border bg-surface shadow-2xl"
        >
          {children}
        </div>
      </div>
    )
  }

  // ── Loading: скелетон шапки/видео-зон ────────────────────────────────────────
  if (loading) {
    return (
      <Overlay>
        <div className="space-y-4 p-5" aria-busy="true" aria-label="Загрузка алерта">
          <h2 id={titleId} className="sr-only">
            Загрузка алерта
          </h2>
          <div className="flex flex-wrap items-center gap-3">
            <SkeletonBox className="h-6 w-24" />
            <SkeletonBox className="h-6 w-56" />
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <SkeletonBox className="aspect-video" />
            <SkeletonBox className="aspect-video" />
          </div>
          <SkeletonBox className="h-40" />
        </div>
      </Overlay>
    )
  }

  // ── Error (≠404) / 404 / неизвестный id ──────────────────────────────────────
  if (error || !alert) {
    const is404 = error?.status === 404
    return (
      <Overlay>
        <div className="p-6 text-center">
          <AlertTriangle className="mx-auto h-8 w-8 text-high" aria-hidden />
          <h2 id={titleId} className="mt-3 text-lg font-semibold text-ink">
            {is404 ? 'Алерт не найден' : 'Ошибка загрузки'}
          </h2>
          <p className="mt-1 text-sm text-muted">
            {is404 ? `Алерт «${id}» не существует.` : error?.message}
          </p>
          <div className="mt-4 flex justify-center gap-2">
            {!is404 && (
              <Button data-autofocus variant="secondary" onClick={load}>
                Повторить
              </Button>
            )}
            <Button
              {...(is404 ? { 'data-autofocus': true } : {})}
              variant={is404 ? 'secondary' : 'primary'}
              icon={X}
              onClick={goBackground}
            >
              Закрыть
            </Button>
          </div>
        </div>
      </Overlay>
    )
  }

  const inc = alert.incident

  return (
    <Overlay>
      {/* ── Шапка ──────────────────────────────────────────────────────────── */}
      <div className="flex items-start gap-3 border-b border-border p-5">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity="critical" label="Критично" />
            <h2 id={titleId} className="text-lg font-semibold text-ink">
              {inc.alarm_label_ru}
            </h2>
          </div>
          <div className="inline-flex items-center gap-1.5 rounded-md bg-critical/10 px-2 py-1 text-xs font-medium text-critical-text">
            🔴 Автозапрос видео ·{' '}
            <span className="tabular-nums">{formatDateTime(alert.requested_at)}</span>
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted">
            <span>
              ТС:{' '}
              <span className="font-medium text-ink">
                {inc.vehicle_model} · {inc.vehicle_plate}
              </span>
            </span>
            <span>
              Водитель: <span className="font-medium text-ink">{inc.driver}</span>
            </span>
            <span>
              Время:{' '}
              <span className="font-medium tabular-nums text-ink">{formatDateTime(inc.ts)}</span>
            </span>
          </div>
        </div>
        <Button
          variant="ghost"
          icon={X}
          onClick={dismiss}
          aria-label="Закрыть (всё в порядке)"
          title="Всё в порядке"
        />
      </div>

      {/* ── Видео ±N с ─────────────────────────────────────────────────────── */}
      <div className="space-y-4 p-5">
        <section>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">
              Видео момента
            </h3>
            {inc.video_available && (
              <span className="text-xs text-muted">
                ±{alert.video_window_sec} с от момента
              </span>
            )}
          </div>

          {inc.video_available ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <VideoPlayer
                  src={inc.cam_front_url ? client.videoUrl(inc.id, 1) : undefined}
                  eventMarkerPct={eventMarkerPct}
                  ariaLabel="Видео ADAS · фронтальная камера"
                />
                <span className="text-xs text-muted">ADAS · фронтальная</span>
              </div>
              <div className="space-y-1">
                <VideoPlayer
                  src={inc.cam_dms_url ? client.videoUrl(inc.id, 5) : undefined}
                  eventMarkerPct={eventMarkerPct}
                  ariaLabel="Видео DMS · камера салона"
                />
                <span className="text-xs text-muted">DMS · салон</span>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center gap-3 rounded-md border border-dashed border-border bg-bg py-8 text-center">
              <VideoOff className="h-7 w-7 text-muted" aria-hidden />
              <div className="text-sm font-medium text-ink">Видео недоступно</div>
              <Button variant="secondary" icon={Archive} onClick={onArchive}>
                Запросить архив
              </Button>
            </div>
          )}
        </section>

        {/* ── Телеметрия момента ───────────────────────────────────────────── */}
        <section>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">
              Телеметрия момента
            </h3>
            <div className="text-right">
              <span className="text-2xl font-bold tabular-nums text-ink">{Math.round(inc.speed_kmh)}</span>
              <span className="ml-1 text-xs text-muted">км/ч в момент</span>
            </div>
          </div>
          {inc.telemetry.length === 0 ? (
            <div className="flex h-40 items-center justify-center rounded-md border border-dashed border-border bg-bg">
              <span className="text-sm text-muted">Нет данных телеметрии</span>
            </div>
          ) : (
            <TelemetryChart data={inc.telemetry} height={180} />
          )}
        </section>

        {/* ── Обратная связь (тост) ────────────────────────────────────────── */}
        {feedback && (
          <p
            role="status"
            aria-live="polite"
            className={cn(
              'rounded-md px-3 py-2 text-sm',
              feedback.kind === 'ok'
                ? 'bg-ok/10 text-ok-text'
                : 'bg-critical/10 text-critical-text',
            )}
          >
            {feedback.text}
          </p>
        )}

        {/* ── 3 кнопки действий ────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          <Button
            data-autofocus
            variant="secondary"
            icon={Phone}
            onClick={callDriver}
            disabled={callState !== 'idle'}
            aria-busy={callState === 'connecting'}
            className="justify-center"
          >
            {CALL_LABEL[callState]}
          </Button>
          <Button
            variant="primary"
            icon={ClipboardList}
            onClick={createTask}
            loading={taskPending}
            aria-busy={taskPending}
            className="justify-center"
          >
            Создать заявку
          </Button>
          <Button
            variant="secondary"
            icon={CheckCircle2}
            onClick={dismiss}
            className="justify-center"
          >
            Всё в порядке
          </Button>
        </div>
      </div>
    </Overlay>
  )
}
