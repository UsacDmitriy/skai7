import { describe, expect, test, beforeEach } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import type { ReactNode } from 'react'
import {
  HYPERCARE_STORAGE_KEY,
  HypercareRulesProvider,
  useHypercareRules,
} from './hypercareRules'
import type { HypercareRule } from '@/api/types'

const baseRule: HypercareRule = {
  id: 'R1',
  name: 'seed',
  enabled: true,
  role_scope: 'all',
  trigger: { kind: 'event', alarm_codes: ['X'] },
  window: { before_sec: 0, after_sec: 0, mode: 'continuous' },
  cameras: [1],
}

const wrapper = ({ children }: { children: ReactNode }) => (
  <HypercareRulesProvider>{children}</HypercareRulesProvider>
)

describe('HypercareRulesProvider · toggleRule', () => {
  beforeEach(() => localStorage.removeItem(HYPERCARE_STORAGE_KEY))

  test('одиночный клик включает КАСТОМНОЕ правило с enabled=false (регресс: был двойной клик)', () => {
    const { result } = renderHook(() => useHypercareRules(), { wrapper })

    const custom: HypercareRule = { ...baseRule, id: 'C1', name: 'custom', enabled: false }
    act(() => result.current.addRule(custom))
    expect(result.current.rules.find((r) => r.id === 'C1')?.enabled).toBe(false)

    act(() => result.current.toggleRule('C1'))
    // до фикса фолбэк ?? true давал !true = false → правило оставалось выключенным
    expect(result.current.rules.find((r) => r.id === 'C1')?.enabled).toBe(true)
  })

  test('toggle seed-правила по-прежнему работает с одного клика', () => {
    const { result } = renderHook(() => useHypercareRules(), { wrapper })
    act(() => result.current.setSeed([baseRule]))
    expect(result.current.rules[0].enabled).toBe(true)
    act(() => result.current.toggleRule('R1'))
    expect(result.current.rules[0].enabled).toBe(false)
  })
})
