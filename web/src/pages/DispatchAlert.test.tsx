import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { INCIDENT_DETAILS } from '@/api/fixtures'
import type { DispatchAlert as DispatchAlertData } from '@/api/types'

/**
 * f9 · DispatchAlert (`/alert/:id`) — overlay-модал критического алярма (идея #5):
 *  • видео-окно ±N с от момента (видео ADAS+DMS), телеметрия момента, 3 действия;
 *  • без видео → плейсхолдер «Видео недоступно» + «Запросить архив».
 */
vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return { ...actual, getAlert: vi.fn(), postAction: vi.fn() }
})

import * as client from '@/api/client'
import DispatchAlert from './DispatchAlert'

const alertOf = (id: string): DispatchAlertData => ({
  incident: INCIDENT_DETAILS[id],
  video_window_sec: 15,
  requested_at: INCIDENT_DETAILS[id].ts_end,
})

function renderAlert(id: string) {
  return render(
    <MemoryRouter
      initialEntries={[`/alert/${id}`]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/alert/:id" element={<DispatchAlert />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('f9 · DispatchAlert', () => {
  beforeEach(() => {
    vi.mocked(client.postAction).mockResolvedValue({
      incident_id: 'x',
      action: 'mark_reviewed',
      comment: '',
      status: 'in_progress',
    })
  })
  afterEach(() => vi.clearAllMocks())

  it('видео есть: окно ±15 с, два канала и три действия', async () => {
    vi.mocked(client.getAlert).mockResolvedValue(alertOf('inc-001'))
    renderAlert('inc-001')

    // Ждём загруженный контент (loading-оверлей тоже role=dialog).
    expect(await screen.findByText('Засыпание за рулём (микросон)')).toBeInTheDocument()
    const dialog = screen.getByRole('dialog')
    // Видео-окно ±15 с от момента
    expect(within(dialog).getByText('±15 с от момента')).toBeInTheDocument()
    // Два канала видео
    expect(within(dialog).getByText('ADAS · фронтальная')).toBeInTheDocument()
    expect(within(dialog).getByText('DMS · салон')).toBeInTheDocument()
    // Три быстрых действия
    expect(within(dialog).getByRole('button', { name: 'Создать заявку' })).toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: 'Всё в порядке' })).toBeInTheDocument()
  })

  it('видео нет: плейсхолдер «Видео недоступно» + «Запросить архив»', async () => {
    vi.mocked(client.getAlert).mockResolvedValue(alertOf('inc-003')) // video_available=false
    renderAlert('inc-003')

    expect(await screen.findByText('Видео недоступно')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Запросить архив/ })).toBeInTheDocument()
  })
})
