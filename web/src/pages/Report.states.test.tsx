import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { DRIVER_REPORT } from '@/api/fixtures'
import type { DriverReport, QueryResult } from '@/api/types'

/**
 * f7 · Report — состояния запроса (loading/empty/error) и дружелюбные плашки.
 *  • loading → скелет дашборда (не белый экран);
 *  • empty → плашка «Нарушений за период не найдено» (пустой набор нарушений);
 *  • error → «Запрос не распознан…» + «Повторить» (ретрай повторно дёргает NLU);
 *  • idle (без запроса) → hero-подсказка вместо пустоты.
 */
vi.mock('@/api/voice', () => ({ queryReport: vi.fn(), transcribe: vi.fn() }))
vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return { ...actual, getIncident: vi.fn(), getSabotage: vi.fn(), postAction: vi.fn() }
})

import * as voice from '@/api/voice'
import * as client from '@/api/client'
import Report from './Report'

const EMPTY_DRIVER: DriverReport = { ...DRIVER_REPORT, violations: [] }
const queryFor = (report: DriverReport): QueryResult => ({
  query: { kind: 'driver', period_days: 7 },
  report,
})

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

describe('f7 · Report — состояния', () => {
  beforeEach(() => vi.mocked(client.getSabotage).mockResolvedValue([]))
  afterEach(() => vi.clearAllMocks())

  it('idle (без запроса): hero-подсказка вместо белого экрана', async () => {
    renderReport()
    expect(
      await screen.findByText(/Постройте отчёт голосом или текстом/),
    ).toBeInTheDocument()
  })

  it('loading: скелет дашборда во время запроса', () => {
    vi.mocked(voice.queryReport).mockReturnValue(new Promise(() => {}))
    const { container } = renderReport('?q=иванов')
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
    expect(screen.queryByText(/Постройте отчёт голосом/)).toBeNull()
  })

  it('empty: пустой набор нарушений → дружелюбная плашка', async () => {
    vi.mocked(voice.queryReport).mockResolvedValue(queryFor(EMPTY_DRIVER))
    renderReport('?q=иванов')
    expect(await screen.findByText('Нарушений за период не найдено')).toBeInTheDocument()
  })

  it('error: «Запрос не распознан…» + «Повторить» (ретрай дёргает NLU)', async () => {
    vi.mocked(voice.queryReport).mockRejectedValue(new Error('NLU offline'))
    renderReport('?q=иванов')
    expect(await screen.findByText(/Запрос не распознан/)).toBeInTheDocument()
    const retry = screen.getByRole('button', { name: /Повторить/ })

    vi.mocked(voice.queryReport).mockResolvedValue(queryFor(EMPTY_DRIVER))
    fireEvent.click(retry)
    await waitFor(() => expect(vi.mocked(voice.queryReport).mock.calls.length).toBeGreaterThan(1))
  })
})
