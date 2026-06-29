import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { RoleToggle } from './RoleToggle'

/**
 * f13 · RoleToggle — segmented-переключатель роли оператора (§7.6).
 * Презентация: отражает `value` (aria-checked) и эмитит `onChange`. Лейблы после
 * переименования ролей (S488/S489): logist→«Логист», dispatcher→«Спец. мониторинга»,
 * security→«Диспетчер». Внутренние коды ролей неизменны.
 */
describe('f13 · RoleToggle', () => {
  it('radiogroup из трёх ролей; активная отражена aria-checked', () => {
    render(<RoleToggle value="dispatcher" onChange={vi.fn()} />)
    expect(screen.getByRole('radiogroup', { name: 'Роль оператора' })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /Логист/ })).toHaveAttribute('aria-checked', 'false')
    expect(screen.getByRole('radio', { name: /Спец/ })).toHaveAttribute('aria-checked', 'true')
    expect(screen.getByRole('radio', { name: /Диспетчер/ })).toHaveAttribute('aria-checked', 'false')
  })

  it('клик по роли эмитит onChange с её кодом', () => {
    const onChange = vi.fn()
    render(<RoleToggle value="dispatcher" onChange={onChange} />)
    fireEvent.click(screen.getByRole('radio', { name: /Логист/ }))
    expect(onChange).toHaveBeenCalledWith('logist')
    fireEvent.click(screen.getByRole('radio', { name: /Диспетчер/ }))
    expect(onChange).toHaveBeenCalledWith('security')
  })

  it('смена value переносит активный сегмент', () => {
    const { rerender } = render(<RoleToggle value="logist" onChange={vi.fn()} />)
    expect(screen.getByRole('radio', { name: /Логист/ })).toHaveAttribute('aria-checked', 'true')
    rerender(<RoleToggle value="security" onChange={vi.fn()} />)
    expect(screen.getByRole('radio', { name: /Логист/ })).toHaveAttribute('aria-checked', 'false')
    expect(screen.getByRole('radio', { name: /Диспетчер/ })).toHaveAttribute('aria-checked', 'true')
  })
})
