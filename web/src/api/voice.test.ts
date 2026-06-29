import { describe, expect, it, vi, beforeEach } from 'vitest'

vi.stubEnv('VITE_USE_FIXTURES', 'true')

import { queryReport } from './voice'

describe('mockNlu (demo)', () => {
  it('«рейтинг водителей» → fleet/drivers', async () => {
    const { query } = await queryReport('рейтинг водителей')
    expect(query.kind).toBe('fleet')
  })
  it('«нарушения по парку» → fleet', async () => {
    const { query } = await queryReport('грубые нарушения по парку')
    expect(query.kind).toBe('fleet')
  })
  it('«дисциплина Иванова за неделю» → driver, period 7', async () => {
    const { query } = await queryReport('дисциплина Иванова за неделю')
    expect(query.kind).toBe('driver')
    if (query.kind === 'driver') expect(query.period_days).toBe(7)
  })
  it('«за сутки» → period 1', async () => {
    const { query } = await queryReport('засыпания за сутки')
    expect(query.kind).toBe('driver')
    if (query.kind === 'driver') expect(query.period_days).toBe(1)
  })
  it('«за месяц» → period 30', async () => {
    const { query } = await queryReport('нарушения по парку за месяц')
    expect(query.kind).toBe('fleet')
    if (query.kind === 'fleet') expect(query.period_days).toBe(30)
  })
})
