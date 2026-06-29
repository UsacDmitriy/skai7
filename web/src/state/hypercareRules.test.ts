import { describe, expect, test } from 'vitest'
import { mergeRules, parseStoredOverlay } from './hypercareRules'
import type { HypercareRule } from '@/api/types'

const seed: HypercareRule[] = [
  {
    id: 'R1',
    name: 'A',
    enabled: true,
    role_scope: 'all',
    trigger: { kind: 'event', alarm_codes: ['X'] },
    window: { before_sec: 0, after_sec: 0, mode: 'continuous' },
    cameras: [1],
  },
]

describe('hypercareRules overlay', () => {
  test('overlay enabled-flag overrides seed', () => {
    const merged = mergeRules(seed, { R1: { enabled: false } })
    expect(merged[0].enabled).toBe(false)
  })

  test('parseStoredOverlay tolerates garbage', () => {
    expect(parseStoredOverlay('not-json')).toEqual({})
    expect(parseStoredOverlay(null)).toEqual({})
  })

  test('merge keeps seed order and adds custom rules', () => {
    const custom: HypercareRule = { ...seed[0], id: 'C1', name: 'Custom' }
    const merged = mergeRules([...seed, custom], { C1: { enabled: false } })
    expect(merged.map((r) => r.id)).toEqual(['R1', 'C1'])
    expect(merged[1].enabled).toBe(false)
  })

  test('no overlay leaves rule unchanged', () => {
    const merged = mergeRules(seed, {})
    expect(merged[0].enabled).toBe(true)
  })
})
