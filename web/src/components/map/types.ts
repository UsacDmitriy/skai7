/**
 * Контракт props-данных map-примитивов (d4).
 * Severity переиспользуется из d2 (единый маппинг §4): critical|high|medium|low.
 */
import type { Severity } from '../ui/SeverityBadge'

/** Роль оператора (§7.6). Фильтрацию слоёв по роли делает f13, не примитивы. */
export type Role = 'logist' | 'dispatcher' | 'security'

/** Последний алярм ТС (вложен в MapUnit). */
export interface MapAlarm {
  id: string
  alarm_label_ru: string
  severity: Severity
  ts: string
}

/**
 * Единица карты — ровно одно ТС (§7.6: дедуп `1 unit_id = 1 marker`, НЕ `1 AlarmId`).
 * `lat`/`lon` могут прийти невалидными (null/NaN) — слой пропускает такие точки.
 */
export interface MapUnit {
  unit_id: string
  vehicle_plate: string
  lat: number
  lon: number
  severity: Severity
  online: boolean
  last_alarm?: MapAlarm | null
}
