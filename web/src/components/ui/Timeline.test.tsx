import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { Timeline, type TimelineEvent } from './Timeline'

/**
 * d5 · Timeline (voice-timeline) — принимает события трека и двигает курсор-плейхед:
 *  • рендерит точку-кнопку на каждое событие; `onSelect` отдаёт событие;
 *  • t=0 — крупная critical-точка (§7.6);
 *  • `has_video` помечает точку (в доступном имени «есть видео»);
 *  • `playheadOffset` внутри диапазона рисует курсор и двигает его; вне — скрывает.
 */
const EVENTS: TimelineEvent[] = [
  { ts_offset: -60, alarm_code: 'OVERSPEED', label: 'Превышение', severity: 'high', has_video: true },
  { ts_offset: 0, alarm_code: 'CRASH_SENSOR', label: 'ДТП', severity: 'critical', has_video: true },
  { ts_offset: 30, alarm_code: 'HARSH_BRAKING', label: 'Торможение', severity: 'medium', has_video: false },
]

function playhead(container: HTMLElement): HTMLElement | null {
  return container.querySelector('div.bg-ink')
}

describe('Timeline · d5 voice-timeline', () => {
  it('рендерит кнопку на каждое событие, t=0 — крупная critical-точка', () => {
    render(<Timeline events={EVENTS} />)
    expect(screen.getByRole('button', { name: /Превышение, -60s, есть видео/ })).toBeInTheDocument()
    const zero = screen.getByRole('button', { name: /ДТП, t=0/ })
    expect(zero.querySelector('span.bg-critical.h-4.w-4')).toBeInTheDocument()
  })

  it('has_video отражается в доступном имени точки', () => {
    render(<Timeline events={EVENTS} />)
    // событие без видео — без суффикса «есть видео»
    const noVideo = screen.getByRole('button', { name: 'Торможение, +30s' })
    expect(noVideo).toBeInTheDocument()
  })

  it('onSelect отдаёт выбранное событие', () => {
    const onSelect = vi.fn()
    render(<Timeline events={EVENTS} onSelect={onSelect} />)
    fireEvent.click(screen.getByRole('button', { name: /Торможение/ }))
    expect(onSelect).toHaveBeenCalledWith(EVENTS[2])
  })

  it('playheadOffset рисует и двигает курсор; вне диапазона — скрыт', () => {
    const { container, rerender } = render(<Timeline events={EVENTS} playheadOffset={0} />)
    const at0 = playhead(container)
    expect(at0).toBeInTheDocument()
    const left0 = (at0 as HTMLElement).style.left

    rerender(<Timeline events={EVENTS} playheadOffset={30} />)
    const at30 = playhead(container) as HTMLElement
    expect(at30).toBeInTheDocument()
    expect(at30.style.left).not.toBe(left0) // курсор сдвинулся

    rerender(<Timeline events={EVENTS} playheadOffset={9999} />)
    expect(playhead(container)).toBeNull() // вне [min,max] — курсора нет
  })

  it('пустой список — рендерит линию без падения', () => {
    const { container } = render(<Timeline events={[]} />)
    expect(container.querySelector('.rounded-full.bg-primary')).toBeInTheDocument()
    expect(screen.queryAllByRole('button')).toHaveLength(0)
  })
})
