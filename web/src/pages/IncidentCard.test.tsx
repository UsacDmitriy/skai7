import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { INCIDENT_DETAILS } from '@/api/fixtures'

/**
 * f4/f14 · IncidentCard:
 *  • `video_available=false` → placeholder + кнопка «Запросить архив»;
 *  • sync (idea #1): `onTimeUpdate` плеера двигает `playheadOffset` графика.
 *
 * VideoPlayer/TelemetryChart мокаем, чтобы наблюдать поток данных (onTimeUpdate →
 * playheadOffset), не завязываясь на recharts/`<video>`. Данные — фикстуры f3.
 */
vi.mock('@/components', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/components')>()
  return {
    ...actual,
    // Кнопка имитирует тик видео (отдаёт currentTime=20с) — только у плеера с onTimeUpdate (ADAS).
    VideoPlayer: ({ onTimeUpdate }: { onTimeUpdate?: (s: number) => void }) =>
      onTimeUpdate ? (
        <button data-testid="vp-timeupdate" onClick={() => onTimeUpdate(20)}>
          tick
        </button>
      ) : (
        <div data-testid="vp" />
      ),
    TelemetryChart: ({ playheadOffset }: { playheadOffset?: number }) => (
      <div data-testid="telemetry-chart" data-playhead={String(playheadOffset)} />
    ),
  }
})

vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return { ...actual, getIncident: vi.fn(), postAction: vi.fn() }
})

import * as client from '@/api/client'
import IncidentCard from './IncidentCard'

function renderCard(id: string) {
  return render(
    <MemoryRouter
      initialEntries={[`/incidents/${id}`]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/incidents/:id" element={<IncidentCard />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('IncidentCard', () => {
  beforeEach(() => {
    vi.mocked(client.postAction).mockResolvedValue({
      incident_id: 'x',
      action: 'request_archive',
      comment: '',
      status: 'in_progress',
    })
  })

  afterEach(() => {
    vi.mocked(client.getIncident).mockReset()
    vi.mocked(client.postAction).mockReset()
  })

  it('нет видео → placeholder «Видео недоступно» + «Запросить архив»', async () => {
    vi.mocked(client.getIncident).mockResolvedValue(INCIDENT_DETAILS['inc-003']) // video_available=false
    renderCard('inc-003')

    expect(await screen.findByText('Видео недоступно')).toBeInTheDocument()
    expect(screen.getAllByText('Запросить архив').length).toBeGreaterThanOrEqual(1)
  })

  it('sync: onTimeUpdate плеера двигает playheadOffset графика (idea #1)', async () => {
    vi.mocked(client.getIncident).mockResolvedValue(INCIDENT_DETAILS['inc-001']) // есть видео + телеметрия
    renderCard('inc-001')

    const chart = await screen.findByTestId('telemetry-chart')
    // Телеметрия inc-001: ts_offset ∈ [-60..30] → span.min = -60; старт currentSec=0.
    expect(chart).toHaveAttribute('data-playhead', '-60')

    // Тик видео: currentTime=20с → playheadOffset = span.min + 20 = -40.
    fireEvent.click(screen.getByTestId('vp-timeupdate'))
    await waitFor(() =>
      expect(screen.getByTestId('telemetry-chart')).toHaveAttribute('data-playhead', '-40'),
    )
  })

  it('404 → экран «Инцидент не найден» + «Назад к ленте»', async () => {
    const { ApiError } = await import('@/api/client')
    vi.mocked(client.getIncident).mockRejectedValue(new ApiError(404, 'not found'))
    renderCard('nope')

    expect(await screen.findByText('Инцидент не найден')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Назад к ленте/ })).toBeInTheDocument()
  })
})
