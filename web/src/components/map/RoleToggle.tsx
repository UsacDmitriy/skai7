import { cn } from '../ui/cn'
import type { Role } from './types'

/**
 * RoleToggle — переключатель роли оператора (segmented chips, §7.6).
 *
 * Только presentation: эмитит `onChange`. Фильтрацию слоёв по роли делает f13.
 * Активный chip — `bg-primary` + белый текст; неактивный — `bg-primary-50` +
 * текст `primary`. Скругление `xl` (12px), плавный переход.
 *
 * a11y: группа сегментов `role="radiogroup"`, каждый chip — `role="radio"` с
 * `aria-checked`; видимый фокус (focus-visible ring).
 */
export interface RoleToggleProps {
  value: Role
  onChange: (role: Role) => void
  className?: string
}

const ROLES: { role: Role; emoji: string; label: string }[] = [
  { role: 'logist', emoji: '🏭', label: 'Логист' },
  { role: 'dispatcher', emoji: '🛡', label: 'Диспетчер' },
  { role: 'security', emoji: '🔒', label: 'Безопасник' },
]

export function RoleToggle({ value, onChange, className }: RoleToggleProps) {
  return (
    <div
      role="radiogroup"
      aria-label="Роль оператора"
      className={cn('inline-flex gap-1 rounded-xl bg-primary-50 p-1', className)}
    >
      {ROLES.map(({ role, emoji, label }) => {
        const active = role === value
        return (
          <button
            key={role}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(role)}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-sm font-medium',
              'transition-colors duration-150',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1',
              active
                ? 'bg-primary text-white shadow-sm'
                : 'bg-primary-50 text-primary hover:bg-white',
            )}
          >
            <span aria-hidden>{emoji}</span>
            {label}
          </button>
        )
      })}
    </div>
  )
}
