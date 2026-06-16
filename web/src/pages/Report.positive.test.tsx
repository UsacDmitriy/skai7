import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { COACHING_CARDS, DRIVER_REPORT, POSITIVE_SCORES } from '@/api/fixtures'
import type { QueryResult } from '@/api/types'

/**
 * f28 · Блок «Позитивное вождение» в driver-ветке Report (§13.3):
 *  • рендер на фикстуре: positive_score крупно + дисклеймер периода + 3 составляющие;
 *  • блок ПОСЛЕ секции обучения f27 (порядок DOM);
 *  • green-zone бейдж для «чистого» кейса;
 *  • ошибка API → блок тихо скрыт, остальной отчёт работает.
 *
 * Дашборд строим через deep-link `?q=` (auto-путь без модалки); скоринг мокаем точечно.
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
    getPositiveScore: vi.fn(),
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

describe('Report · блок «Позитивное вождение» (f28, §13.3)', () => {
  beforeEach(() => {
    vi.mocked(voice.queryReport).mockResolvedValue(DRIVER_QUERY)
    vi.mocked(client.getSabotage).mockResolvedValue([])
    vi.mocked(client.getForecast).mockRejectedValue(new Error('no forecast in test'))
    // Секция обучения f27 присутствует — нужна для проверки порядка «после обучения».
    vi.mocked(client.getCoaching).mockResolvedValue(COACHING_CARDS['А777ВВ 77'])
  })

  afterEach(() => vi.clearAllMocks())

  it('рендерит positive_score, дисклеймер периода и 3 составляющие', async () => {
    vi.mocked(client.getPositiveScore).mockResolvedValue(POSITIVE_SCORES['А777ВВ 77'])
    renderReport()

    expect(await screen.findByText('Позитивное вождение')).toBeInTheDocument()
    // positive_score крупно.
    expect(screen.getByText(String(POSITIVE_SCORES['А777ВВ 77'].positive_score))).toBeInTheDocument()
    // Дисклеймер периода (§13.0).
    expect(screen.getByText(/за период \d+ дн\./)).toBeInTheDocument()
    // Три составляющие.
    expect(screen.getByText('Соблюдение лимитов')).toBeInTheDocument()
    expect(screen.getByText('Чистые дни')).toBeInTheDocument()
    expect(screen.getByText('Без резких манёвров')).toBeInTheDocument()
  })

  it('блок идёт ПОСЛЕ секции обучения f27 (порядок DOM)', async () => {
    vi.mocked(client.getPositiveScore).mockResolvedValue(POSITIVE_SCORES['А777ВВ 77'])
    renderReport()

    const coaching = await screen.findByText('Обучение водителя')
    const positive = await screen.findByText('Позитивное вождение')
    // compareDocumentPosition: FOLLOWING = 4.
    expect(coaching.compareDocumentPosition(positive) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('green-zone бейдж для «чистого» кейса (все ratio 1.0)', async () => {
    vi.mocked(client.getPositiveScore).mockResolvedValue(POSITIVE_SCORES['Е902СТ 150'])
    renderReport()

    expect(await screen.findByText('Позитивное вождение')).toBeInTheDocument()
    expect(screen.getByText('зелёная зона')).toBeInTheDocument()
  })

  it('ошибка API → блок позитива скрыт, отчёт работает', async () => {
    vi.mocked(client.getPositiveScore).mockRejectedValue(new Error('boom'))
    renderReport()

    // Остальной отчёт рендерится.
    expect(await screen.findByText(DRIVER_REPORT.driver.driver_name)).toBeInTheDocument()
    // Блок позитива отсутствует.
    expect(screen.queryByText('Позитивное вождение')).not.toBeInTheDocument()
  })
})
