import { useCallback, useEffect, useState } from 'react'
import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  EyeOff,
  Gauge,
  RotateCcw,
  ShieldCheck,
  TriangleAlert,
  UserCog,
  VideoOff,
} from 'lucide-react'
import * as client from '@/api/client'
import { ApiError } from '@/api/client'
import type { SabotageEvent } from '@/api/types'
import { Button, Card, VideoPlayer } from '@/components'

/**
 * f12 · Виджет детекции саботажа камеры (идея #9, §7.4 GET /api/sabotage, §7.5 SabotageEvent).
 *
 * Корреляция-улика: DMS-камера даёт тёмный кадр (`dms_dark=true`), а телематика
 * показывает движение (`speed_kmh > 0`) → перекрытая камера на ходу = саботаж.
 * Переиспользуемый компонент (не маршрут): встраивается в Report (f7) и Monitor (f6).
 *
 * `variant="full"`     — KPI-счётчик + полный список карточек (для /report).
 * `variant="compact"`  — панель-сводка (счётчик + последние события, клик разворачивает,
 *                        для /monitor); при ошибке показывает ошибку, а не пустоту.
 *
 * Данные грузит сам через `client.getSabotage()`; на фикстурах — `VITE_USE_FIXTURES=true`.
 */

export interface SabotageWidgetProps {
  variant?: 'full' | 'compact'
  className?: string
}

type LoadState = 'loading' | 'ready' | 'error'

function humanError(e: unknown): string {
  if (e instanceof ApiError) return e.message
  if (e instanceof Error) return e.message
  return 'Неизвестная ошибка'
}

/** Дата в локали/таймзоне пользователя (a11y: читаемо скринридеру). */
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

// ── Хук загрузки списка саботажа (общий для обоих вариантов) ───────────────────

function useSabotage() {
  const [state, setState] = useState<LoadState>('loading')
  const [events, setEvents] = useState<SabotageEvent[]>([])
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    let alive = true
    setState('loading')
    setError(null)
    client
      .getSabotage()
      .then((data) => {
        if (!alive) return
        setEvents(data)
        setState('ready')
      })
      .catch((e: unknown) => {
        if (!alive) return
        setError(humanError(e))
        setState('error')
      })
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => load(), [load])

  return { state, events, error, reload: load }
}

// ── Тёмный DMS-кадр + оверлей «DMS перекрыта» ─────────────────────────────────

function DarkFrame({ event }: { event: SabotageEvent }) {
  // a11y: тёмный кадр сам по себе не несёт смысла — текстовая альтернатива через aria-label.
  const alt = event.dms_dark
    ? `Тёмный кадр DMS, камера перекрыта · ${event.vehicle_plate}`
    : `Кадр DMS · ${event.vehicle_plate}`
  return (
    <div className="relative">
      {event.video_url ? (
        <VideoPlayer src={event.video_url} ariaLabel={alt} />
      ) : (
        // Нет видео: плейсхолдер вместо плеера, метка «DMS перекрыта» сохраняется.
        <div
          role="img"
          aria-label={alt}
          className="flex aspect-video flex-col items-center justify-center gap-2 rounded-md bg-ink text-muted"
        >
          <VideoOff size={32} aria-hidden />
          <span className="text-sm">Кадр недоступен</span>
        </div>
      )}
      {event.dms_dark && (
        <span className="pointer-events-none absolute left-2 top-2 inline-flex items-center gap-1.5 rounded-md bg-critical px-2 py-1 text-xs font-semibold text-white shadow">
          <EyeOff className="h-3.5 w-3.5" aria-hidden />
          DMS перекрыта
        </span>
      )}
    </div>
  )
}

// ── Корреляция-улика: крупная скорость «машина едет» ──────────────────────────

