import { useEffect, useRef } from 'react'
import { Loader2, Mic, Square } from 'lucide-react'
import { cn } from './cn'

export type VoiceButtonState = 'idle' | 'recording' | 'processing'

export interface VoiceButtonProps {
  /** Внешнее состояние управляет видом (CONTRACT §7.6). */
  state: VoiceButtonState
  /** Вызывается по остановке записи с готовым аудио-Blob (наружу — в f7/STT). */
  onRecorded: (blob: Blob) => void
  disabled?: boolean
  /** Микрофон успешно открыт и запись пошла. */
  onStart?: () => void
  /** Запись остановлена пользователем (до прихода blob). */
  onStop?: () => void
}

// Презентационный контракт: вид — по `state`, запись — внутренний MediaRecorder,
// который только пишет и отдаёт blob через onRecorded. NLU/STT не трогаем.
const LABEL: Record<VoiceButtonState, string> = {
  idle: 'Записать голосовой запрос',
  recording: 'Остановить запись',
  processing: 'Распознавание запроса…',
}

const STATUS: Record<VoiceButtonState, string> = {
  idle: 'Готов к записи',
  recording: 'Идёт запись голоса',
  processing: 'Идёт распознавание',
}

const VARIANT: Record<VoiceButtonState, string> = {
  // primary-outline: обводка primary, прозрачный фон.
  idle: 'border-2 border-primary bg-transparent text-primary hover:bg-primary-50',
  // critical-pulse: фон critical + пульсация.
  recording: 'border-2 border-critical bg-critical text-white animate-pulse',
  // primary spinner: primary + крутящийся Loader2 (disabled).
  processing: 'border-2 border-primary bg-primary text-white',
}

export function VoiceButton({ state, onRecorded, disabled, onStart, onStop }: VoiceButtonProps) {
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])

  // Закрыть микрофонный поток (release tracks), чтобы не висел индикатор записи.
  const releaseStream = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
  }

  // Размонтирование посреди записи не должно оставлять микрофон открытым.
  useEffect(() => releaseStream, [])

  const startRecording = async () => {
    if (recorderRef.current) return
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      // Контракт transcribe — multipart wav; если браузер умеет только webm/opus,
      // отдаём как есть с корректным MIME (перекодировка — на f7/бэке).
      const mime =
        typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported('audio/wav')
          ? 'audio/wav'
          : undefined
      const recorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/wav' })
        releaseStream()
        recorderRef.current = null
        onRecorded(blob)
      }
      streamRef.current = stream
      recorderRef.current = recorder
      recorder.start()
      onStart?.()
    } catch {
      // Нет разрешения/устройства: не падаем, поток не оставляем висеть,
      // onStart не зовём — внешнее `state` остаётся idle (визуально валидно).
      releaseStream()
      recorderRef.current = null
    }
  }

  const stopRecording = () => {
    onStop?.()
    const recorder = recorderRef.current
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop() // onstop → onRecorded + releaseStream
    } else {
      releaseStream()
      recorderRef.current = null
    }
  }

  const handleClick = () => {
    if (state === 'idle') void startRecording()
    else if (state === 'recording') stopRecording()
    // processing — кнопка disabled, кликов нет.
  }

  const isProcessing = state === 'processing'
  const isRecording = state === 'recording'

  return (
    <div className="inline-flex flex-col items-center gap-1">
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled || isProcessing}
        aria-label={LABEL[state]}
        aria-pressed={isRecording}
        aria-busy={isProcessing}
        className={cn(
          'inline-flex h-12 w-12 items-center justify-center rounded-full',
          'transition-colors duration-150',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
          'disabled:cursor-not-allowed disabled:opacity-70',
          VARIANT[state],
        )}
      >
        {isProcessing ? (
          <Loader2 size={22} className="animate-spin" aria-hidden />
        ) : isRecording ? (
          <Square size={20} aria-hidden />
        ) : (
          <Mic size={22} aria-hidden />
        )}
      </button>
      {/* Статус записи доступен скринридеру — не только цвет/пульс. */}
      <span role="status" aria-live="polite" className="sr-only">
        {STATUS[state]}
      </span>
    </div>
  )
}
