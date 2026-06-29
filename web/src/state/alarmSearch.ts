import type { IncidentSummary } from '@/api/types'

/**
 * Локальный умный поиск по активным алярмам (Monitor).
 * Чистая детерминированная функция: пустой запрос → список без изменений.
 * Спецсинтаксис: «критичные» → severity==='critical'; «риск>N» → risk_score>N.
 * Иначе — подстрочный матч по плашке/водителю/типу/источнику (регистронезависимо).
 */
export function alarmSearch(query: string, list: IncidentSummary[]): IncidentSummary[] {
  const q = query.trim().toLowerCase()
  if (!q) return list

  const riskGt = q.match(/риск\s*>\s*(\d{1,3})/)
  if (riskGt) {
    const n = Number(riskGt[1])
    return list.filter((a) => a.risk_score > n)
  }
  if (/критичн/.test(q)) return list.filter((a) => a.severity === 'critical')

  return list.filter(
    (a) =>
      a.vehicle_plate.toLowerCase().includes(q) ||
      a.driver.toLowerCase().includes(q) ||
      a.alarm_label_ru.toLowerCase().includes(q) ||
      a.source.toLowerCase().includes(q),
  )
}
