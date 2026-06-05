/**
 * f13 · Общее состояние роли оператора (идея #10).
 *
 * Одна точка истины для роли во всех экранах (лента + карта). Значение персистится
 * в `localStorage`; повреждённое/неизвестное значение → откат на дефолт «Диспетчер»
 * без падения. Без `Date.now()` в логике.
 *
 * Размещение в `state/` согласовано так, чтобы не пересекаться с роутингом (f1).
 */
import {
  createContext,
  createElement,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import type { Role } from '@/components/map/types'

export type { Role }

/** Ключ персиста роли в localStorage. */
export const ROLE_STORAGE_KEY = 'skai.role'

/** Дефолтная роль — Диспетчер (полный доступ). */
export const DEFAULT_ROLE: Role = 'dispatcher'

const ROLES: readonly Role[] = ['logist', 'dispatcher', 'security']

/** Type-guard валидной роли (чистый). */
export function isRole(value: unknown): value is Role {
  return typeof value === 'string' && (ROLES as readonly string[]).includes(value)
}

/** Разбор сохранённого значения: валидная роль или дефолт (чистый, без localStorage). */
export function parseStoredRole(raw: string | null): Role {
  return isRole(raw) ? raw : DEFAULT_ROLE
}

/** Чтение роли из localStorage с откатом на дефолт (безопасно вне браузера). */
function readPersistedRole(): Role {
  if (typeof localStorage === 'undefined') return DEFAULT_ROLE
  try {
    return parseStoredRole(localStorage.getItem(ROLE_STORAGE_KEY))
  } catch {
    return DEFAULT_ROLE
  }
}

// ── Контекст / провайдер / хук ────────────────────────────────────────────────

interface RoleContextValue {
  role: Role
  setRole: (role: Role) => void
}

const RoleContext = createContext<RoleContextValue | null>(null)

/**
 * Провайдер роли: ленивая инициализация из localStorage, персист при смене.
 * Монтируется один раз над всем приложением (App), чтобы лента и карта читали
 * одну роль согласованно.
 */
export function RoleProvider({ children }: { children: ReactNode }) {
  const [role, setRoleState] = useState<Role>(readPersistedRole)

  useEffect(() => {
    try {
      localStorage.setItem(ROLE_STORAGE_KEY, role)
    } catch {
      /* приватный режим / quota — персист необязателен, роль живёт в памяти */
    }
  }, [role])

  const setRole = useCallback((next: Role) => {
    setRoleState(isRole(next) ? next : DEFAULT_ROLE)
  }, [])

  return createElement(RoleContext.Provider, { value: { role, setRole } }, children)
}

/** Доступ к роли и сеттеру. Бросает вне `RoleProvider` (явная ошибка интеграции). */
export function useRole(): RoleContextValue {
  const ctx = useContext(RoleContext)
  if (!ctx) throw new Error('useRole должен использоваться внутри <RoleProvider>')
  return ctx
}
