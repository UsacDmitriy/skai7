import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { getFixtureReviewQueue } from '@/api/fixtures'
import type { ReviewQueue as ReviewQueueData, ReviewStatus } from '@/api/types'

/**
 * f26 · ReviewQueue — рендер очереди на фикстуре, фильтр статуса, кнопки решений
 * у pending, состояния empty/error. Против §11.2/§11.3/§11.4.
 */
vi.mock('@/api/client', () => ({
  getReviewQueue: vi.fn(),
  postReviewDecision: vi.fn(),
}))

import * as client from '@/api/client'
import ReviewQueue from './ReviewQueue'

function renderQueue() {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ReviewQueue />
    </MemoryRouter>,
  )
}

/** Фикстура с фильтрацией по статусу (как живой клиент). */
function mockQueue() {
  vi.mocked(client.getReviewQueue).mockImplementation((status?: ReviewStatus) =>
    Promise.resolve(getFixtureReviewQueue(status)),
  )
}

describe('f26 · ReviewQueue', () => {
  beforeEach(() => mockQueue())
  afterEach(() => {
    vi.mocked(client.getReviewQueue).mockReset()
    vi.mocked(client.postReviewDecision).mockReset()
  })

  it('рендер: по умолчанию pending — счётчики и доказательность видны', async () => {
    renderQueue()
    expect(await screen.findByText('Очередь верификации')).toBeInTheDocument()
    // Доказательность из §10 (0.9 → 90%).
    expect(screen.getByText('90%')).toBeInTheDocument()
    // Дефолтный фильтр pending — загружен с status='pending'.
    expect(vi.mocked(client.getReviewQueue)).toHaveBeenCalledWith('pending')
  })

  it('кнопки «Подтвердить»/«Отклонить» есть у pending-строк', async () => {
    renderQueue()
    await screen.findByText('Очередь верификации')
    expect((await screen.findAllByRole('button', { name: /Подтвердить инцидент/ })).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('button', { name: /Отклонить инцидент/ }).length).toBeGreaterThan(0)
  })

  it('фильтр статуса: переключение на «Отклонённые» перезапрашивает очередь', async () => {
    renderQueue()
    await screen.findByText('Очередь верификации')
    fireEvent.click(screen.getByRole('tab', { name: /Отклонённые/ }))
    await waitFor(() =>
      expect(vi.mocked(client.getReviewQueue)).toHaveBeenCalledWith('dismissed'),
    )
  })

  it('решение: подтверждение дёргает клиент и обновляет список (refetch)', async () => {
    const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue('проверено')
    vi.mocked(client.postReviewDecision).mockResolvedValue({
      incident_id: 'inc-001',
      alarm_code: 'FATIGUE',
      severity: 'critical',
      vehicle_plate: 'А777ВВ 77',
      ts: '2026-04-02T08:12:00',
      video_available: true,
      status: 'validated',
      note: 'проверено',
      decided_at: '2026-06-15T12:00:00',
    })
    renderQueue()
    await screen.findByText('Очередь верификации')
    const before = vi.mocked(client.getReviewQueue).mock.calls.length
    fireEvent.click((await screen.findAllByRole('button', { name: /Подтвердить инцидент/ }))[0])
    await waitFor(() => expect(vi.mocked(client.postReviewDecision)).toHaveBeenCalled())
    // refetch после решения.
    await waitFor(() =>
      expect(vi.mocked(client.getReviewQueue).mock.calls.length).toBeGreaterThan(before),
    )
    promptSpy.mockRestore()
  })

  it('empty: «нет событий в этом статусе»', async () => {
    const empty: ReviewQueueData = {
      items: [],
      counts: { pending: 0, validated: 0, dismissed: 0 },
      evidence_rate: 0.9,
    }
    vi.mocked(client.getReviewQueue).mockResolvedValue(empty)
    renderQueue()
    expect(await screen.findByText('Нет событий в этом статусе')).toBeInTheDocument()
  })

  it('error: плашка + «Повторить» (ретрай повторно дёргает клиент)', async () => {
    vi.mocked(client.getReviewQueue).mockRejectedValue(new Error('очередь недоступна'))
    renderQueue()
    expect(await screen.findByText('очередь недоступна')).toBeInTheDocument()
    const retry = screen.getByRole('button', { name: /Повторить/ })
    mockQueue()
    fireEvent.click(retry)
    await waitFor(() =>
      expect(vi.mocked(client.getReviewQueue).mock.calls.length).toBeGreaterThan(1),
    )
  })
})
