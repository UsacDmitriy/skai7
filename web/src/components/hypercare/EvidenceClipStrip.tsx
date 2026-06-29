import { cn } from '@/components/ui/cn'
import type { HypercareEvidenceClip } from '@/api/types'

const CHANNEL_LABEL: Record<number, string> = {
  1: 'ADAS',
  2: 'SNZ-L',
  3: 'SNZ-R',
  5: 'DMS',
}

const STATUS_STYLE: Record<string, string> = {
  fulfilled: 'bg-green-100 text-green-800 border-green-200',
  partial: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  pending: 'bg-blue-50 text-blue-700 border-blue-200',
  missing: 'bg-gray-100 text-gray-500 border-gray-200',
}

const STATUS_ICON: Record<string, string> = {
  fulfilled: '▶',
  partial: '◑',
  pending: '⏳',
  missing: '—',
}

export default function EvidenceClipStrip({
  items,
  onOpen,
}: {
  items: HypercareEvidenceClip[]
  onOpen: (clip: HypercareEvidenceClip) => void
}) {
  if (items.length === 0) {
    return <p className="text-sm text-muted italic">Нет медиа</p>
  }

  return (
    <div className="flex flex-wrap gap-2" role="list">
      {items.map((clip, i) => {
        const label = CHANNEL_LABEL[clip.channel] ?? `Cam${clip.channel}`
        const canOpen = clip.status === 'fulfilled' || clip.status === 'partial'
        return (
          <button
            key={i}
            role="listitem"
            disabled={!canOpen}
            aria-label={`Открыть клип ${label} ${clip.status}`}
            onClick={() => canOpen && onOpen(clip)}
            className={cn(
              'flex flex-col items-center justify-center rounded-lg border px-3 py-2 text-xs font-medium transition-opacity',
              STATUS_STYLE[clip.status] ?? STATUS_STYLE.missing,
              canOpen ? 'cursor-pointer hover:opacity-80' : 'cursor-default opacity-60',
            )}
          >
            <span className="text-base leading-none">{STATUS_ICON[clip.status] ?? '?'}</span>
            <span className="mt-1">{label}</span>
            {clip.status === 'pending' && clip.eta_sec != null && (
              <span className="mt-0.5 text-[10px] opacity-75">~{clip.eta_sec}с</span>
            )}
          </button>
        )
      })}
    </div>
  )
}
