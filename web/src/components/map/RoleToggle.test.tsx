import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { RoleToggle } from './RoleToggle'

/**
 * f13 · RoleToggle — segmented-переключатель роли оператора (§7.6).
 * Презентация: отражает `value` (aria-checked) и эмитит `onChange`. Согласованную
 * смену видимости слоёв/колонок по роли проверяют экранные тесты (EventsFeed/Monitor)
 * и чистый `roleFilter` — здесь покрываем сам примитив-переключатель.
 */
describe('f13 · RoleToggle', () => {
  it('radiogroup из трёх ролей; активная отражена aria-checked', () => {
    render(<RoleToggle value="dispatcher" onChange={vi.fn()} />)
    expect(screen.getByRole('radiogroup', { name: 'Роль оператора' })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /Логист/ })).toHaveAttribute('aria-checked', 'false')
    expect(screen.getByRole('radio', { name: /Диспетчер/ })).toHaveAttribute('aria-checked', 'true')
    expect(screen.getByRole('radio', { name: /Безопасник/ })).toHaveAttribute('aria-checked', 'false')
  })

  it('клик по роли эмитит onChange с её кодом', () => {
    const onChange = vi.fn()
    render(<RoleToggle value="dispatcher" onChange={onChange} />)
    fireEvent.click(screen.getByRole('radio', { name: /Логист/ }))
    expect(onChange).toHaveBeenCalledWith('logist')
    fireEvent.click(screen.getByRole('radio', { name: /Безопасник/ }))
    expect(onChange).toHaveBeenCalledWith('security')
  })

  it('смена value переносит активный сегмент', () => {
    const { rerender } = render(<RoleToggle value="logist" onChange={vi.fn()} />)
    expect(screen.getByRole('radio', { name: /Логист/ })).toHaveAttribute('aria-checked', 'true')
    rerender(<RoleToggle value="security" onChange={vi.fn()} />)
    expect(screen.getByRole('radio', { name: /Логист/ })).toHaveAttribute('aria-checked', 'false')
    expect(screen.getByRole('radio', { name: /Безопасник/ })).toHaveAttribute('aria-checked', 'true')
  })
})
