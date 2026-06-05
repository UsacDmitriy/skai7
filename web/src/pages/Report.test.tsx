import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { DRIVER_REPORT, INCIDENT_DETAILS } from '@/api/fixtures'
import type { QueryResult } from '@/api/types'

/**
 * f7 · Report (`/report`):
 *  • дашборд В-1 (DriverReport) рендерит KPI и таблицу нарушений;
 *  • killer-feature (§6): клик по строке нарушения открывает видео-панель справа
 *    с правильным каналом (DMS→ch5).
 *
 * Данные мокаем на уровне voice/client (без сети). Дашборд строим через deep-link
 * `?q=` (auto-путь Report восстанавливает запрос без модалки подтверждения).
 */
vi.mock('@/api/voice', () => ({
  queryReport: vi.fn(),
  transcribe: vi.fn(),
}))

vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return {
    ...actual,
    getIncident: vi.fn(),
    getSabotage: vi.fn(),
    postAction: vi.fn(),
  }
})

import * as voice from '@/api/voice'
import * as client from '@/api/client'
import Report from './Report'

const DRIVER_QUERY: QueryResult = {
  query: {
    kind: 'driver',
    plate: DRIVER_REPORT.vehicle_plate,
    driver_name: DRIVER_REPORT.driver.driver_name,
    period_days: 7,
  },
  report: DRIVER_REPORT,
}

function renderReport(search = '?q=дисциплина%20Иванова') {
  return render(
    <MemoryRouter
      initialEntries={[`/report${search}`]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Report />
    </MemoryRouter>,
  )
}

describe('Report · дашборд В-1 (DriverReport)', () => {
  beforeEach(() => {
    vi.mocked(voice.queryReport).mockResolvedValue(DRIVER_QUERY)
    vi.mocked(client.getSabotage).mockResolvedValue([])
    vi.mocked(client.getIncident).mockResolvedValue(INCIDENT_DETAILS['inc-001'])
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('рендерит KPI и таблицу нарушений водителя', async () => {
    renderReport()

    // Водитель + дисциплинарный флаг (safety_score<60 / gross>=3).
    expect(await screen.findByText(DRIVER_REPORT.driver.driver_name)).toBeInTheDocument()
    expect(screen.getByText('Дисциплинарное взыскание')).toBeInTheDocument()

    // KPI (§7.5 ReportKPI): всего / ВА видео / телематика / грубых.
    expect(screen.getByText('Всего')).toBeInTheDocument()
    expect(screen.getByText(String(DRIVER_REPORT.kpi.total))).toBeInTheDocument()
    expect(screen.getByText('Грубых')).toBeInTheDocument()
    expect(screen.getByText(String(DRIVER_REPORT.kpi.gross))).toBeInTheDocument()

    // Таблица нарушений с реальными строками.
    expect(screen.getByText('Засыпание за рулём (микросон)')).toBeInTheDocument()
  })

  it('клик по нарушению открывает видео-панель с каналом DMS→ch5', async () => {
    renderReport()

    const row = await screen.findByText('Засыпание за рулём (микросон)')
    fireEvent.click(row)

    // Панель-диалог справа с правильным видео.
    const dialog = await screen.findByRole('dialog', { name: 'Видео нарушения' })
    expect(client.getIncident).toHaveBeenCalledWith('inc-001')
    await waitFor(() =>
      expect(within(dialog).getByText('Засыпание за рулём (микросон)')).toBeInTheDocument(),
    )
    // DMS-нарушение → канал 5 (анти-регресс DEF-3: src через videoUrl, не сырой путь).
    expect(within(dialog).getByText(/DMS · ch5/)).toBeInTheDocument()
  })
})
