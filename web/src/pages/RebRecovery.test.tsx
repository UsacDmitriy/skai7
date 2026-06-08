import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import type { RebRecovery as RebRecoveryData } from '@/api/types'

/**
 * f11 · RebRecovery (`/reb/:id`) — восстановление трека при РЭБ:
 *  • `gap_periods[]` визуализируются (счётчик, сегменты таймлайна, видеокадры момента);
 *  • выбор разрыва переключает блок видеокадров;
 *  • пустой список разрывов → «разрывов нет» (см. RebRecovery.states).
 * Карта мокается (Leaflet не монтируется); `getReb` фикстур не имеет — мокаем клиент.
 */
vi.mock('@/components/map', () => ({
  MapView: () => <div data-testid="map" />,
  MarkerLayer: () => null,
}))
vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return { ...actual, getReb: vi.fn() }
})

import * as client from '@/api/client'
import RebRecovery from './RebRecovery'

const REB: RebRecoveryData = {
  vehicle_plate: 'А777ВВ 77',
  gps_track: [
    { lat: 55.75, lon: 37.61, ts: '2026-04-02T03:10:00' },
    { lat: 55.76, lon: 37.62, ts: '2026-04-02T03:11:00' },
    { lat: 55.77, lon: 37.63, ts: '2026-04-02T03:20:00' },
    { lat: 55.78, lon: 37.64, ts: '2026-04-02T03:21:00' },
  ],
  gap_periods: [
    { start: '2026-04-02T03:11:30', end: '2026-04-02T03:14:30', duration_sec: 180 },
    { start: '2026-04-02T03:21:10', end: '2026-04-02T03:22:10', duration_sec: 60 },
  ],
  video_frames: [
    { ts: '2026-04-02T03:12:00', channel: 1, url: 'frame-ch1.mp4' },
    { ts: '2026-04-02T03:12:30', channel: 5, url: 'frame-ch5.mp4' },
  ],
}

function renderReb(id = 'reb-001') {
  return render(
    <MemoryRouter
      initialEntries={[`/reb/${id}`]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/reb/:id" element={<RebRecovery />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('f11 · RebRecovery', () => {
  beforeEach(() => vi.mocked(client.getReb).mockResolvedValue(REB))
  afterEach(() => vi.mocked(client.getReb).mockReset())

  it('gap_periods визуализируются: счётчик, сегменты таймлайна, суммарная длительность', async () => {
    renderReb()
    expect(
      await screen.findByText('РЭБ-восстановление трека · А777ВВ 77'),
    ).toBeInTheDocument()

    // Счётчик «Разрывов GPS» = длине gap_periods
    expect(screen.getByText(String(REB.gap_periods.length))).toBeInTheDocument()
    // Суммарно потеряно = 180+60 = 240 c = «4 мин 0 с»
    expect(screen.getByText('4 мин 0 с')).toBeInTheDocument()
    // Сегменты таймлайна — по кнопке на разрыв
    expect(screen.getAllByRole('button', { name: /Разрыв GPS/ })).toHaveLength(2)
  })

  it('авто-выбор первого разрыва показывает его видеокадры', async () => {
    renderReb()
    await screen.findByText(/РЭБ-восстановление трека/)
    // разрыв 1 из 2 + кадры обоих каналов внутри окна
    expect(screen.getByText(/разрыв 1 из 2/)).toBeInTheDocument()
    expect(screen.getByText('Канал 1')).toBeInTheDocument()
    expect(screen.getByText('Канал 5')).toBeInTheDocument()
  })

  it('выбор второго разрыва переключает блок видеокадров', async () => {
    renderReb()
    await screen.findByText(/РЭБ-восстановление трека/)

    const gaps = screen.getAllByRole('button', { name: /Разрыв GPS/ })
    fireEvent.click(gaps[1])
    expect(await screen.findByText(/разрыв 2 из 2/)).toBeInTheDocument()
  })
})
