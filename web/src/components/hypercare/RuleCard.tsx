import { Card } from '@/components'
import { cn } from '@/components/ui/cn'
import type { HypercareRule } from '@/api/types'

const KIND_LABEL: Record<string, string> = {
  event: 'событие',
  sensor: 'датчик',
  schedule: 'расписание',
  manual: 'ручной',
}

const KIND_COLOR: Record<string, string> = {
  event: 'var(--sev-critical)',
  sensor: 'var(--sev-high)',
  schedule: 'var(--color-primary)',
  manual: 'var(--color-muted)',
}

function fmtSec(sec: number): string {
  if (sec === 0) return '0'
  const m = Math.floor(sec / 60)
  const s = sec % 60
  if (m > 0 && s > 0) return `${m}м${s}с`
  if (m > 0) return `${m}м`
  return `${s}с`
}

export function windowSummary(rule: HypercareRule): string {
  const { before_sec, after_sec, mode, interval_sec, clip_len_sec } = rule.window
  const base = `−${fmtSec(before_sec)} … +${fmtSec(after_sec)}`
  if (mode === 'interval' && interval_sec) return `${base} · фото/${fmtSec(interval_sec)}`
  if (clip_len_sec) return `${base} · клип ${clip_len_sec}с`
  return `${base} · непрерыв.`
}

export default function RuleCard({
  rule,
  onToggle,
}: {
  rule: HypercareRule
  onToggle: (id: string) => void
}) {
  const subtitle =
    rule.trigger.alarm_codes?.join(', ') ??
    rule.trigger.metric ??
    rule.trigger.kind

  return (
    <Card className="p-4 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <span aria-hidden style={{ color: KIND_COLOR[rule.trigger.kind] }}>●</span>
        <span className="font-semibold text-ink">{rule.name}</span>
      </div>
      <div className="text-sm text-muted">
        {KIND_LABEL[rule.trigger.kind] ?? rule.trigger.kind} · {subtitle}
      </div>
      <div className="text-sm text-ink">⏱ {windowSummary(rule)}</div>
      <div className="text-sm text-muted">🎥 кам {rule.cameras.join(', ')}</div>
      <button
        role="switch"
        aria-checked={rule.enabled}
        aria-label={`Переключить правило ${rule.name}`}
        onClick={() => onToggle(rule.id)}
        className={cn(
          'mt-1 self-start rounded-full px-3 py-1 text-xs font-medium transition-colors',
          rule.enabled
            ? 'bg-primary text-white'
            : 'bg-primary-50 text-primary',
        )}
      >
        {rule.enabled ? '● вкл' : '○ выкл'}
      </button>
    </Card>
  )
}
