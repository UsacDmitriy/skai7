import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { Bell } from 'lucide-react'
import { Button } from './Button'

/**
 * d3 · Button (component-lib) — варианты/состояния и проброс props:
 *  • `loading`/`disabled` блокируют клик (disabled);
 *  • icon-only (без children) даёт квадратную кнопку (w-9);
 *  • произвольные HTML-атрибуты (aria-label) пробрасываются на <button>.
 */
describe('Button · d3 component-lib', () => {
  it('клик вызывает onClick, loading/disabled — блокируют', () => {
    const onClick = vi.fn()
    const { rerender } = render(<Button onClick={onClick}>Жми</Button>)
    fireEvent.click(screen.getByRole('button', { name: 'Жми' }))
    expect(onClick).toHaveBeenCalledTimes(1)

    rerender(
      <Button onClick={onClick} loading>
        Жми
      </Button>,
    )
    const btn = screen.getByRole('button')
    expect(btn).toBeDisabled()
    fireEvent.click(btn)
    expect(onClick).toHaveBeenCalledTimes(1) // клик не прошёл

    rerender(
      <Button onClick={onClick} disabled>
        Жми
      </Button>,
    )
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('icon-only (без текста) — квадратная кнопка, aria-label пробрасывается', () => {
    render(<Button icon={Bell} aria-label="Уведомления" />)
    const btn = screen.getByRole('button', { name: 'Уведомления' })
    expect(btn.className).toContain('w-9')
  })

  it('вариант меняет цветовые классы', () => {
    const { rerender } = render(<Button variant="danger">x</Button>)
    expect(screen.getByRole('button').className).toContain('bg-critical')
    rerender(<Button variant="ghost">x</Button>)
    expect(screen.getByRole('button').className).toContain('bg-transparent')
  })
})
