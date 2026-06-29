import { Loader2, Search } from 'lucide-react'
import { VoiceButton, type VoiceButtonState } from './VoiceButton'
import { cn } from './cn'

export interface SmartQueryInputProps {
  value: string
  onChange: (text: string) => void
  onSubmit?: (text: string) => void
  placeholder?: string
  suggestions?: string[]
  voice?: boolean
  voiceState?: VoiceButtonState
  onRecorded?: (blob: Blob) => void
  busy?: boolean
  className?: string
}

/**
 * SmartQueryInput — единый ввод запроса: текст (первичный) + опц. голос + подсказки.
 * Чистая презентация: эмитит onChange (каждое изменение) и onSubmit (Enter/чип).
 */
export function SmartQueryInput({
  value, onChange, onSubmit, placeholder = 'Сформулируйте запрос…',
  suggestions = [], voice = false, voiceState = 'idle', onRecorded, busy, className,
}: SmartQueryInputProps) {
  const pickSuggestion = (s: string) => {
    onChange(s)
    onSubmit?.(s)
  }
  return (
    <div className={cn('flex flex-col gap-2', className)} role="search">
      <div className="flex items-center gap-2">
        {voice && onRecorded && (
          <VoiceButton state={voiceState} onRecorded={onRecorded} disabled={busy} />
        )}
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
          <input
            type="search"
            value={value}
            placeholder={placeholder}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onSubmit?.(value)
            }}
            className="w-full rounded-lg border border-border bg-surface py-2 pl-9 pr-3 text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          />
          {busy && (
            <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-primary" aria-hidden />
          )}
        </div>
      </div>
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {suggestions.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => pickSuggestion(s)}
              className="rounded-full border border-border bg-bg px-2.5 py-1 text-xs text-muted hover:bg-primary-50 hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            >
              {s}
            </button>
          ))}
        </div>
      )}
      <span role="status" aria-live="polite" className="sr-only">
        {voiceState === 'recording' ? 'Идёт запись' : voiceState === 'processing' ? 'Распознавание' : ''}
      </span>
    </div>
  )
}
