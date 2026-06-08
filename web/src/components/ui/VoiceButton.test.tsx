import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { VoiceButton } from './VoiceButton'

/**
 * d5 · VoiceButton — «🎤»-состояния (контракт §7.6): вид и a11y управляются `state`.
 *  • idle/recording/processing → разные aria-label, aria-pressed/aria-busy, sr-status;
 *  • processing — кнопка disabled;
 *  • клик в idle открывает микрофон (getUserMedia); отказ устройства не роняет UI;
 *  • клик в recording эмитит onStop.
 * MediaRecorder/getUserMedia мокаются — проверяем презентацию и обработчики, не реальный звук.
 */

class FakeMediaRecorder {
  static isTypeSupported(): boolean {
    return false
  }
  state: 'inactive' | 'recording' = 'inactive'
  mimeType = 'audio/webm'
  ondataavailable: ((e: { data: Blob }) => void) | null = null
  onstop: (() => void) | null = null
  constructor(public stream: unknown) {}
  start(): void {
    this.state = 'recording'
  }
  stop(): void {
    this.state = 'inactive'
    this.onstop?.()
  }
}

describe('VoiceButton · d5 🎤-состояния', () => {
  beforeEach(() => {
    vi.stubGlobal('MediaRecorder', FakeMediaRecorder as unknown as typeof MediaRecorder)
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('idle: микрофон, «Записать…», не нажата, статус «Готов к записи»', () => {
    render(<VoiceButton state="idle" onRecorded={vi.fn()} />)
    const btn = screen.getByRole('button', { name: 'Записать голосовой запрос' })
    expect(btn).toHaveAttribute('aria-pressed', 'false')
    expect(btn).not.toBeDisabled()
    expect(screen.getByText('Готов к записи')).toBeInTheDocument()
  })

  it('recording: «Остановить запись», нажата (aria-pressed)', () => {
    render(<VoiceButton state="recording" onRecorded={vi.fn()} />)
    const btn = screen.getByRole('button', { name: 'Остановить запись' })
    expect(btn).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByText('Идёт запись голоса')).toBeInTheDocument()
  })

  it('processing: кнопка заблокирована, aria-busy', () => {
    render(<VoiceButton state="processing" onRecorded={vi.fn()} />)
    const btn = screen.getByRole('button', { name: 'Распознавание запроса…' })
    expect(btn).toBeDisabled()
    expect(btn).toHaveAttribute('aria-busy', 'true')
    expect(screen.getByText('Идёт распознавание')).toBeInTheDocument()
  })

  it('клик в idle открывает микрофон и эмитит onStart', async () => {
    const getUserMedia = vi.fn().mockResolvedValue({ getTracks: () => [{ stop: vi.fn() }] })
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia } })
    const onStart = vi.fn()
    render(<VoiceButton state="idle" onRecorded={vi.fn()} onStart={onStart} />)
    fireEvent.click(screen.getByRole('button'))
    await waitFor(() => expect(getUserMedia).toHaveBeenCalled())
    await waitFor(() => expect(onStart).toHaveBeenCalled())
  })

  it('отказ микрофона не роняет UI и не зовёт onStart', async () => {
    const getUserMedia = vi.fn().mockRejectedValue(new Error('NotAllowedError'))
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia } })
    const onStart = vi.fn()
    render(<VoiceButton state="idle" onRecorded={vi.fn()} onStart={onStart} />)
    fireEvent.click(screen.getByRole('button'))
    await waitFor(() => expect(getUserMedia).toHaveBeenCalled())
    expect(onStart).not.toHaveBeenCalled()
  })

  it('клик в recording эмитит onStop', () => {
    const onStop = vi.fn()
    render(<VoiceButton state="recording" onRecorded={vi.fn()} onStop={onStop} />)
    fireEvent.click(screen.getByRole('button'))
    expect(onStop).toHaveBeenCalled()
  })
})
