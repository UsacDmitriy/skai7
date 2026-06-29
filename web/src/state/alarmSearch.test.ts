import { describe, expect, it } from 'vitest'
import { alarmSearch } from './alarmSearch'
import type { IncidentSummary } from '@/api/types'

const base: IncidentSummary = {
  id: '1', alarm_type: 'Smoking', alarm_code: 'DMS_SMOKING', alarm_label_ru: 'Курение',
  source: 'DMS', severity: 'medium', risk_level: 'medium', risk_score: 58,
  ts: '2026-05-19 02:59:00+04', vehicle_plate: 'С643УР799', driver: 'Волков Андрей',
  vehicle_model: 'Volvo FH', speed_kmh: 0, lat: null, lon: null, address: null,
  video_available: true, status: 'active',
}
const list: IncidentSummary[] = [
  base,
  { ...base, id: '2', alarm_label_ru: 'Засыпание за рулём', severity: 'critical', risk_score: 80, driver: 'Захаров Тимур', vehicle_plate: 'М078ОО154' },
  { ...base, id: '3', alarm_label_ru: 'Курение', driver: 'Козлов Иван', vehicle_plate: 'К776ВС977', risk_score: 54 },
]

describe('alarmSearch', () => {
  it('пустой запрос → исходный список', () => {
    expect(alarmSearch('', list)).toHaveLength(3)
    expect(alarmSearch('   ', list)).toHaveLength(3)
  })
  it('матч по госномеру (регистронезависимо)', () => {
    expect(alarmSearch('м078', list).map((a) => a.id)).toEqual(['2'])
  })
  it('матч по водителю', () => {
    expect(alarmSearch('козлов', list).map((a) => a.id)).toEqual(['3'])
  })
  it('матч по типу алярма', () => {
    expect(alarmSearch('засыпание', list).map((a) => a.id)).toEqual(['2'])
  })
  it('«критичные» → только critical', () => {
    expect(alarmSearch('критичные', list).map((a) => a.id)).toEqual(['2'])
  })
  it('«риск>70» → risk_score > 70', () => {
    expect(alarmSearch('риск>70', list).map((a) => a.id)).toEqual(['2'])
  })
})
