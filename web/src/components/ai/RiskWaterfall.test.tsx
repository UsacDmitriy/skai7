import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RiskWaterfall, RiskWaterfallView } from './RiskWaterfall'
import type { RiskBreakdown } from '../../api/types'

/**
 * f20 · RiskWaterfall — explainability-разложение risk_score (§8.8).
 *  • View: сумма вкладов = total_risk_score (совпадает с API);
 *  • weather_bonus=0 (без кэша) → вклад 0, не ломается;
 *  • раскрывашка тянет данные лениво при первом открытии (f2-клиент).
 */

const BREAKDOWN: RiskBreakdown = {
  id: 'inc-001',
  severity_w: 45,
  speed_ratio: 13,
  night: 15,
  freq_w: 6,
  weather_bonus: 18,
  total_risk_score: 97,
}

vi.mock('../../api/client', () => ({
  getRiskBreakdown: vi.fn(() => Promise.resolve(BREAKDOWN)),
  ApiError: class ApiError extends Error {},
}))

import * as client from '../../api/client'

describe('RiskWaterfallView', () => {
  it('итог = total_risk_score и равен сумме вкладов', () => {
    render(<RiskWaterfallView data={BREAKDOWN} />)
    const sum = BREAKDOWN.severity_w + BREAKDOWN.speed_ratio + BREAKDOWN.night + BREAKDOWN.weather_bonus + BREAKDOWN.freq_w
    expect(sum).toBe(BREAKDOWN.total_risk_score)
    // Итоговая строка показывает risk_score.
    const totalRow = screen.getByText('Итоговый риск').closest('li')!
    expect(within(totalRow).getByText('97')).toBeInTheDocument()
  })

  it('показывает каждый вклад со знаком', () => {
    render(<RiskWaterfallView data={BREAKDOWN} />)
    expect(screen.getByText('Тяжесть')).toBeInTheDocument()
    expect(screen.getByText('+45')).toBeInTheDocument()
    expect(screen.getByText('+18')).toBeInTheDocument()
  })

  it('weather_bonus=0 (без кэша) → вклад 0, не ломается', () => {
    const noCache: RiskBreakdown = { ...BREAKDOWN, weather_bonus: 0, total_risk_score: 79 }
    render(<RiskWaterfallView data={noCache} />)
    const weatherRow = screen.getByText('Погода/сцена').closest('li')!
    expect(within(weatherRow).getByText('+0')).toBeInTheDocument()
    const totalRow = screen.getByText('Итоговый риск').closest('li')!
    expect(within(totalRow).getByText('79')).toBeInTheDocument()
  })
})

describe('RiskWaterfall (раскрывашка)', () => {
  it('тянет разложение лениво только при первом открытии', async () => {
    const user = userEvent.setup()
    render(<RiskWaterfall id="inc-001" />)
    // Свёрнуто — данные ещё не запрошены.
    expect(client.getRiskBreakdown).not.toHaveBeenCalled()
    expect(screen.queryByText('Итоговый риск')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Почему такой риск/i }))
    await waitFor(() => expect(client.getRiskBreakdown).toHaveBeenCalledWith('inc-001'))
    expect(await screen.findByText('Итоговый риск')).toBeInTheDocument()
  })
})
