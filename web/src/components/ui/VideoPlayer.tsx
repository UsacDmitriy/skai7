import { useEffect, useRef } from 'react'
import { VideoOff } from 'lucide-react'
import { cn } from './cn'

export interface VideoPlayerProps {
  /** URL видеофайла. Пусто/undefined → пустое состояние «Видео недоступно». */
  src?: string
  poster?: string
  /** Позиция жёлтой метки события на таймлайне, 0..100 (% длины ролика). */
  eventMarkerPct?: number
  /**
   * Колбэк прогресса воспроизведения — отдаёт `video.currentTime` (сек).
   * Используется экраном для синхронизации двух плееров и playhead графика (idea #1).
   */
  onTimeUpdate?: (currentSec: number) => void
  /** Контролируемая перемотка: при изменении плеер прыгает на эту секунду. */
  seekTo?: number
  /** Метка для скринридера, например «Видео ADAS» или «Видео DMS». */
  ariaLabel?: string
  className?: string
}

// Минимальный интервал между вызовами onTimeUpdate — ~80 мс (~12 fps).
// Используем DOMHighResTimeStamp из rAF вместо Date.now() для детерминизма.
const THROTTLE_MS = 80

export function VideoPlayer({
  src,
  poster,
  eventMarkerPct,
  onTimeUpdate,
  seekTo,
  ariaLabel = 'Видеозапись',
  className,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const rafRef = useRef<number>(0)
  const lastRafTs = useRef<number>(0)
  // Флаг программного seek: подавляет onTimeUpdate во время seek → предотвращает петлю.
  const isSeeking = useRef(false)
  // Держим актуальный колбэк в ref, чтобы не пересоздавать слушатели при смене prop.
  const onTimeUpdateRef = useRef(onTimeUpdate)
  onTimeUpdateRef.current = onTimeUpdate

  // Throttled timeupdate через rAF — предотвращает «захлёбывание» ререндеров графика.
  // Слушатели и rAF снимаются на unmount.
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const handleTimeUpdate = () => {
      if (isSeeking.current) return
      cancelAnimationFrame(rafRef.current)
      rafRef.current = requestAnimationFrame((ts) => {
        if (ts - lastRafTs.current >= THROTTLE_MS) {
          lastRafTs.current = ts
          onTimeUpdateRef.current?.(video.currentTime)
        }
      })
    }

    const handleSeeked = () => {
      isSeeking.current = false
    }

    video.addEventListener('timeupdate', handleTimeUpdate)
    video.addEventListener('seeked', handleSeeked)

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate)
      video.removeEventListener('seeked', handleSeeked)
      cancelAnimationFrame(rafRef.current)
    }
  }, [])

  // Контролируемая перемотка: применяется только при реальном расхождении (>0.25 с),
  // чтобы не зациклить seek → timeupdate → seek.
  useEffect(() => {
    const video = videoRef.current
    if (!video || seekTo == null || !Number.isFinite(seekTo)) return
    if (Math.abs(video.currentTime - seekTo) > 0.25) {
      isSeeking.current = true
      video.currentTime = seekTo
    }
  }, [seekTo])

  if (!src) {
    return (
      <div
        className={cn(
          'flex aspect-video flex-col items-center justify-center gap-2 rounded-md bg-ink text-muted',
          className,
        )}
      >
        <VideoOff size={32} aria-hidden />
        <span className="text-sm">Видео недоступно</span>
      </div>
    )
  }

  return (
    <div className={cn('relative aspect-video overflow-hidden rounded-md bg-ink', className)}>
      <video
        ref={videoRef}
        src={src}
        poster={poster}
        controls
        className="h-full w-full"
        aria-label={ariaLabel}
      />
      {eventMarkerPct != null && (
        <div
          className="pointer-events-none absolute bottom-0 top-0 w-0.5 bg-warning"
          style={{ left: `${Math.min(100, Math.max(0, eventMarkerPct))}%` }}
          aria-hidden
        />
      )}
    </div>
  )
}
