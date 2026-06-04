// f2 · Типизированный тонкий fetch-клиент к FastAPI (префикс /api через Vite proxy, его настроит x2).
// ЕДИНСТВЕННЫЙ владелец client-методов (P0 §3.2–§3.4 + full-scope §7.4). f7–f13 их только вызывают.
// Источник истины путей/схем: prompts/v2-fullstack/00-CONTRACT.md.

import type {
  Action,
  ActionInput,
  DispatchAlert,
  DriverReport,
  FleetReport,
  IncidentDetail,
  IncidentFilters,
  IncidentSummary,
  QueryReportResult,
  RebRecovery,
  ReportView,
  SabotageEvent,
  TelemetryPoint,
  Ticket,
  TranscribeResult,
  TripDossier,
  VehicleReport,
  VehicleSummary,
  VideoChannel,
} from './types'

export const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api'

/** Включает работу на статичных фикстурах f3 (без сети). */
export const USE_FIXTURES = import.meta.env.VITE_USE_FIXTURES === 'true'

// ─────────────────────────────────────────────────────────────── HTTP helper

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/** Тонкий fetch: бросает ApiError на !res.ok, парсит {detail}; отдаёт JSON как T. */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: unknown }
      if (body && typeof body.detail === 'string') detail = body.detail
    } catch {
      // тело не JSON — оставляем statusText
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

function qs(params: Record<string, string | number | undefined>): string {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') sp.set(k, String(v))
  }
  const s = sp.toString()
  return s ? `?${s}` : ''
}

// ─────────────────────────────────────────────────── fixtures seam (f3, опц.)
//
// f3 владеет web/src/api/fixtures.ts и идёт ПОСЛЕ f2 — поэтому импорт ленивый и
// типо-нейтральный (variable-path + @vite-ignore), чтобы typecheck проходил до
// появления fixtures.ts. Когда VITE_USE_FIXTURES=true и модуль есть — методы
// incidents/vehicles/reports берут данные оттуда без сети, иначе fallthrough на fetch.

/** Контракт фикстур f3 (подмножество клиента). Все методы опциональны. */
export interface Fixtures {
  listIncidents?(filters?: IncidentFilters): IncidentSummary[]
  getIncident?(id: string): IncidentDetail | undefined
  getTelemetry?(id: string): TelemetryPoint[]
  listVehicles?(): VehicleSummary[]
  driverReport?(plate: string): DriverReport
  fleetReport?(view?: ReportView): FleetReport
}

let _fx: Fixtures | null = null
let _fxLoaded = false

async function fixtures(): Promise<Fixtures | null> {
  if (!USE_FIXTURES) return null
  if (_fxLoaded) return _fx
  _fxLoaded = true
  try {
    const path = './fixtures'
    // variable-path import: TS/Vite не резолвят модуль статически (returns any).
    const mod = (await import(/* @vite-ignore */ path)) as Record<string, unknown>
    const pick = <F>(name: string) =>
      typeof mod[name] === 'function' ? (mod[name] as F) : undefined
    const constFn = <V>(name: string): (() => V) | undefined =>
      name in mod ? () => mod[name] as V : undefined
    // Маппинг на документированные экспорты f3 (§f3): helpers + константы.
    _fx = {
      listIncidents:
        pick<NonNullable<Fixtures['listIncidents']>>('listFixtureIncidents'),
      getIncident: pick<NonNullable<Fixtures['getIncident']>>('getFixtureIncident'),
      getTelemetry: pick<NonNullable<Fixtures['getTelemetry']>>('getFixtureTelemetry'),
      listVehicles: constFn<VehicleSummary[]>('VEHICLES'),
      driverReport: constFn<DriverReport>('DRIVER_REPORT'),
      fleetReport: constFn<FleetReport>('FLEET_REPORT'),
    }
  } catch {
    _fx = null // fixtures.ts ещё нет (до f3) — спокойный fallthrough на сеть
  }
  return _fx
}

// ───────────────────────────────────────────────────────── P0 · incidents (§3.2)

