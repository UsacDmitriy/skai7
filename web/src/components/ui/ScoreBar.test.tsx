import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ScoreBar } from './ScoreBar'

/**
 * d2 · ScoreBar — градиентная заливка (.score-bar-fill, ширина = % значения) и
 * числовое значение моноширинными цифрами (tabular-nums). Вне диапазона — кламп 0..100.
 */
describe('ScoreBar', () => {
  it('рисует градиентную заливку шириной = значению', () => {
    const { container } = render(<ScoreBar score={42} />)
    const fill = container.querySelector('.score-bar-fill') as HTMLElement
    expect(fill).toBeInTheDocument()
    expect(fill.style.width).toBe('42%')
  })

  it('значение — tabular-nums', () => {
    render(<ScoreBar score={42} />)
    const value = screen.getByText('42')
    expect(value).toHaveClass('tabular-nums')
  })

  it('клампит значения выше 100', () => {
    const { container } = render(<ScoreBar score={150} />)
    expect(screen.getByText('100')).toBeInTheDocument()
    expect((container.querySelector('.score-bar-fill') as HTMLElement).style.width).toBe('100%')
  })

  it('клампит отрицательные значения к 0', () => {
    const { container } = render(<ScoreBar score={-10} />)
    expect(screen.getByText('0')).toBeInTheDocument()
    expect((container.querySelector('.score-bar-fill') as HTMLElement).style.width).toBe('0%')
  })

  it('округляет дробные значения', () => {
    render(<ScoreBar score={66.7} />)
    expect(screen.getByText('67')).toBeInTheDocument()
  })
})
