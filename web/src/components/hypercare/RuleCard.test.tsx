import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, test, vi } from 'vitest'
import RuleCard, { windowSummary } from './RuleCard'
import type { HypercareRule } from '@/api/types'

const rule: HypercareRule = {
  id: 'R-TEST',
  name: 'Тест авария',
  enabled: true,
  role_scope: 'all',
  trigger: { kind: 'event', alarm_codes: ['CRASH'] },
  window: { before_sec: 300, after_sec: 120, mode: 'continuous' },
  cameras: [1, 5],
}

describe('windowSummary', () => {
  test('continuous mode', () => {
    expect(windowSummary(rule)).toBe('−5м … +2м · непрерыв.')
  })

  test('clip mode', () => {
    const r = { ...rule, window: { ...rule.window, mode: 'clip' as const, clip_len_sec: 15 } }
    expect(windowSummary(r)).toBe('−5м … +2м · клип 15с')
  })

  test('interval/photo mode', () => {
    const r = { ...rule, window: { ...rule.window, mode: 'interval' as const, interval_sec: 60, before_sec: 0 } }
    expect(windowSummary(r)).toBe('−0 … +2м · фото/1м')
  })
})

describe('RuleCard', () => {
  test('renders rule name', () => {
    render(<RuleCard rule={rule} onToggle={vi.fn()} />)
    expect(screen.getByText('Тест авария')).toBeTruthy()
  })

  test('shows alarm codes', () => {
    render(<RuleCard rule={rule} onToggle={vi.fn()} />)
    expect(screen.getByText(/CRASH/)).toBeTruthy()
  })

  test('toggle calls onToggle with rule id', () => {
    const onToggle = vi.fn()
    render(<RuleCard rule={rule} onToggle={onToggle} />)
    fireEvent.click(screen.getByRole('switch'))
    expect(onToggle).toHaveBeenCalledWith('R-TEST')
  })

  test('switch aria-checked reflects enabled state', () => {
    render(<RuleCard rule={{ ...rule, enabled: false }} onToggle={vi.fn()} />)
    expect(screen.getByRole('switch').getAttribute('aria-checked')).toBe('false')
  })

  test('shows camera list', () => {
    render(<RuleCard rule={rule} onToggle={vi.fn()} />)
    expect(screen.getByText(/1.*5/)).toBeTruthy()
  })
})
