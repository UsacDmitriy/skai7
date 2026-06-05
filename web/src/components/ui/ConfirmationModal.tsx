import { useEffect } from 'react'
import { Check } from 'lucide-react'
import type { ReportQuery } from '@/api/types'
import { Button } from './Button'

export interface ConfirmationModalProps {
  open: boolean
  /** Распарсенный NLU-запрос (CONTRACT §7.5). */
  query: ReportQuery
  /** [Исправить] — вернуться к редактированию запроса. */
  onEdit: () => void
  /** [✓ Показать] — подтвердить и построить отчёт. */
  onConfirm: () => void
  /** Закрытие по overlay/Escape. */
  onClose?: () => void
}

const KIND_LABEL: Record<ReportQuery['kind'], string> = {
  driver: 'Отчёт по водителю',
  fleet: 'Отчёт по автопарку',
}

const VIEW_LABEL: Record<NonNullable<ReportQuery['view']>, string> = {
  drivers: 'По водителям',
  vehicles: 'По машинам',
}

// «за 1 день / 2 дня / 5 дней» — RU-плюрализация периода.
function pluralizeDays(n: number): string {
  const abs = Math.abs(n) % 100
  const last = abs % 10
  if (abs > 10 && abs < 20) return `за ${n} дней`
  if (last === 1) return `за ${n} день`
  if (last >= 2 && last <= 4) return `за ${n} дня`
  return `за ${n} дней`
}

interface Field {
  label: string
  value: string
}

function fieldsOf(query: ReportQuery): Field[] {
  const fields: Field[] = [{ label: 'Тип отчёта', value: KIND_LABEL[query.kind] }]
  if (query.driver_name) fields.push({ label: 'Водитель', value: query.driver_name })
  if (query.plate) fields.push({ label: 'Госномер', value: query.plate })
  if (query.period_days != null) fields.push({ label: 'Период', value: pluralizeDays(query.period_days) })
  if (query.view) fields.push({ label: 'Представление', value: VIEW_LABEL[query.view] })
  return fields
}

export function ConfirmationModal({ open, query, onEdit, onConfirm, onClose }: ConfirmationModalProps) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose?.()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/60 p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-modal-title"
        className="w-full max-w-md rounded-xl bg-surface p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="confirm-modal-title" className="text-lg font-semibold text-ink">
          Вот как я понял ваш запрос
        </h2>

        <dl className="mt-4 space-y-2">
          {fieldsOf(query).map((f) => (
            <div key={f.label} className="flex items-baseline justify-between gap-4">
              <dt className="text-sm text-muted">{f.label}</dt>
              <dd className="text-sm font-medium text-ink">{f.value}</dd>
            </div>
          ))}
        </dl>

        <div className="mt-6 flex justify-end gap-3">
          <Button variant="secondary" onClick={onEdit}>
            Исправить
          </Button>
          <Button variant="primary" icon={Check} onClick={onConfirm}>
            Показать
          </Button>
        </div>
      </div>
    </div>
  )
}
