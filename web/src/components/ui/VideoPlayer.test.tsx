import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { VideoPlayer } from './VideoPlayer'

/**
 * d2 · VideoPlayer:
 *  • пустой/undefined `src` → состояние «Видео недоступно» (без <video>);
 *  • `onTimeUpdate` зовётся на событие timeupdate видео (throttle через rAF);
 *  • контролируемый `seekTo` перематывает `video.currentTime`.
 *
 * rAF и currentTime в jsdom не «настоящие» — детерминируем их в тесте.
 */
describe('VideoPlayer', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('пустой src → пустое состояние «Видео недоступно», без <video>', () => {
    const { container } = render(<VideoPlayer />)
    expect(screen.getByText('Видео недоступно')).toBeInTheDocument()
    expect(container.querySelector('video')).toBeNull()
  })

  it('рендерит <video> при наличии src', () => {
    render(<VideoPlayer src="/api/incidents/inc-001/video/1" ariaLabel="Видео ADAS" />)
    const video = screen.getByLabelText('Видео ADAS') as HTMLVideoElement
    expect(video.tagName).toBe('VIDEO')
    expect(video).toHaveAttribute('src', '/api/incidents/inc-001/video/1')
  })

  it('зовёт onTimeUpdate на событие timeupdate видео', () => {
    // rAF синхронно с детерминированной меткой времени > THROTTLE_MS (80).
    vi.stubGlobal(
      'requestAnimationFrame',
      (cb: FrameRequestCallback) => {
        cb(1000)
        return 1
      },
    )
    vi.stubGlobal('cancelAnimationFrame', () => {})

    const onTimeUpdate = vi.fn()
    render(<VideoPlayer src="/v.mp4" onTimeUpdate={onTimeUpdate} ariaLabel="Видео" />)
    const video = screen.getByLabelText('Видео') as HTMLVideoElement

    fireEvent.timeUpdate(video)
    expect(onTimeUpdate).toHaveBeenCalledTimes(1)
  })

  it('seekTo перематывает currentTime видео', () => {
    const { rerender } = render(<VideoPlayer src="/v.mp4" ariaLabel="Видео" />)
    const video = screen.getByLabelText('Видео') as HTMLVideoElement

    // Контролируем currentTime (jsdom не двигает позицию сам).
    let position = 0
    const setter = vi.fn((v: number) => {
      position = v
    })
    Object.defineProperty(video, 'currentTime', {
      configurable: true,
      get: () => position,
      set: setter,
    })

    rerender(<VideoPlayer src="/v.mp4" ariaLabel="Видео" seekTo={12} />)
    expect(setter).toHaveBeenCalledWith(12)
    expect(position).toBe(12)
  })

  it('рисует маркер события (eventMarkerPct) поверх видео', () => {
    const { container } = render(<VideoPlayer src="/v.mp4" eventMarkerPct={50} />)
    const marker = container.querySelector('.bg-warning') as HTMLElement
    expect(marker).toBeInTheDocument()
    expect(marker.style.left).toBe('50%')
  })
})
