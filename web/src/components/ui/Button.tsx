import { type ButtonHTMLAttributes, type ReactNode } from 'react'
import { Loader2, type LucideIcon } from 'lucide-react'
import { cn } from './cn'

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Визуальный вариант (DESIGN.md §Кнопки). */
  variant?: ButtonVariant
  /** Иконка Lucide слева от текста (или единственное содержимое icon-кнопки). */
  icon?: LucideIcon
  /** Состояние загрузки: показывает спиннер и блокирует клики. */
  loading?: boolean
  children?: ReactNode
}

// Цвета только из токенов d1; danger-hover — brightness (нет токена critical-dark).
const VARIANT: Record<ButtonVariant, string> = {
  primary: 'bg-primary text-white hover:bg-primary-dark',
  secondary: 'bg-surface border border-border text-ink hover:border-primary',
  danger: 'bg-critical text-white hover:brightness-90',
  ghost: 'bg-transparent text-muted hover:bg-bg',
}

export function Button({
  variant = 'primary',
  icon: Icon,
  loading = false,
  disabled,
  className,
  children,
  ...rest
}: ButtonProps) {
  const iconOnly = children == null || children === false
  return (
    <button
      type="button"
      disabled={disabled || loading}
      className={cn(
        'inline-flex items-center justify-center gap-2 h-9 rounded-md text-sm font-medium',
        'transition-all duration-150 ease-in-out',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        iconOnly ? 'w-9 px-0' : 'px-4',
        VARIANT[variant],
        className,
      )}
      {...rest}
    >
      {loading ? (
        <Loader2 size={16} className="animate-spin" aria-hidden />
      ) : (
        Icon && <Icon size={16} aria-hidden />
      )}
      {children}
    </button>
  )
}
