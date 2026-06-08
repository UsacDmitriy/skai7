import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { Card } from './Card'

/**
 * d3 · Card (component-lib) — композиция рендерится и пробрасывает props:
 *  • variant `incident` красит левую полосу по severity (медиум→warning, low→ok);
 *  • `onClick` делает карточку интерактивной (role=button + Enter/Space);
 *  • `selected`/`className` пробрасываются в разметку.
 * Дополняет t3 (DataTable уже покрыт) — не дублирует.
 */
describe('Card · d3 component-lib', () => {
  it('default-вариант: непрозрачный контейнер, не интерактивен', () => {
    render(<Card>контент</Card>)
    const text = screen.getByText('контент')
    const card = text.closest('div') as HTMLElement
    expect(card).toBeInTheDocument()
    expect(card).not.toHaveAttribute('role')
    expect(card.className).toContain('p-5')
  })

  it('incident-вариант: цвет левой полосы по severity (medium→warning, low→ok)', () => {
    const { rerender, container } = render(
      <Card variant="incident" severity="medium">
        строка
      </Card>,
    )
    let card = container.firstElementChild as HTMLElement
    expect(card.className).toContain('border-l-4')
    expect(card.className).toContain('border-l-warning')

    rerender(
      <Card variant="incident" severity="critical">
        строка
      </Card>,
    )
    card = container.firstElementChild as HTMLElement
    expect(card.className).toContain('border-l-critical')

    rerender(
      <Card variant="incident" severity="low">
        строка
      </Card>,
    )
    card = container.firstElementChild as HTMLElement
    expect(card.className).toContain('border-l-ok')
  })

  it('onClick делает карточку кнопкой и активируется кликом / Enter / Space', () => {
    const onClick = vi.fn()
    render(<Card onClick={onClick}>кликни</Card>)
    const card = screen.getByRole('button')
    expect(card).toHaveAttribute('tabindex', '0')

    fireEvent.click(card)
    fireEvent.keyDown(card, { key: 'Enter' })
    fireEvent.keyDown(card, { key: ' ' })
    expect(onClick).toHaveBeenCalledTimes(3)
  })

  it('selected и className пробрасываются', () => {
    const { container } = render(
      <Card selected className="my-custom">
        x
      </Card>,
    )
    const card = container.firstElementChild as HTMLElement
    expect(card.className).toContain('bg-primary-50')
    expect(card.className).toContain('my-custom')
  })
})