function SpeedProof({ speed }: { speed: number }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-md border border-critical/30 bg-critical-bg px-4 py-3 text-center">
      <Gauge className="h-5 w-5 text-critical-text" aria-hidden />
      {/* a11y: смысл не только цветом — подпись «машина едет · N км/ч» доступна скринридеру. */}
      <span className="sr-only">машина едет · {speed} км/ч</span>
      <div aria-hidden className="mt-1 text-2xl font-bold tabular-nums text-critical-text">
        {speed}
        <span className="ml-1 text-sm font-medium">км/ч</span>
      </div>
      <div aria-hidden className="text-[11px] font-medium uppercase tracking-wide text-critical-text/80">
        машина едет
      </div>
    </div>
  )
}

// ── Умный вердикт саботажа (идея #16, §8 кросс-проверка) ──────────────────────
//
// b23 кладёт в `SabotageEvent` опциональные `verdict_confidence` (0..1) и
// `verdict_reason`. Высокий confidence — «день/ясно снаружи, камера должна была
// видеть» ⇒ подмена; ниже — «ночь/туман» ⇒ тёмный кадр объясним внешними условиями.
// Backward-compat: нет полей вердикта (старые данные) → блок не рендерится вовсе.

/** Палитра шкалы по уровню уверенности: выше уверенность саботажа → насыщеннее критичный тон. */
function verdictTone(confidence: number): { label: string; bar: string; text: string } {
  if (confidence >= 0.7) {
    return { label: 'высокая', bar: 'bg-critical', text: 'text-critical-text' }
  }
  if (confidence >= 0.4) {
    return { label: 'средняя', bar: 'bg-high-text', text: 'text-high-text' }
  }
  return { label: 'низкая', bar: 'bg-muted', text: 'text-muted' }
}

function VerdictBadge({ event }: { event: SabotageEvent }) {
  // Поля опциональны (b23). Нет уверенности → прежний вид карточки (обратная совместимость).
  if (event.verdict_confidence == null) return null

  // Клампим в [0..1] на случай «грязных» данных, проценты — для читаемости оператору.
  const confidence = Math.min(1, Math.max(0, event.verdict_confidence))
  const percent = Math.round(confidence * 100)
  const tone = verdictTone(confidence)

  return (
    <div className="rounded-md border border-border bg-surface px-3 py-2.5">
      <div className="flex items-center justify-between gap-2">
        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-ink">
          <Gauge className={`h-3.5 w-3.5 ${tone.text}`} aria-hidden />
          Вердикт саботажа
        </span>
        <span className={`text-sm font-semibold tabular-nums ${tone.text}`}>
          {/* a11y: смысл словами, не только цветом/числом. */}
          <span className="sr-only">уверенность {tone.label}, </span>
          {percent}%
        </span>
      </div>
      {/* Шкала уверенности 0..1: ширина = confidence, цвет = тон уровня. */}
      <div
        className="mt-2 h-1.5 overflow-hidden rounded-full bg-border/60"
        role="meter"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-label={`Уверенность вердикта саботажа: ${percent}%`}
      >
        <div className={`h-full rounded-full ${tone.bar}`} style={{ width: `${percent}%` }} />
      </div>
      {event.verdict_reason && (
        <p className="mt-2 text-xs leading-snug text-muted">{event.verdict_reason}</p>
      )}
    </div>
  )
}

// ── Кнопки действий (postAction) с состоянием in-flight + откатом ──────────────

type ActionKind = 'create_task' | 'notify_hr'

