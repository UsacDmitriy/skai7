/**
 * Состояние правил Гиперопеки. Seed приходит с бэкенда (GET /rules); локальные
 * правки (enable/disable, новые правила) — overlay в localStorage. Паттерн
 * повторяет state/role.ts: ленивая инициализация, безопасный парс, без Date.now().
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
import type { HypercareRule } from '@/api/types'

export const HYPERCARE_STORAGE_KEY = 'skai.hypercare.overlay'

/** Overlay: по id правила — переопределяемые поля (MVP: enabled). */
export type RuleOverlay = Record<string, { enabled?: boolean }>

export function parseStoredOverlay(raw: string | null): RuleOverlay {
  if (!raw) return {}
  try {
    const v = JSON.parse(raw)
    return v && typeof v === 'object' ? (v as RuleOverlay) : {}
  } catch {
    return {}
  }
}

export function mergeRules(seed: HypercareRule[], overlay: RuleOverlay): HypercareRule[] {
  return seed.map((r) =>
    overlay[r.id]?.enabled === undefined
      ? r
      : { ...r, enabled: overlay[r.id].enabled as boolean },
  )
}

function readOverlay(): RuleOverlay {
  if (typeof localStorage === 'undefined') return {}
  try {
    return parseStoredOverlay(localStorage.getItem(HYPERCARE_STORAGE_KEY))
  } catch {
    return {}
  }
}

interface Ctx {
  rules: HypercareRule[]
  toggleRule: (id: string) => void
  addRule: (rule: HypercareRule) => void
  setSeed: (seed: HypercareRule[]) => void
}

const HypercareCtx = createContext<Ctx | null>(null)

export function HypercareRulesProvider({ children }: { children: ReactNode }) {
  const [seed, setSeedState] = useState<HypercareRule[]>([])
  const [custom, setCustom] = useState<HypercareRule[]>([])
  const [overlay, setOverlay] = useState<RuleOverlay>(readOverlay)

  useEffect(() => {
    try {
      localStorage.setItem(HYPERCARE_STORAGE_KEY, JSON.stringify(overlay))
    } catch {
      /* приватный режим — overlay живёт в памяти */
    }
  }, [overlay])

  const all = mergeRules([...seed, ...custom], overlay)

  const toggleRule = useCallback((id: string) => {
    setOverlay((o) => {
      // Дефолт ищем в объединённом списке (seed + custom): кастомное правило
      // с enabled=false иначе требовало бы двойного клика (фолбэк ?? true был неверен).
      const base = o[id]?.enabled ?? [...seed, ...custom].find((r) => r.id === id)?.enabled ?? true
      return { ...o, [id]: { enabled: !base } }
    })
  }, [seed, custom])

  const addRule = useCallback((rule: HypercareRule) => {
    setCustom((c) => [...c, rule])
  }, [])

  const setSeed = useCallback((s: HypercareRule[]) => setSeedState(s), [])

  return createElement(
    HypercareCtx.Provider,
    { value: { rules: all, toggleRule, addRule, setSeed } },
    children,
  )
}

export function useHypercareRules(): Ctx {
  const ctx = useContext(HypercareCtx)
  if (!ctx) throw new Error('useHypercareRules должен использоваться внутри <HypercareRulesProvider>')
  return ctx
}
