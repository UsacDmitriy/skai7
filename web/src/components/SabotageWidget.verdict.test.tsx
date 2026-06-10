import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { SabotageEvent } from '@/api/types'

/**
 * f19 · SabotageWidget — умный вердикт саботажа (идея #16, §8, b23):
 *  • при наличии `verdict_confidence` карточка показывает «Вердикт саботажа»
 *    с процентом, шкалой (role=meter) и причиной `verdict_reason`;
 *  • уровень уверенности проговаривается словами (a11y, не только цвет);
 *  • backward-compat: события без полей вердикта → прежний вид (блока нет).
 *
 * Отдельный файл на вердикт — НЕ трогает SabotageWidget.test.tsx/.states.test.tsx.
 */
vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return { ...actual, getSabotage: vi.fn(), postAction: vi.fn() }
})

import * as client from '@/api/client'
import { SabotageWidget } from './SabotageWidget'

const event = (over: Partial<SabotageEvent> = {}): SabotageEvent => ({
  id: 'sab-1',
  vehicle_plate: 'А777ВВ 77',
  ts: '2026-04-02T00:36:00',
  dms_dark: true,
  speed_kmh: 62,
  driver_name: 'Иванов Алексей Петрович',
  video_url: '',
  ...over,
})

describe('f19 · SabotageWidget · вердикт', () => {
  beforeEach(() => {
    vi.mocked(client.postAction).mockResolvedValue({
      incident_id: 'x',
      action: 'create_task',
      comment: '',
      status: 'in_progress',
    })
  })
  afterEach(() => vi.clearAllMocks())

  it('высокая уверенность → процент, шкала-meter и причина', async () => {
    vi.mocked(client.getSabotage).mockResolvedValue([
      event({
        verdict_confidence: 0.86,
        verdict_reason: 'День, ясно снаружи — камера должна была видеть, тёмный кадр указывает на перекрытие',
      }),
    ])
    render(<SabotageWidget variant="full" />)

    expect(await screen.findByText('Вердикт саботажа')).toBeInTheDocument()
    expect(screen.getByText('86%')).toBeInTheDocument()
    // a11y: уровень словами + meter с aria-valuenow.
    expect(screen.getByText(/уверенность высокая/)).toBeInTheDocument()
    const meter = screen.getByRole('meter')
    expect(meter).toHaveAttribute('aria-valuenow', '86')
    expect(screen.getByText(/тёмный кадр указывает на перекрытие/)).toBeInTheDocument()
  })

  it('низкая уверенность → процент и пометка «низкая»', async () => {
    vi.mocked(client.getSabotage).mockResolvedValue([
      event({ verdict_confidence: 0.38, verdict_reason: 'Ночь, туман снаружи — тёмный кадр объясним' }),
    ])
    render(<SabotageWidget variant="full" />)

    expect(await screen.findByText('38%')).toBeInTheDocument()
    expect(screen.getByText(/уверенность низкая/)).toBeInTheDocument()
  })

  it('confidence клампится в [0..1] (грязные данные → 100%)', async () => {
    vi.mocked(client.getSabotage).mockResolvedValue([event({ verdict_confidence: 1.5 })])
    render(<SabotageWidget variant="full" />)

    expect(await screen.findByText('100%')).toBeInTheDocument()
    expect(screen.getByRole('meter')).toHaveAttribute('aria-valuenow', '100')
  })

  it('backward-compat: без полей вердикта блок не рендерится', async () => {
    vi.mocked(client.getSabotage).mockResolvedValue([event()])
    render(<SabotageWidget variant="full" />)

    // Карточка пришла (водитель виден), но блока вердикта нет.
    expect(await screen.findByText('Иванов Алексей Петрович')).toBeInTheDocument()
    expect(screen.queryByText('Вердикт саботажа')).not.toBeInTheDocument()
    expect(screen.queryByRole('meter')).not.toBeInTheDocument()
  })
})
