import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, test, vi } from 'vitest'
import RuleBuilder from './RuleBuilder'

function fillForm() {
  fireEvent.change(screen.getByLabelText('Гос. номер ТС'), { target: { value: 'а001аа77' } })
  fireEvent.change(screen.getByLabelText('Время события'), { target: { value: '2026-06-29T10:00' } })
}

describe('RuleBuilder', () => {
  test('renders form fields', () => {
    render(<RuleBuilder onSubmit={vi.fn()} />)
    expect(screen.getByLabelText('Гос. номер ТС')).toBeTruthy()
    expect(screen.getByLabelText('Время события')).toBeTruthy()
    expect(screen.getByLabelText('Секунд до события')).toBeTruthy()
    expect(screen.getByLabelText('Секунд после события')).toBeTruthy()
  })

  test('submit disabled when plate is empty', () => {
    render(<RuleBuilder onSubmit={vi.fn()} />)
    expect(screen.getByRole('button', { name: /Запросить/ })).toBeDisabled()
  })

  test('submit enabled after filling required fields', () => {
    render(<RuleBuilder onSubmit={vi.fn()} />)
    fillForm()
    expect(screen.getByRole('button', { name: /Запросить/ })).not.toBeDisabled()
  })

  test('calls onSubmit with uppercased plate and ISO timestamp', () => {
    const onSubmit = vi.fn()
    render(<RuleBuilder onSubmit={onSubmit} />)
    fillForm()
    fireEvent.click(screen.getByRole('button', { name: /Запросить/ }))
    expect(onSubmit).toHaveBeenCalledOnce()
    const arg = onSubmit.mock.calls[0][0]
    expect(arg.vehicle_plate).toBe('А001АА77')
    expect(arg.trigger_ts).toMatch(/^2026-06-29T/)
  })

  test('cameras toggle on/off', () => {
    render(<RuleBuilder onSubmit={vi.fn()} />)
    const dms = screen.getByLabelText('Камера DMS')
    // DMS (ch=5) starts checked
    expect(dms.getAttribute('aria-checked')).toBe('true')
    fireEvent.click(dms)
    expect(dms.getAttribute('aria-checked')).toBe('false')
    fireEvent.click(dms)
    expect(dms.getAttribute('aria-checked')).toBe('true')
  })

  test('submit disabled when no cameras selected', () => {
    render(<RuleBuilder onSubmit={vi.fn()} />)
    fillForm()
    // Uncheck all default cameras
    fireEvent.click(screen.getByLabelText('Камера ADAS'))
    fireEvent.click(screen.getByLabelText('Камера DMS'))
    expect(screen.getByRole('button', { name: /Запросить/ })).toBeDisabled()
  })

  test('shows loading state', () => {
    render(<RuleBuilder onSubmit={vi.fn()} loading />)
    expect(screen.getByRole('button', { name: /Запрос/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: /Запрос/ }).getAttribute('aria-busy')).toBe('true')
  })
})
