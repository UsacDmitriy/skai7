/**
 * f7 · Тонкий voice-слой поверх f2-клиента (`client.ts`).
 * НЕ переписывает client.ts — только оборачивает `transcribe`/`queryReport`,
 * добавляя честную деградацию и детерминированный mock под `VITE_USE_FIXTURES=true`
 * (демо без сети/микрофона). Запись/получение Blob — в `VoiceButton` (d5, MediaRecorder).
 *
 * Контракт ответов — CONTRACT §7.4/§7.5:
 *   transcribe(blob, lang?) → { text, lang, confidence }
 *   queryReport(text)       → { query: ReportQuery, report: DriverReport | FleetReport }
 */
import * as client from './client'
import { DRIVER_REPORT, FLEET_REPORT } from './fixtures'
import type { QueryResult, ReportQuery, Transcription } from './types'

/** Демо без сети/микрофона: детерминированные mock-ответы. */
const USE_FIXTURES = import.meta.env.VITE_USE_FIXTURES === 'true'

/** Детерминированная «расшифровка» для демо без микрофона. */
const FIXTURE_TRANSCRIPT: Transcription = {
  text: 'дисциплина Иванова за неделю',
  lang: 'ru',
  confidence: 0.96,
}

/**
 * Голос → текст. `multipart/form-data` собирает клиент (f2).
 * Если браузер отдал webm/opus — шлём как есть с корректным MIME (перекодировка на бэке, b8).
 * На фикстурах — мгновенный детерминированный ответ (микрофон не нужен).
 */
export function transcribe(blob: Blob, lang?: string): Promise<Transcription> {
  if (USE_FIXTURES) return Promise.resolve({ ...FIXTURE_TRANSCRIPT, lang: lang ?? FIXTURE_TRANSCRIPT.lang })
  return client.transcribe(blob, lang)
}

/** Грубая офлайн-эвристика NLU: только для фикстур (реальный разбор — на бэке b8). */
function mockNlu(text: string): ReportQuery {
  const t = text.toLowerCase()
  const isFleet = /парк|флот|всем|по тс|по машин|по водител[яеи]м|рейтинг/.test(t)
  const period_days = /за сутки|за день|за ночь/.test(t) ? 1 : /за месяц/.test(t) ? 30 : 7
  if (isFleet) {
    const view = /тс|машин/.test(t) ? 'vehicles' : 'drivers'
    return { kind: 'fleet', view, period_days }
  }
  return {
    kind: 'driver',
    driver_name: DRIVER_REPORT.driver.driver_name,
    plate: DRIVER_REPORT.vehicle_plate,
    period_days,
  }
}

/**
 * NL-запрос → `{ query, report }` (CONTRACT §7.4).
 * На фикстурах — офлайн-разбор + готовый отчёт из f3 (детерминизм демо).
 */
export function queryReport(text: string): Promise<QueryResult> {
  if (USE_FIXTURES) {
    const query = mockNlu(text)
    const report = query.kind === 'fleet' ? FLEET_REPORT : DRIVER_REPORT
    return Promise.resolve({ query, report })
  }
  return client.queryReport(text)
}
