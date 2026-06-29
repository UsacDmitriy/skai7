import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

vi.mock('@/api/voice', async (orig) => ({
  ...(await orig()),
  queryReport: vi.fn().mockResolvedValue({
    query: { kind: 'driver', period_days: 7, driver_name: 'Тест', plate: 'А000АА 77' },
    report: {},
  }),
}))

import Report from './Report'
import * as voice from '@/api/voice'

describe('Report · SmartQueryInput', () => {
  it('клик по чипу-подсказке строит отчёт через queryReport', () => {
    render(<MemoryRouter><Report /></MemoryRouter>)
    fireEvent.click(screen.getByRole('button', { name: 'рейтинг водителей' }))
    expect(voice.queryReport).toHaveBeenCalledWith('рейтинг водителей')
  })
})