function ActionButtons({ event }: { event: SabotageEvent }) {
  // Состояние по каждому действию: идёт ли запрос, успех, ошибка.
  const [pending, setPending] = useState<ActionKind | null>(null)
  const [done, setDone] = useState<Partial<Record<ActionKind, boolean>>>({})
  const [error, setError] = useState<string | null>(null)

  const run = useCallback(
    (kind: ActionKind, comment: string) => {
      setPending(kind)
      setError(null)
      // `notify_hr` — валидный ActionType в §3.4 (контракт расширён, TODO b13 снят).
      client
        .postAction({ incident_id: event.id, action: kind, comment })
        .then(() => setDone((d) => ({ ...d, [kind]: true })))
        .catch((e: unknown) => setError(humanError(e)))
        .finally(() => setPending(null))
    },
    [event.id],
  )

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        <Button
          variant="primary"
          icon={ShieldCheck}
          loading={pending === 'create_task'}
          disabled={pending !== null || done.create_task}
          onClick={() => run('create_task', 'Саботаж камеры: создать заявку')}
        >
          {done.create_task ? 'Заявка создана' : 'Создать заявку'}
        </Button>
        <Button
          variant="secondary"
          icon={UserCog}
          loading={pending === 'notify_hr'}
          disabled={pending !== null || done.notify_hr}
          onClick={() => run('notify_hr', 'Саботаж камеры: уведомить HR')}
        >
          {done.notify_hr ? 'HR уведомлён' : 'Уведомить HR'}
        </Button>
      </div>
      {(done.create_task || done.notify_hr) && !error && (
        <p className="inline-flex items-center gap-1.5 text-xs text-ok-text" role="status">
          <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
          Действие выполнено
        </p>
      )}
      {error && (
        // Ошибка отката не теряет карточку: кнопка снова активна, сообщение рядом.
        <p className="inline-flex items-center gap-1.5 text-xs text-high-text" role="alert">
          <TriangleAlert className="h-3.5 w-3.5" aria-hidden />
          Не удалось: {error}
        </p>
      )}
    </div>
  )
}

// ── Карточка одного события саботажа ──────────────────────────────────────────

function SabotageCard({ event }: { event: SabotageEvent }) {
  return (
    <Card className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
        <DarkFrame event={event} />
        <SpeedProof speed={event.speed_kmh} />
      </div>
      <VerdictBadge event={event} />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-medium text-ink">{event.driver_name}</div>
          <div className="mt-0.5 text-xs text-muted">
            {event.vehicle_plate} · <span className="tabular-nums">{formatTime(event.ts)}</span>
          </div>
        </div>
      </div>
      <ActionButtons event={event} />
    </Card>
  )
}

// ── Состояния (loading / error / empty) ───────────────────────────────────────