export async function listIncidents(filters: IncidentFilters = {}): Promise<IncidentSummary[]> {
  const fx = await fixtures()
  if (fx?.listIncidents) return fx.listIncidents(filters)
  return request<IncidentSummary[]>(`/incidents${qs({ ...filters })}`)
}

export async function getIncident(id: string): Promise<IncidentDetail> {
  const fx = await fixtures()
  if (fx?.getIncident) {
    const hit = fx.getIncident(id)
    if (hit) return hit
    throw new ApiError(404, `incident ${id} not found in fixtures`)
  }
  return request<IncidentDetail>(`/incidents/${encodeURIComponent(id)}`)
}

export async function getTelemetry(id: string): Promise<TelemetryPoint[]> {
  const fx = await fixtures()
  if (fx?.getTelemetry) return fx.getTelemetry(id)
  if (fx?.getIncident) return fx.getIncident(id)?.telemetry ?? []
  return request<TelemetryPoint[]>(`/incidents/${encodeURIComponent(id)}/telemetry`)
}

/** Прямой URL видеопотока канала (FileResponse mp4). channel ∈ {1,2,3,5}. */
export function videoUrl(id: string, channel: VideoChannel): string {
  return `${BASE}/incidents/${encodeURIComponent(id)}/video/${channel}`
}

// ───────────────────────────────────────────────────────── P0 · vehicles + actions

export async function listVehicles(): Promise<VehicleSummary[]> {
  const fx = await fixtures()
  if (fx?.listVehicles) return fx.listVehicles()
  return request<VehicleSummary[]>(`/vehicles`)
}

export async function postAction(action: ActionInput): Promise<Action> {
  return request<Action>(`/actions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(action),
  })
}

// ───────────────────────────────────────────── full-scope · voice / reports (§7.4)

/** Голос → текст (multipart/form-data wav). */
export async function transcribe(blob: Blob, lang?: string): Promise<TranscribeResult> {
  const form = new FormData()
  form.append('file', blob, 'audio.wav')
  if (lang) form.append('lang', lang)
  return request<TranscribeResult>(`/reports/transcribe`, { method: 'POST', body: form })
}

/** NL-запрос → {query: ReportQuery, report: DriverReport|FleetReport}. */
export async function queryReport(text: string): Promise<QueryReportResult> {
  return request<QueryReportResult>(`/reports/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
}

export async function driverReport(plate: string): Promise<DriverReport> {
  const fx = await fixtures()
  if (fx?.driverReport) return fx.driverReport(plate)
  return request<DriverReport>(`/reports/driver/${encodeURIComponent(plate)}`)
}

export async function fleetReport(view?: ReportView): Promise<FleetReport> {
  const fx = await fixtures()
  if (fx?.fleetReport) return fx.fleetReport(view)
  return request<FleetReport>(`/reports/fleet${qs({ view })}`)
}

export async function getVehicleReport(plate: string): Promise<VehicleReport> {
  return request<VehicleReport>(`/reports/vehicle/${encodeURIComponent(plate)}`)
}

// ───────────────────────────────────────── full-scope · tickets/alerts/trips/reb/sabotage

export async function getTickets(): Promise<Ticket[]> {
  return request<Ticket[]>(`/tickets`)
}

export async function getAlert(id: string): Promise<DispatchAlert> {
  return request<DispatchAlert>(`/alerts/${encodeURIComponent(id)}`)
}

export async function getTrip(id: string): Promise<TripDossier> {
  return request<TripDossier>(`/trips/${encodeURIComponent(id)}`)
}

export async function getReb(id: string): Promise<RebRecovery> {
  return request<RebRecovery>(`/reb/${encodeURIComponent(id)}`)
}

export async function getSabotage(): Promise<SabotageEvent[]> {
  return request<SabotageEvent[]>(`/sabotage`)
}

// ───────────────────────────────────────────────────────── namespace re-export

/** Единая точка доступа: `import { api } from '@/api/client'`. */
export const api = {
  listIncidents,
  getIncident,
  getTelemetry,
  videoUrl,
  listVehicles,
  postAction,
  transcribe,
  queryReport,
  driverReport,
  fleetReport,
  getVehicleReport,
  getTickets,
  getAlert,
  getTrip,
  getReb,
  getSabotage,
}
