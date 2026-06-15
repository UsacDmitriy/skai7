import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { COACHING_CARDS, DRIVER_REPORT } from '@/api/fixtures'
import type { QueryResult } from '@/api/types'

/**
 * f27 · Секция «Обучение водителя» в driver-ветке Report (§12.4):
 *  • рендер на фикстуре: бейдж синтетики + 3 статуса (passed/failed/incomplete) + KPI;
 *  • пустые назначения → «обучение не назначалось» (секция видна — пустота информативна);
 *  • ошибка API → секция тихо скрыта, остальной отчёт работает.
 *
 * Дашборд строим через deep-link `?q=` (auto-путь без модалки); coaching мокаем точечно.
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
    getForecast: vi.fn(),
    getCoaching: vi.fn(),
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

function renderReport() {
  return render(
    <MemoryRouter
      initialEntries={['/report?q=дисциплина%20Иванова']}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Report />
    </MemoryRouter>,
  )
}

describe('Report · секция «Обучение водителя» (f27, §12.4)', () => {
  beforeEach(() => {
    vi.mocked(voice.queryReport).mockResolvedValue(DRIVER_QUERY)
    vi.mocked(client.getSabotage).mockResolvedValue([])
    // ForecastCard монтируется в driver-ветке — гасим сеть, чтобы не мешала.
    vi.mocked(client.getForecast).mockRejectedValue(new Error('no forecast in test'))
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('рендерит секцию: бейдж синтетики, 3 статуса, KPI-чипы', async () => {
    vi.mocked(client.getCoaching).mockResolvedValue(COACHING_CARDS['А777ВВ 77'])
    renderReport()

    expect(await screen.findByText('Обучение водителя')).toBeInTheDocument()
    // Обязательный бейдж синтетики (§12.0).
    expect(screen.getByText('синтетические данные (демо)')).toBeInTheDocument()

    // Три статуса текстом (a11y: статус не только цветом).
    expect(await screen.findByText('Сдан')).toBeInTheDocument()
    expect(screen.getByText('Провален')).toBeInTheDocument()
    expect(screen.getByText('Не завершён')).toBeInTheDocument()

    // KPI-чипы (§12.4).
    expect(screen.getByText('Завершение')).toBeInTheDocument()
    expect(screen.getByText('Сдача теста')).toBeInTheDocument()
    expect(screen.getByText('Повторные нарушения')).toBeInTheDocument()

    // Балл теста {test_score}/20 присутствует.
    expect(screen.getByText('19/20')).toBeInTheDocument()
  })

  it('пустые назначения → «обучение не назначалось», секция видна', async () => {
    vi.mocked(client.getCoaching).mockResolvedValue(COACHING_CARDS['Е902СТ 150'])
    renderReport()

    expect(await screen.findByText('Обучение не назначалось')).toBeInTheDocument()
    // Секция не скрыта: бейдж синтетики на месте.
    expect(screen.getByText('синтетические данные (демо)')).toBeInTheDocument()
  })

  it('ошибка API → секция обучения скрыта, отчёт работает', async () => {
    vi.mocked(client.getCoaching).mockRejectedValue(new Error('boom'))
    renderReport()

    // Остальной отчёт рендерится.
    expect(await screen.findByText(DRIVER_REPORT.driver.driver_name)).toBeInTheDocument()
    // Секция обучения отсутствует.
    expect(screen.queryByText('Обучение водителя')).not.toBeInTheDocument()
  })
})
