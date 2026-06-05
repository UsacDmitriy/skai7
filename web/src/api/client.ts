/**
 * f2 · Тонкий fetch-клиент к FastAPI (`/api`).
 * Базовый URL — `VITE_API_BASE ?? '/api'` (Vite proxy настроит x2).
 * Флаг `VITE_USE_FIXTURES=true` подменяет ответы на статичные фикстуры f3 (без сети).
 *
 * Владелец файла — f2. f7–f13 только используют методы, НЕ дописывают новые.
 */
import {
  DRIVER_REPORT,
  FLEET_REPORT,
  SABOTAGE_EVENTS,
  TICKETS,
  VEHICLES,
  getFixtureIncident,
  getFixtureTrip,
  listFixtureIncidents,
} from './fixtures'
import type {
  Action,
  DriverReport,
  FleetReport,
  IncidentDetail,
  IncidentFilters,
  IncidentSummary,
  QueryResult,
  RebRecovery,
  SabotageEvent,
  TelemetryPoint,
  Ticket,
  Transcription,
  TripDossier,
  VehicleReport,
  VehicleSummary,
  VideoChannel,
} from './types'

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api'

/** Подмена сети на фикстуры f3 (демо без бэкенда). */
const USE_FIXTURES = import.meta.env.VITE_USE_FIXTURES === 'true'

/** Ошибка API с HTTP-кодом и `detail` из тела. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/** Низкоуровневый запрос: бросает ApiError на `!res.ok`, парсит `{detail}`. */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: string }
      if (body?.detail) detail = body.detail
    } catch {
      /* тело не JSON — оставляем statusText */
    }
    throw new ApiError(res.status, detail)
  }
  return (await res.json()) as T
}

/** Сборка query-строки из фильтров (пропускает undefined). */
function qs(params: Record<string, string | number | undefined>): string {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== '') sp.set(k, String(v))
  }
  const s = sp.toString()
  return s ? `?${s}` : ''
}

// ── P0: incidents / vehicles / actions (§3.2–§3.4) ────────────────────────────

export function listIncidents(
  filters?: IncidentFilters,
): Promise<IncidentSummary[]> {
  if (USE_FIXTURES) return Promise.resolve(listFixtureIncidents(filters))
  return request<IncidentSummary[]>(`/incidents${qs({ ...filters })}`)
}

export function getIncident(id: string): Promise<IncidentDetail> {
  if (USE_FIXTURES) {
    const inc = getFixtureIncident(id)
    if (!inc) {
      return Promise.reject(new ApiError(404, `Incident ${id} not found`))
    }
    return Promise.resolve(inc)
  }
  return request<IncidentDetail>(`/incidents/${encodeURIComponent(id)}`)
}

export function getTelemetry(id: string): Promise<TelemetryPoint[]> {
  if (USE_FIXTURES) {
    const inc = getFixtureIncident(id)
    return inc
      ? Promise.resolve(inc.telemetry)
      : Promise.reject(new ApiError(404, `Incident ${id} not found`))
  }
  return request<TelemetryPoint[]>(`/incidents/${encodeURIComponent(id)}/telemetry`)
}

/** URL файла видео (для <video src>), не fetch. */
export function videoUrl(id: string, channel: VideoChannel): string {
  return `${BASE}/incidents/${encodeURIComponent(id)}/video/${channel}`
}

export function listVehicles(): Promise<VehicleSummary[]> {
  if (USE_FIXTURES) return Promise.resolve(VEHICLES)
  return request<VehicleSummary[]>('/vehicles')
}

export function postAction(action: Action): Promise<Action> {
  if (USE_FIXTURES) {
    // Демо-режим: эхо тела с дефолтным статусом.
    return Promise.resolve({ status: 'in_progress', ...action })
  }
  return request<Action>('/actions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(action),
  })
}

// ── §7.4 full-scope (reports / voice / stub-домены) ───────────────────────────

/** Голос → текст (multipart/form-data). */
export function transcribe(blob: Blob, lang?: string): Promise<Transcription> {
  const form = new FormData()
  form.append('file', blob, 'audio.wav')
  if (lang) form.append('lang', lang)
  return request<Transcription>('/reports/transcribe', {
    method: 'POST',
    body: form,
  })
}

/** NL-запрос → `{query, report}` (реальный NLU + отчёт). */
export function queryReport(text: string): Promise<QueryResult> {
  return request<QueryResult>('/reports/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
}

export function driverReport(plate: string): Promise<DriverReport> {
  if (USE_FIXTURES) return Promise.resolve(DRIVER_REPORT)
  return request<DriverReport>(`/reports/driver/${encodeURIComponent(plate)}`)
}

export function fleetReport(view?: 'drivers' | 'vehicles'): Promise<FleetReport> {
  if (USE_FIXTURES) return Promise.resolve(FLEET_REPORT)
  return request<FleetReport>(`/reports/fleet${qs({ view })}`)
}

export function getVehicleReport(plate: string): Promise<VehicleReport> {
  return request<VehicleReport>(`/reports/vehicle/${encodeURIComponent(plate)}`)
}

export function getTickets(): Promise<Ticket[]> {
  if (USE_FIXTURES) return Promise.resolve(TICKETS)
  return request<Ticket[]>('/tickets')
}

export function getAlert(id: string): Promise<import('./types').DispatchAlert> {
  if (USE_FIXTURES) {
    const inc = getFixtureIncident(id)
    if (!inc) {
      return Promise.reject(new ApiError(404, `Alert ${id} not found`))
    }
    // Демо-режим: окно ±15 с; момент запроса видео — конец алярма (без Date.now()).
    return Promise.resolve({
      incident: inc,
      video_window_sec: 15,
      requested_at: inc.ts_end,
    })
  }
  return request<import('./types').DispatchAlert>(
    `/alerts/${encodeURIComponent(id)}`,
  )
}

export function getTrip(id: string): Promise<TripDossier> {
  if (USE_FIXTURES) {
    const trip = getFixtureTrip(id)
    return trip
      ? Promise.resolve(trip)
      : Promise.reject(new ApiError(404, `Trip ${id} not found`))
  }
  return request<TripDossier>(`/trips/${encodeURIComponent(id)}`)
}

export function getReb(id: string): Promise<RebRecovery> {
  return request<RebRecovery>(`/reb/${encodeURIComponent(id)}`)
}

export function getSabotage(): Promise<SabotageEvent[]> {
  if (USE_FIXTURES) return Promise.resolve(SABOTAGE_EVENTS)
  return request<SabotageEvent[]>('/sabotage')
}
