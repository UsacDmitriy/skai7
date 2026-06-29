import { Card } from '@/components'
import type { HypercareEvidence, HypercareEvidenceClip } from '@/api/types'
import EvidenceClipStrip from './EvidenceClipStrip'

const STATUS_LABEL: Record<string, string> = {
  fulfilled: 'Готово',
  partial: 'Частично',
  pending: 'Ожидание',
  empty: 'Нет данных',
}

const STATUS_COLOR: Record<string, string> = {
  fulfilled: 'var(--sev-ok)',
  partial: 'var(--sev-warning)',
  pending: 'var(--color-primary)',
  empty: 'var(--color-muted)',
}

function fmtTs(ts: string): string {
  try {
    return new Date(ts).toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ts
  }
}

export default function EvidenceCard({
  evidence,
  onOpenClip,
}: {
  evidence: HypercareEvidence
  onOpenClip: (clip: HypercareEvidenceClip) => void
}) {
  const { vehicle_plate, driver, rule_name, trigger_label, trigger_ts, status, items } = evidence

  return (
    <Card className="p-4 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-0.5">
          <span className="font-semibold text-ink text-base">{vehicle_plate}</span>
          {driver && <span className="text-sm text-muted">{driver}</span>}
        </div>
        <span
          className="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium text-white"
          style={{ background: STATUS_COLOR[status] ?? 'var(--color-muted)' }}
        >
          {STATUS_LABEL[status] ?? status}
        </span>
      </div>

      {/* Trigger info */}
      <div className="text-sm text-ink">
        <span className="font-medium">{trigger_label}</span>
        <span className="text-muted ml-2">{fmtTs(trigger_ts)}</span>
      </div>
      <div className="text-xs text-muted">📋 {rule_name}</div>

      {/* Clips */}
      <EvidenceClipStrip items={items} onOpen={onOpenClip} />
    </Card>
  )
}
