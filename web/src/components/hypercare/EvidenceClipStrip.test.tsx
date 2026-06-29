import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, test, vi } from 'vitest'
import EvidenceClipStrip from './EvidenceClipStrip'
import type { HypercareEvidenceClip } from '@/api/types'

const clips: HypercareEvidenceClip[] = [
  { channel: 1, kind: 'video', offset_sec: -300, status: 'available' },
  { channel: 5, kind: 'video', offset_sec: -300, status: 'pending', eta_sec: 42 },
  { channel: 2, kind: 'video', offset_sec: -300, status: 'pending' },
]

describe('EvidenceClipStrip', () => {
  test('renders clip buttons for each item', () => {
    render(<EvidenceClipStrip items={clips} onOpen={vi.fn()} />)
    expect(screen.getAllByRole('listitem')).toHaveLength(3)
  })

  test('shows channel labels', () => {
    render(<EvidenceClipStrip items={clips} onOpen={vi.fn()} />)
    expect(screen.getByText('ADAS')).toBeTruthy()
    expect(screen.getByText('DMS')).toBeTruthy()
    expect(screen.getByText('SNZ-L')).toBeTruthy()
  })

  test('calls onOpen when available clip clicked', () => {
    const onOpen = vi.fn()
    render(<EvidenceClipStrip items={clips} onOpen={onOpen} />)
    fireEvent.click(screen.getByLabelText(/ADAS available/))
    expect(onOpen).toHaveBeenCalledWith(clips[0])
  })

  test('does not call onOpen for pending clip', () => {
    const onOpen = vi.fn()
    render(<EvidenceClipStrip items={clips} onOpen={onOpen} />)
    const pendingBtn = screen.getByLabelText(/SNZ-L pending/)
    expect(pendingBtn).toBeDisabled()
  })

  test('shows ETA for pending clip', () => {
    render(<EvidenceClipStrip items={clips} onOpen={vi.fn()} />)
    expect(screen.getByText(/42с/)).toBeTruthy()
  })

  test('renders empty state when no items', () => {
    render(<EvidenceClipStrip items={[]} onOpen={vi.fn()} />)
    expect(screen.getByText(/Нет медиа/)).toBeTruthy()
  })
})