function Bar({ className }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-border/60 ${className ?? ''}`} />
}

function CardSkeleton() {
  return (
    <Card className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
        <Bar className="aspect-video w-full" />
        <Bar className="h-20 w-24" />
      </div>
      <Bar className="h-4 w-48" />
      <Bar className="h-9 w-56" />
    </Card>
  )
}

function ErrorBlock({ message, onRetry, compact }: { message: string; onRetry: () => void; compact?: boolean }) {
  return (
    <div
      role="alert"
      className={`flex flex-col items-center gap-3 rounded-md border border-border bg-surface text-center ${compact ? 'px-4 py-6' : 'px-5 py-10'}`}
    >
      <TriangleAlert className="h-7 w-7 text-high-text" aria-hidden />
      <p className="max-w-sm text-sm text-muted">{message}</p>
      <Button variant="secondary" icon={RotateCcw} onClick={onRetry}>
        Повторить
      </Button>
    </div>
  )
}

function EmptyBlock({ compact }: { compact?: boolean }) {
  return (
    <div
      className={`flex flex-col items-center gap-2 rounded-md border border-border bg-surface text-center text-muted ${compact ? 'px-4 py-6' : 'px-5 py-12'}`}
    >
      <ShieldCheck className="h-8 w-8 text-ok" aria-hidden />
      <p className="text-sm">Саботаж не обнаружен</p>
    </div>
  )
}

// ── Заголовок секции со счётчиком ─────────────────────────────────────────────

function SectionTitle({ count }: { count: number }) {
  return (
    <div className="flex items-center gap-2">
      <EyeOff className="h-5 w-5 text-critical-text" aria-hidden />
      <h2 className="text-base font-semibold text-ink">
        Камера заблокирована · подозрение на саботаж
      </h2>
      <span
        className="inline-flex min-w-6 items-center justify-center rounded-full bg-critical-bg px-2 py-0.5 text-xs font-semibold tabular-nums text-critical-text"
        aria-label={`Событий за период: ${count}`}
      >
        {count}
      </span>
    </div>
  )
}

// ── Полный вариант (для Report f7) ────────────────────────────────────────────

function FullWidget({ className }: { className?: string }) {
  const { state, events, error, reload } = useSabotage()

  return (
    <section className={`space-y-4 ${className ?? ''}`} aria-label="Детекция саботажа камеры">
      <SectionTitle count={state === 'ready' ? events.length : 0} />

      {state === 'loading' && (
        <div className="space-y-4" aria-busy="true">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      )}

      {state === 'error' && <ErrorBlock message={error ?? 'Ошибка загрузки'} onRetry={reload} />}

      {state === 'ready' && events.length === 0 && <EmptyBlock />}

      {state === 'ready' && events.length > 0 && (
        <div className="space-y-4">
          {events.map((ev) => (
            <SabotageCard key={ev.id} event={ev} />
          ))}
        </div>
      )}
    </section>
  )
}

// ── Компактный вариант (для Monitor f6) ───────────────────────────────────────

function CompactWidget({ className }: { className?: string }) {
  const { state, events, error, reload } = useSabotage()
  const [open, setOpen] = useState(false)

  // Последние события (по ts, свежие сверху) для свёрнутой сводки.
  const recent = [...events].sort((a, b) => b.ts.localeCompare(a.ts))
  const preview = recent.slice(0, 3)

  return (
    <Card className={`space-y-3 ${className ?? ''}`}>
      <div className="flex items-center justify-between gap-2">
        <SectionTitle count={state === 'ready' ? events.length : 0} />
        {state === 'ready' && events.length > 0 && (
          <Button
            variant="ghost"
            icon={open ? ChevronUp : ChevronDown}
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-label={open ? 'Свернуть список саботажа' : 'Развернуть список саботажа'}
          >
            {open ? 'Свернуть' : 'Подробнее'}
          </Button>
        )}
      </div>

      {state === 'loading' && (
        <div className="space-y-2" aria-busy="true">
          <Bar className="h-4 w-3/4" />
          <Bar className="h-4 w-1/2" />
        </div>
      )}

      {state === 'error' && <ErrorBlock message={error ?? 'Ошибка загрузки'} onRetry={reload} compact />}

      {state === 'ready' && events.length === 0 && <EmptyBlock compact />}

      {state === 'ready' && events.length > 0 && !open && (
        <ul className="space-y-1.5">
          {preview.map((ev) => (
            <li key={ev.id} className="flex items-center justify-between gap-2 text-sm">
              <span className="inline-flex min-w-0 items-center gap-1.5">
                <EyeOff className="h-3.5 w-3.5 shrink-0 text-critical-text" aria-hidden />
                <span className="truncate text-ink">{ev.vehicle_plate}</span>
                <span className="truncate text-muted">· {ev.driver_name}</span>
              </span>
              <span className="shrink-0 tabular-nums text-xs font-medium text-critical-text">
                <span className="sr-only">машина едет · </span>
                {ev.speed_kmh} км/ч
              </span>
            </li>
          ))}
        </ul>
      )}

      {state === 'ready' && events.length > 0 && open && (
        <div className="space-y-3">
          {recent.map((ev) => (
            <SabotageCard key={ev.id} event={ev} />
          ))}
        </div>
      )}
    </Card>
  )
}

// ── Публичный компонент ───────────────────────────────────────────────────────

export function SabotageWidget({ variant = 'full', className }: SabotageWidgetProps) {
  return variant === 'compact' ? (
    <CompactWidget className={className} />
  ) : (
    <FullWidget className={className} />
  )
}
