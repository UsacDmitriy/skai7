import { useState } from 'react'
import { Card, Button } from '@/components'
import type { HypercareManualRequest } from '@/api/types'

type VideoChannel = 1 | 2 | 3 | 5

const CHANNELS: { ch: VideoChannel; label: string }[] = [
  { ch: 1, label: 'ADAS' },
  { ch: 2, label: 'SNZ-L' },
  { ch: 3, label: 'SNZ-R' },
  { ch: 5, label: 'DMS' },
]

interface FormState {
  vehicle_plate: string
  trigger_ts: string
  before_sec: number
  after_sec: number
  cameras: VideoChannel[]
}

const DEFAULTS: FormState = {
  vehicle_plate: '',
  trigger_ts: '',
  before_sec: 300,
  after_sec: 120,
  cameras: [1, 5],
}

function isValid(f: FormState): boolean {
  return f.vehicle_plate.trim().length > 0 && f.trigger_ts.length > 0 && f.cameras.length > 0
}

export default function RuleBuilder({
  onSubmit,
  loading = false,
}: {
  onSubmit: (req: HypercareManualRequest) => void
  loading?: boolean
}) {
  const [form, setForm] = useState<FormState>(DEFAULTS)

  function toggleCamera(ch: VideoChannel) {
    setForm((f) => ({
      ...f,
      cameras: f.cameras.includes(ch) ? f.cameras.filter((c) => c !== ch) : [...f.cameras, ch],
    }))
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!isValid(form)) return
    onSubmit({
      vehicle_plate: form.vehicle_plate.trim().toUpperCase(),
      trigger_ts: new Date(form.trigger_ts).toISOString(),
      before_sec: form.before_sec,
      after_sec: form.after_sec,
      cameras: [...form.cameras].sort((a, b) => a - b) as VideoChannel[],
    })
  }

  return (
    <Card className="p-4">
      <h3 className="font-semibold text-ink mb-3">Ручной запрос</h3>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3" noValidate>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-muted">Гос. номер</span>
          <input
            type="text"
            placeholder="А001АА77"
            value={form.vehicle_plate}
            onChange={(e) => setForm((f) => ({ ...f, vehicle_plate: e.target.value }))}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm"
            aria-label="Гос. номер ТС"
            required
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span className="text-muted">Время события</span>
          <input
            type="datetime-local"
            value={form.trigger_ts}
            onChange={(e) => setForm((f) => ({ ...f, trigger_ts: e.target.value }))}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm"
            aria-label="Время события"
            required
          />
        </label>

        <div className="flex gap-3">
          <label className="flex flex-col gap-1 text-sm flex-1">
            <span className="text-muted">До (сек)</span>
            <input
              type="number"
              min={0}
              max={3600}
              value={form.before_sec}
              onChange={(e) => setForm((f) => ({ ...f, before_sec: Number(e.target.value) }))}
              className="rounded border border-gray-300 px-3 py-1.5 text-sm"
              aria-label="Секунд до события"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm flex-1">
            <span className="text-muted">После (сек)</span>
            <input
              type="number"
              min={0}
              max={3600}
              value={form.after_sec}
              onChange={(e) => setForm((f) => ({ ...f, after_sec: Number(e.target.value) }))}
              className="rounded border border-gray-300 px-3 py-1.5 text-sm"
              aria-label="Секунд после события"
            />
          </label>
        </div>

        <div className="flex flex-col gap-1 text-sm">
          <span className="text-muted">Камеры</span>
          <div className="flex gap-2 flex-wrap">
            {CHANNELS.map(({ ch, label }) => (
              <button
                key={ch}
                type="button"
                role="checkbox"
                aria-checked={form.cameras.includes(ch)}
                aria-label={`Камера ${label}`}
                onClick={() => toggleCamera(ch)}
                className={[
                  'rounded border px-3 py-1 text-xs font-medium transition-colors',
                  form.cameras.includes(ch)
                    ? 'bg-primary text-white border-primary'
                    : 'bg-white text-muted border-gray-300',
                ].join(' ')}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <Button
          type="submit"
          variant="primary"
          disabled={!isValid(form) || loading}
          aria-busy={loading}
        >
          {loading ? 'Запрос…' : 'Запросить видео'}
        </Button>
      </form>
    </Card>
  )
}
