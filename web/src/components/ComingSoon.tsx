import { Clock } from 'lucide-react'

/**
 * w3-13 · Честный сигнпостинг для ещё не реализованных разделов (§9.4).
 * Заменяет generic `Placeholder` («Раздел в разработке») в catch-all: вместо
 * ощущения пустого 404 — название секции, одна строка описания и пилюля статуса.
 * Карта `path → props` живёт в `App.tsx`.
 *
 * f22 · Пилюля честна по виду пункта (`kind`):
 *   `'soon'`   — scaffold/in-progress: «Скоро · Волна N» (warning, обещание волны);
 *   `'future'` — вне скоупа / нужен новый источник: «Будущее» (нейтральный тон,
 *                БЕЗ «Волна N» — обещания конкретной волны нет).
 * Так пилюля карточки согласована с бейджем сайдбара (`NAV`).
 */
export interface ComingSoonProps {
  title: string
  description: string
  wave: number
  kind?: 'soon' | 'future'
}

export function ComingSoon({
  title,
  description,
  wave,
  kind = 'soon',
}: ComingSoonProps) {
  return (
    <div className="grid h-full place-items-center">
      <div className="max-w-md px-4 text-center">
        <div className="mx-auto grid h-12 w-12 place-items-center rounded-xl bg-primary-50 text-primary">
          <Clock className="h-6 w-6" strokeWidth={1.75} aria-hidden />
        </div>
        <div className="mt-4 text-[18px] font-semibold text-ink">{title}</div>
        <p className="mt-1 text-[13px] leading-relaxed text-muted">
          {description}
        </p>
        {kind === 'future' ? (
          <span className="mt-4 inline-flex items-center gap-1.5 rounded-xl border border-border bg-bg px-3 py-1 text-[12px] font-medium text-muted">
            <span className="h-1.5 w-1.5 rounded-full bg-muted" aria-hidden />
            Будущее
          </span>
        ) : (
          <span className="mt-4 inline-flex items-center gap-1.5 rounded-xl bg-warning-bg px-3 py-1 text-[12px] font-medium text-warning-text">
            <span className="h-1.5 w-1.5 rounded-full bg-warning" aria-hidden />
            Скоро · Волна {wave}
          </span>
        )}
      </div>
    </div>
  )
}
