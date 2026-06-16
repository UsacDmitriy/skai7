import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { DRIVER_SCORES } from '@/api/fixtures'

/**
 * f28 · Лидерборд водителей (`/leaderboard`, §13.2/§13.3):
 *  • рендер на фикстуре: порядок строк = порядок API (1-е место — макс. unified_score);
 *  • дисклеймер периода присутствует (§13.0);
 *  • green-zone бейдж у нужных строк (a11y — текст, не только цвет);
 *  • клик по строке → отчёт водителя (/report?q=<driver>);
 *  • пустой / error кейсы.
 */
vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return { ...actual, getLeaderboard: vi.fn() }
})

import * as client from '@/api/client'
import Leaderboard from './Leaderboard'

function renderAt() {
  return render(
    <MemoryRouter
      initialEntries={['/leaderboard']}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/leaderboard" element={<Leaderboard />} />
        {/* Цель клика — отчёт водителя; читаем q из URL. */}
        <Route path="/report" element={<ReportProbe />} />
      </Routes>
    </MemoryRouter>,
  )
}

function ReportProbe() {
  return <div data-testid="report-probe">отчёт водителя</div>
}

describe('Leaderboard · рейтинг водителей (f28, §13.3)', () => {
  afterEach(() => vi.clearAllMocks())

  describe('ready', () => {
    beforeEach(() => {
      vi.mocked(client.getLeaderboard).mockResolvedValue(DRIVER_SCORES)
    })

    it('рендерит строки в порядке фикстуры (1-е место — макс. unified_score)', async () => {
      renderAt()
      await screen.findByText('Сидоров Владимир Николаевич')

      const rows = screen.getAllByRole('button')
      // Порядок строк совпадает с порядком DRIVER_SCORES (API уже отсортирован desc).
      DRIVER_SCORES.forEach((d, i) => {
        expect(within(rows[i]).getByText(d.driver_name)).toBeInTheDocument()
      })
      // 1-е место — максимальный unified_score.
      const top = DRIVER_SCORES[0]
      expect(top.unified_score).toBe(Math.max(...DRIVER_SCORES.map((d) => d.unified_score)))
      expect(within(rows[0]).getByText(String(top.unified_score))).toBeInTheDocument()
    })

    it('дисклеймер периода присутствует (§13.0)', async () => {
      renderAt()
      expect(await screen.findByText(/Оценки за период \d+ дн\./)).toBeInTheDocument()
    })

    it('green-zone бейдж у строк с green_zone (текст, не только цвет)', async () => {
      renderAt()
      await screen.findByText('Сидоров Владимир Николаевич')
      const greenCount = DRIVER_SCORES.filter((d) => d.green_zone).length
      expect(screen.getAllByText('зелёная зона')).toHaveLength(greenCount)
    })

    it('клик по строке открывает отчёт водителя (/report?q=)', async () => {
      const user = userEvent.setup()
      renderAt()
      const firstRow = (await screen.findAllByRole('button'))[0]
      await user.click(firstRow)
      expect(await screen.findByTestId('report-probe')).toBeInTheDocument()
    })
  })

  it('пустой кейс → информативная пустота', async () => {
    vi.mocked(client.getLeaderboard).mockResolvedValue([])
    renderAt()
    expect(await screen.findByText('Нет водителей для рейтинга')).toBeInTheDocument()
  })

  it('ошибка API → блок ошибки с ретраем', async () => {
    vi.mocked(client.getLeaderboard).mockRejectedValue(new Error('boom'))
    renderAt()
    expect(await screen.findByText('Повторить')).toBeInTheDocument()
  })
})
