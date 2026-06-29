import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { SmartQueryInput } from './SmartQueryInput'

describe('SmartQueryInput', () => {
  it('печать эмитит onChange', () => {
    const onChange = vi.fn()
    render(<SmartQueryInput value="" onChange={onChange} />)
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'гусев' } })
    expect(onChange).toHaveBeenCalledWith('гусев')
  })
  it('Enter эмитит onSubmit с текущим текстом', () => {
    const onSubmit = vi.fn()
    render(<SmartQueryInput value="курение" onChange={vi.fn()} onSubmit={onSubmit} />)
    fireEvent.keyDown(screen.getByRole('searchbox'), { key: 'Enter' })
    expect(onSubmit).toHaveBeenCalledWith('курение')
  })
  it('клик по чипу-подсказке эмитит onChange и onSubmit', () => {
    const onChange = vi.fn()
    const onSubmit = vi.fn()
    render(
      <SmartQueryInput value="" onChange={onChange} onSubmit={onSubmit} suggestions={['рейтинг водителей']} />,
    )
    fireEvent.click(screen.getByRole('button', { name: 'рейтинг водителей' }))
    expect(onChange).toHaveBeenCalledWith('рейтинг водителей')
    expect(onSubmit).toHaveBeenCalledWith('рейтинг водителей')
  })
  it('voice=false → нет кнопки записи', () => {
    render(<SmartQueryInput value="" onChange={vi.fn()} />)
    expect(screen.queryByLabelText(/Записать голосовой запрос/)).toBeNull()
  })
})
