import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SeverityBadge } from './SeverityBadge'

/**
 * d2 · SeverityBadge — маппинг API-severity → токен-палитра d1 (CONTRACT §4):
 *   critical→critical · high→high · medium→warning(жёлтый) · low→ok(зелёный).
 * Гейт Check: доказать medium→warning и low→ok.
 */
describe('SeverityBadge', () => {
  it('medium → warning-палитра (жёлтый), включая точку', () => {
    render(<SeverityBadge severity="medium" label="Средний" />)
    const badge = screen.getByText('Средний')
    expect(badge).toHaveClass('bg-warning-bg', 'text-warning-text')
    const dot = badge.querySelector('[aria-hidden]')
    expect(dot).toHaveClass('bg-warning')
  })

  it('low → ok-палитра (зелёный), включая точку', () => {
    render(<SeverityBadge severity="low" label="Низкий" />)
    const badge = screen.getByText('Низкий')
    expect(badge).toHaveClass('bg-ok-bg', 'text-ok-text')
    expect(badge.querySelector('[aria-hidden]')).toHaveClass('bg-ok')
  })

  it('critical → critical-палитра', () => {
    render(<SeverityBadge severity="critical" label="Критично" />)
    const badge = screen.getByText('Критично')
    expect(badge).toHaveClass('bg-critical-bg', 'text-critical-text')
    expect(badge.querySelector('[aria-hidden]')).toHaveClass('bg-critical')
  })

  it('high → high-палитра', () => {
    render(<SeverityBadge severity="high" label="Высокий" />)
    const badge = screen.getByText('Высокий')
    expect(badge).toHaveClass('bg-high-bg', 'text-high-text')
    expect(badge.querySelector('[aria-hidden]')).toHaveClass('bg-high')
  })

  it('пробрасывает className потребителя', () => {
    render(<SeverityBadge severity="low" label="Низкий" className="ml-2" />)
    expect(screen.getByText('Низкий')).toHaveClass('ml-2')
  })
})
