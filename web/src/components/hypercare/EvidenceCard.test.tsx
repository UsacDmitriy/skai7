import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, test, vi } from 'vitest'
import EvidenceCard from './EvidenceCard'
import type { HypercareEvidence } from '@/api/types'

const fulfilled: HypercareEvidence = {
  id: 'ev-1',
  rule_id: 'R-SABOTAGE',
  rule_name: 'Вскрытие кузова',
  vehicle_plate: 'А001АА77',
  trigger_ts: '2026-06-29T10:00:00',
  trigger_label: 'Вскрытие (TRUCK_BODY)',
  status: 'fulfilled',
  items: [
    { channel: 1, kind: 'video', offset_sec: -300, status: 'available' },
    { channel: 5, kind: 'video', offset_sec: -300, status: 'available' },
  ],
}

const pending: HypercareEvidence = {
  ...fulfilled,
  id: 'ev-2',
  status: 'pending',
  driver: 'Иванов И.И.',
  items: [
    { channel: 1, kind: 'video', offset_sec: -60, status: 'pending', eta_sec: 45 },
  ],
}

describe('EvidenceCard', () => {
  test('renders vehicle plate', () => {
    render(<EvidenceCard evidence={fulfilled} onOpenClip={vi.fn()} />)
    expect(screen.getByText('А001АА77')).toBeTruthy()
  })

  test('shows status badge', () => {
    render(<EvidenceCard evidence={fulfilled} onOpenClip={vi.fn()} />)
    expect(screen.getByText('Готово')).toBeTruthy()
  })

  test('shows pending status badge', () => {
    render(<EvidenceCard evidence={pending} onOpenClip={vi.fn()} />)
    expect(screen.getByText('Ожидание')).toBeTruthy()
  })

  test('renders trigger label', () => {
    render(<EvidenceCard evidence={fulfilled} onOpenClip={vi.fn()} />)
    expect(screen.getByText('Вскрытие (TRUCK_BODY)')).toBeTruthy()
  })

  test('shows rule name', () => {
    render(<EvidenceCard evidence={fulfilled} onOpenClip={vi.fn()} />)
    expect(screen.getByText(/Вскрытие кузова/)).toBeTruthy()
  })

  test('shows driver when provided', () => {
    render(<EvidenceCard evidence={pending} onOpenClip={vi.fn()} />)
    expect(screen.getByText('Иванов И.И.')).toBeTruthy()
  })

  test('does not render driver row when absent', () => {
    render(<EvidenceCard evidence={fulfilled} onOpenClip={vi.fn()} />)
    expect(screen.queryByText(/И\.И\./)).toBeNull()
  })

  test('clicking available clip calls onOpenClip', () => {
    const onOpenClip = vi.fn()
    render(<EvidenceCard evidence={fulfilled} onOpenClip={onOpenClip} />)
    fireEvent.click(screen.getByLabelText(/ADAS available/))
    expect(onOpenClip).toHaveBeenCalledWith(fulfilled.items[0])
  })
})
