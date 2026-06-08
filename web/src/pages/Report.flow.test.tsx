import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { DRIVER_REPORT, FLEET_REPORT, INCIDENT_DETAILS } from '@/api/fixtures'
import type { DriverReport, QueryResult } from '@/api/types'

/**
 * f7 · Report (`/report`) — поток аналитики (идея #2) и роутинг видео-канала (§6/DEF-3):
 *  • текст → queryReport → ConfirmationModal → подтверждение → дашборд В-1;
 *  • дашборд В-2: toggle «По водителям ↔ По ТС»;
 *  • killer-feature: клик по ADAS-нарушению → видео-канал ADAS→ch1 (DMS→ch5 покрыт в Report.test).
 */
vi.mock('@/api/voice', () => ({ queryReport: vi.fn(), transcribe: vi.fn() }))
vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return { ...actual, getIncident: vi.fn(), getSabotage: vi.fn(), postAction: vi.fn() }
})

import * as voice from '@/api/voice'
import * as client from '@/api/client'
import Report from './Report'

const DRIVER_QUERY: QueryResult = {
  query: { kind: 'driver', plate: DRIVER_REPORT.vehicle_plate, driver_name: DRIVER_REPORT.driver.driver_name, period_days: 7 },
  report: DRIVER_REPORT,
}

const FLEET_QUERY: QueryResult = {
  query: { kind: 'fleet', view: 'drivers', period_days: 7 },
  report: FLEET_REPORT,
}

// Отчёт с единственным ADAS-нарушением → клик должен дать канал ADAS·ch1.
const ADAS_REPORT: DriverReport = {
  ...DRIVER_REPORT,
  violations: [
    { id: 'inc-004', ts: '2026-04-02T01:00:00', alarm_code: 'HARSH_BRAKING', alarm_label_ru: 'Резкое торможение ADAS', source: 'ADAS', severity: 'high', is_gross: true },
  ],
}
const ADAS_QUERY: QueryResult = { query: { kind: 'driver', period_days: 7 }, report: ADAS_REPORT }

function renderReport(search = '') {
  return render(
    <MemoryRouter
      initialEntries={[`/report${search}`]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Report />
    </MemoryRouter>,
  )
}

describe('f7 · Report — поток и каналы', () => {
  beforeEach(() => {
    vi.mocked(client.getSabotage).mockResolvedValue([])
  })
  afterEach(() => vi.clearAllMocks())

  it('текст → ConfirmationModal → подтверждение → дашборд водителя', async () => {
    vi.mocked(voice.queryReport).mockResolvedValue(DRIVER_QUERY)
    renderReport()

    fireEvent.change(screen.getByLabelText('Текст запроса'), {
      target: { value: 'дисциплина Иванова за неделю' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Построить/ }))

    // Модалка подтверждения NLU (d5)
    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText('Вот как я понял ваш запрос')).toBeInTheDocument()
    expect(within(dialog).getByText('Отчёт по водителю')).toBeInTheDocument()

    fireEvent.click(within(dialog).getByRole('button', { name: /Показать/ }))

    // Дашборд В-1
    expect(await screen.findByText(DRIVER_REPORT.driver.driver_name)).toBeInTheDocument()
    expect(screen.getByText('Дисциплинарное взыскание')).toBeInTheDocument()
  })

  it('дашборд парка В-2: переключение «По водителям ↔ По ТС»', async () => {
    vi.mocked(voice.queryReport).mockResolvedValue(FLEET_QUERY)
    renderReport('?q=по%20парку') // auto-путь строит дашборд без модалки

    expect(await screen.findByText('Рейтинг водителей')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /По ТС/ }))
    expect(await screen.findByText('Рейтинг ТС')).toBeInTheDocument()
    // колонка «Камеры» (cameras_ok) есть только в представлении по ТС
    expect(screen.getByRole('columnheader', { name: 'Камеры' })).toBeInTheDocument()
    expect(screen.getByText('1/2')).toBeInTheDocument() // уникальный cameras_ok
  })

  it('killer-feature: ADAS-нарушение → видео-канал ADAS·ch1', async () => {
    vi.mocked(voice.queryReport).mockResolvedValue(ADAS_QUERY)
    vi.mocked(client.getIncident).mockResolvedValue(INCIDENT_DETAILS['inc-004']) // cam_front_url есть
    renderReport('?q=иванов')

    const row = await screen.findByText('Резкое торможение ADAS')
    fireEvent.click(row)

    const panel = await screen.findByRole('dialog', { name: 'Видео нарушения' })
    expect(client.getIncident).toHaveBeenCalledWith('inc-004')
    await waitFor(() => expect(within(panel).getByText(/ADAS · ch1/)).toBeInTheDocument())
  })
})
