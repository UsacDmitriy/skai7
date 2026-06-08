import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import type { IncidentSummary } from '@/api/types'
import { RoleProvider } from '@/state/role'

/**
 * f5 · EventsFeed (`/`) — поведение ленты:
 *  • toggle «Нет видео» оставляет только `video_available=false`;
 *  • поиск по ТС/водителю (дебаунс) сужает строки;
 *  • ролевой switcher «Логист» убирает DMS-алармы (общий `filterByRole`);
 *  • клик по строке → переход на карточку инцидента.
 * Клиент мокаем (listIncidents); RoleToggle — настоящий (f13 интеграция роли).
 */
vi.mock('@/api/client', () => ({
  listIncidents: vi.fn(),
}))

import * as client from '@/api/client'
import EventsFeed from './EventsFeed'

const mk = (over: Partial<IncidentSummary>): IncidentSummary => ({
  id: 'inc-x',
  alarm_type: 'OVERSPEED',
  alarm_code: 'OVERSPEED',
  alarm_label_ru: 'Превышение',
  source: 'TELEMATICS',
  severity: 'high',
  risk_level: 'high',
  risk_score: 50,
  ts: '2026-04-02T10:00:00',
  vehicle_plate: 'А000АА 77',
  driver: 'Тест Водитель',
  vehicle_model: 'ГАЗон NEXT',
  speed_kmh: 80,
  lat: 55.75,
  lon: 37.61,
  address: 'ул. Тестовая, 1',
  video_available: true,
  status: 'active',
  ...over,
})

const INCIDENTS: IncidentSummary[] = [
  mk({ id: 'a', source: 'DMS', vehicle_plate: 'А777ВВ 77', driver: 'Иванов Алексей', alarm_label_ru: 'Засыпание', video_available: true }),
  mk({ id: 'b', source: 'TELEMATICS', vehicle_plate: 'В345КМ 97', driver: 'Петров Дмитрий', alarm_label_ru: 'Телефон', video_available: false }),
  mk({ id: 'c', source: 'ADAS', vehicle_plate: 'Е902СТ 150', driver: 'Сидоров Владимир', alarm_label_ru: 'Торможение', video_available: true }),
  mk({ id: 'd', source: 'COMBINED', vehicle_plate: 'Н124УУ 199', driver: 'Козлов Иван', alarm_label_ru: 'ДТП', video_available: false }),
]

function rowCount(): number {
  return document.querySelectorAll('tbody tr[role="button"]').length
}

function renderFeed() {
  return render(
    <RoleProvider>
      <MemoryRouter
        initialEntries={['/']}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/" element={<EventsFeed />} />
          <Route path="/incidents/:id" element={<div>Карточка инцидента</div>} />
        </Routes>
      </MemoryRouter>
    </RoleProvider>,
  )
}

describe('f5 · EventsFeed', () => {
  beforeEach(() => {
    localStorage.clear() // дефолтная роль — Диспетчер (полный список)
    vi.mocked(client.listIncidents).mockResolvedValue(INCIDENTS)
  })
  afterEach(() => {
    vi.mocked(client.listIncidents).mockReset()
  })

  it('toggle «Нет видео» оставляет только алармы без видео', async () => {
    renderFeed()
    await screen.findByRole('button', { name: 'Засыпание, А777ВВ 77' })
    expect(rowCount()).toBe(4)

    fireEvent.click(screen.getByRole('button', { name: 'Нет видео' }))
    await waitFor(() => expect(rowCount()).toBe(2)) // b + d
    expect(screen.getByRole('button', { name: 'Телефон, В345КМ 97' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Засыпание, А777ВВ 77' })).toBeNull()
  })

  it('поиск по водителю сужает ленту (дебаунс)', async () => {
    renderFeed()
    await screen.findByRole('button', { name: 'Засыпание, А777ВВ 77' })

    fireEvent.change(screen.getByLabelText('Поиск по госномеру или водителю'), {
      target: { value: 'Петров' },
    })
    await waitFor(() => expect(rowCount()).toBe(1))
    expect(screen.getByRole('button', { name: 'Телефон, В345КМ 97' })).toBeInTheDocument()
  })

  it('роль «Логист» скрывает DMS-алармы', async () => {
    renderFeed()
    await screen.findByRole('button', { name: 'Засыпание, А777ВВ 77' })
    expect(rowCount()).toBe(4)

    fireEvent.click(screen.getByRole('radio', { name: /Логист/ }))
    await waitFor(() => expect(rowCount()).toBe(3)) // DMS «Засыпание» ушла
    expect(screen.queryByRole('button', { name: 'Засыпание, А777ВВ 77' })).toBeNull()
  })

  it('клик по строке открывает карточку инцидента', async () => {
    renderFeed()
    const row = await screen.findByRole('button', { name: 'Засыпание, А777ВВ 77' })
    fireEvent.click(row)
    expect(await screen.findByText('Карточка инцидента')).toBeInTheDocument()
  })
})
