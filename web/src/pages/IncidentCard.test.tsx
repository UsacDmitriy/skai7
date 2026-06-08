import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { INCIDENT_DETAILS, TICKETS } from '@/api/fixtures'

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
  return { ...actual, getIncident: vi.fn(), postAction: vi.fn(), getTickets: vi.fn() }
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

// Зонд пути для кросс-врезок: наблюдаем навигацию инцидент → рейс/заявки.
function LocationProbe() {
  const loc = useLocation()
  return <div data-testid="loc">{loc.pathname}</div>
}

function renderCardWithLocation(id: string) {
  return render(
    <MemoryRouter
      initialEntries={[`/incidents/${id}`]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/incidents/:id" element={<IncidentCard />} />
        <Route path="*" element={null} />
      </Routes>
      <LocationProbe />
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
    // Кросс-врезка «Связанные заявки» опрашивает getTickets в useEffect — по умолчанию пусто.
    vi.mocked(client.getTickets).mockResolvedValue([])
  })

  afterEach(() => {
    vi.mocked(client.getIncident).mockReset()
    vi.mocked(client.postAction).mockReset()
    vi.mocked(client.getTickets).mockReset()
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

  // ── w3-15 · кросс-врезки целостности (§9.4) ───────────────────────────────────
  describe('кросс-врезки (w3-12/§9.4)', () => {
    it('«Показать маршрут поездки» → /trip/<id> (trip_id == incident_id)', async () => {
      vi.mocked(client.getIncident).mockResolvedValue(INCIDENT_DETAILS['inc-001'])
      renderCardWithLocation('inc-001')

      const btn = await screen.findByRole('button', { name: /Показать маршрут поездки/ })
      fireEvent.click(btn)
      await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/trip/inc-001'))
    })

    it('блок «Связанные заявки» фильтрует фикстурные заявки по incident_id', async () => {
      vi.mocked(client.getIncident).mockResolvedValue(INCIDENT_DETAILS['inc-001'])
      vi.mocked(client.getTickets).mockResolvedValue(TICKETS)
      renderCard('inc-001')

      // inc-001 имеет 2 заявки (tkt-001 + tkt-006) — обе показаны.
      expect(await screen.findByText('Назначить разбор засыпания с водителем')).toBeInTheDocument()
      expect(screen.getByText('Передать в HR для дисциплинарной беседы')).toBeInTheDocument()
      // Заявка другого инцидента (inc-002) — отфильтрована.
      expect(screen.queryByText('Запросить архив по фронтальной камере')).not.toBeInTheDocument()
    })

    it('пустой список → дружелюбная плашка «Заявок по инциденту нет»', async () => {
      vi.mocked(client.getIncident).mockResolvedValue(INCIDENT_DETAILS['inc-001'])
      vi.mocked(client.getTickets).mockResolvedValue([])
      renderCard('inc-001')

      expect(await screen.findByText('Заявок по инциденту нет')).toBeInTheDocument()
    })

    it('после create_task появляется ссылка «Открыть в Заявках» → /tickets', async () => {
      vi.mocked(client.getIncident).mockResolvedValue(INCIDENT_DETAILS['inc-001'])
      vi.mocked(client.postAction).mockResolvedValue({
        incident_id: 'inc-001',
        action: 'create_task',
        comment: '',
        status: 'in_progress',
      })
      renderCard('inc-001')

      const createBtn = await screen.findByRole('button', { name: /Создать заявку/ })
      fireEvent.click(createBtn)

      const link = await screen.findByRole('link', { name: /Открыть в Заявках/ })
      expect(link).toHaveAttribute('href', '/tickets')
    })
  })
})
