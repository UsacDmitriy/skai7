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
  className?: string
}

export function VideoPlayer({
  src,
  poster,
  eventMarkerPct,
  onTimeUpdate,
  seekTo,
  className,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)

  // Контролируемая перемотка от родителя (sync двух плееров / клик по графику).
  useEffect(() => {
    const video = videoRef.current
    if (video && seekTo != null && Number.isFinite(seekTo)) {
      if (Math.abs(video.currentTime - seekTo) > 0.25) {
        video.currentTime = seekTo
      }
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
        onTimeUpdate={(e) => onTimeUpdate?.(e.currentTarget.currentTime)}
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
