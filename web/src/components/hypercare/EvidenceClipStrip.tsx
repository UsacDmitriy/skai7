import { cn } from '@/components/ui/cn'
import type { HypercareClipStatus, HypercareEvidenceClip } from '@/api/types'

const CHANNEL_LABEL: Record<number, string> = {
  1: 'ADAS',
  2: 'SNZ-L',
  3: 'SNZ-R',
  5: 'DMS',
}

// Статус клипа (ClipStatus, спека M-HYPERCARE): available → готов к просмотру,
// pending → фолбэк-заявка на регистратор с ETA.
const STATUS_STYLE: Record<HypercareClipStatus, string> = {
  available: 'bg-green-100 text-green-800 border-green-200',
  pending: 'bg-blue-50 text-blue-700 border-blue-200',
}

const STATUS_ICON: Record<HypercareClipStatus, string> = {
  available: '▶',
  pending: '⏳',
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
        const canOpen = clip.status === 'available'
        return (
          <button
            key={i}
            role="listitem"
            disabled={!canOpen}
            aria-label={`Открыть клип ${label} ${clip.status}`}
            onClick={() => canOpen && onOpen(clip)}
            className={cn(
              'flex flex-col items-center justify-center rounded-lg border px-3 py-2 text-xs font-medium transition-opacity',
              STATUS_STYLE[clip.status],
              canOpen ? 'cursor-pointer hover:opacity-80' : 'cursor-default opacity-60',
            )}
          >
            <span className="text-base leading-none">{STATUS_ICON[clip.status]}</span>
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
