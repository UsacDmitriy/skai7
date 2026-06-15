/**
 * f2 · Тонкий fetch-клиент к FastAPI (`/api`).
 * Базовый URL — `VITE_API_BASE ?? '/api'` (Vite proxy настроит x2).
 * Флаг `VITE_USE_FIXTURES=true` подменяет ответы на статичные фикстуры f3 (без сети).
 *
 * Владелец файла — f2. f7–f13 только используют методы, НЕ дописывают новые.
 */
import {
  AI_METRICS,
  CONSISTENCY_REPORT,
  DATA_QUALITY,
  DRIVER_REPORT,
  FLEET_HEALTH,
  FLEET_REPORT,
  FUEL_VEHICLES,
  NAV_PROBLEMS,
  RISK_BREAKDOWN,
  SABOTAGE_EVENTS,
  SENSOR_VEHICLES,
  TICKETS,
  VEHICLES,
  VEHICLE_REPORT,
  ZONES,
  applyFixtureReviewDecision,
  getFixtureCopilot,
  getFixtureReviewQueue,
  getFixtureFatigue,
  getFixtureForecast,
  getFixtureFuel,
  getFixtureIncident,
  getFixtureNavProblem,
  getFixtureReb,
  getFixtureScene,
  getFixtureSensor,
  getFixtureSpeedCheck,
  getFixtureTrip,
  listFixtureIncidents,
} from './fixtures'
import type {
  Action,
  AiMetrics,
  ConsistencyReport,
  CopilotMessage,
  DataQuality,
  DriverReport,
  FatigueChain,
  FleetHealthResponse,
  FleetReport,
  FuelVehicleCard,
  FuelVehicleSummary,
  IncidentDetail,
  IncidentFilters,
  IncidentSummary,
  NavProblemVehicle,
  QueryResult,
  RebRecovery,
  ReviewItem,
  ReviewQueue,
  ReviewStatus,
  RiskBreakdown,
  RiskForecast,
  RiskZone,
  RiskZoneKind,
  SabotageEvent,
  SceneResponse,
  SensorVehicleCard,
  SensorVehicleSummary,
  SpeedCheck,
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
  // Fix (w3-10): раньше в фикстур-режиме уходил в сеть → демо-сирота.
  if (USE_FIXTURES) return Promise.resolve(VEHICLE_REPORT)
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
  // Fix (w3-10): раньше в фикстур-режиме уходил в сеть → демо-сирота.
  if (USE_FIXTURES) {
    const reb = getFixtureReb(id)
    return reb
      ? Promise.resolve(reb)
      : Promise.reject(new ApiError(404, `REB ${id} not found`))
  }
  return request<RebRecovery>(`/reb/${encodeURIComponent(id)}`)
}

export function getSabotage(): Promise<SabotageEvent[]> {
  if (USE_FIXTURES) return Promise.resolve(SABOTAGE_EVENTS)
  return request<SabotageEvent[]>('/sabotage')
}

// ── Волна 3 · тёмные данные fuel / sensors / navigation / fleet-health (§9.1) ──

export function listFuel(): Promise<FuelVehicleSummary[]> {
  if (USE_FIXTURES) return Promise.resolve(FUEL_VEHICLES)
  return request<FuelVehicleSummary[]>('/fuel')
}

export function getFuel(plate: string): Promise<FuelVehicleCard> {
  if (USE_FIXTURES) {
    const card = getFixtureFuel(plate)
    return card
      ? Promise.resolve(card)
      : Promise.reject(new ApiError(404, `Vehicle ${plate} not found`))
  }
  return request<FuelVehicleCard>(`/fuel/${encodeURIComponent(plate)}`)
}

export function listSensors(): Promise<SensorVehicleSummary[]> {
  if (USE_FIXTURES) return Promise.resolve(SENSOR_VEHICLES)
  return request<SensorVehicleSummary[]>('/sensors')
}

export function getSensors(plate: string): Promise<SensorVehicleCard> {
  if (USE_FIXTURES) {
    const card = getFixtureSensor(plate)
    return card
      ? Promise.resolve(card)
      : Promise.reject(new ApiError(404, `Vehicle ${plate} not found`))
  }
  return request<SensorVehicleCard>(`/sensors/${encodeURIComponent(plate)}`)
}

export function listNavProblems(): Promise<NavProblemVehicle[]> {
  if (USE_FIXTURES) return Promise.resolve(NAV_PROBLEMS)
  return request<NavProblemVehicle[]>('/navigation')
}

export function getNavProblem(plate: string): Promise<NavProblemVehicle> {
  if (USE_FIXTURES) {
    const row = getFixtureNavProblem(plate)
    return row
      ? Promise.resolve(row)
      : Promise.reject(new ApiError(404, `Vehicle ${plate} not found`))
  }
  return request<NavProblemVehicle>(`/navigation/${encodeURIComponent(plate)}`)
}

export function getFleetHealth(): Promise<FleetHealthResponse> {
  if (USE_FIXTURES) return Promise.resolve(FLEET_HEALTH)
  return request<FleetHealthResponse>('/fleet-health')
}

// ── Волна 4 · AI-слой (§8.3) — каркас под f15–f21 (только заглушки + фикстуры) ──

/** Сцена + погодная сверка инцидента (§8.3 `GET /api/incidents/{id}/scene`). */
export function getScene(id: string): Promise<SceneResponse> {
  if (USE_FIXTURES) return Promise.resolve(getFixtureScene(id))
  return request<SceneResponse>(`/incidents/${encodeURIComponent(id)}/scene`)
}

/** Прогноз риска по ТС (§8.3 `GET /api/reports/forecast/{plate}`). */
export function getForecast(plate: string): Promise<RiskForecast> {
  if (USE_FIXTURES) return Promise.resolve(getFixtureForecast(plate))
  return request<RiskForecast>(`/reports/forecast/${encodeURIComponent(plate)}`)
}

/** Риск-зоны (§8.3 `GET /api/zones?kind=&hour=`). */
export function getZones(params?: {
  kind?: RiskZoneKind
  hour?: number
}): Promise<RiskZone[]> {
  if (USE_FIXTURES) {
    const zones = params?.kind
      ? ZONES.filter((z) => z.kind === params.kind)
      : ZONES
    return Promise.resolve(zones)
  }
  return request<RiskZone[]>(`/zones${qs({ ...params })}`)
}

/** Цепочки усталости по ТС (§8.3 `GET /api/fatigue?plate=`). Пустой набор валиден. */
export function getFatigue(plate: string): Promise<FatigueChain[]> {
  if (USE_FIXTURES) return Promise.resolve(getFixtureFatigue(plate))
  return request<FatigueChain[]>(`/fatigue${qs({ plate })}`)
}

/** Копилот: текст → ответ ассистента (§8.3 `POST /api/copilot/chat`). */
export function copilotChat(text: string): Promise<CopilotMessage> {
  if (USE_FIXTURES) return Promise.resolve(getFixtureCopilot(text))
  return request<CopilotMessage>('/copilot/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
}

/** KPI AI-слоя (§8.7 `GET /api/metrics/ai`). */
export function getAiMetrics(): Promise<AiMetrics> {
  if (USE_FIXTURES) return Promise.resolve(AI_METRICS)
  return request<AiMetrics>('/metrics/ai')
}

/** Качество данных (§8.7 `GET /api/metrics/data-quality`). */
export function getDataQuality(): Promise<DataQuality> {
  if (USE_FIXTURES) return Promise.resolve(DATA_QUALITY)
  return request<DataQuality>('/metrics/data-quality')
}

/** Декомпозиция риска для waterfall (§8.8 `GET /api/incidents/{id}/risk-breakdown`). */
export function getRiskBreakdown(id: string): Promise<RiskBreakdown> {
  if (USE_FIXTURES) return Promise.resolve(RISK_BREAKDOWN)
  return request<RiskBreakdown>(
    `/incidents/${encodeURIComponent(id)}/risk-breakdown`,
  )
}

// ── Волна 4.4 · Data Trust (§10) — консистентность данных + сверка скоростей ────

/** Сводка консистентности датасетов (§10.1 `GET /api/consistency`). */
export function getConsistency(): Promise<ConsistencyReport> {
  if (USE_FIXTURES) return Promise.resolve(CONSISTENCY_REPORT)
  return request<ConsistencyReport>('/consistency')
}

/** Сверка скоростей события и GPS-трека (§10.1 `GET /api/incidents/{id}/speed-check`). */
export function getSpeedCheck(id: string): Promise<SpeedCheck> {
  if (USE_FIXTURES) {
    const sc = getFixtureSpeedCheck(id)
    return sc
      ? Promise.resolve(sc)
      : Promise.reject(new ApiError(404, `Speed-check ${id} not found`))
  }
  return request<SpeedCheck>(`/incidents/${encodeURIComponent(id)}/speed-check`)
}

// ── Волна 5.1 · Review-queue (§11) — очередь верификации инцидентов ─────────────

/** Очередь верификации, опц. фильтр по статусу (§11.1 `GET /api/review-queue`). */
export function getReviewQueue(status?: ReviewStatus): Promise<ReviewQueue> {
  if (USE_FIXTURES) return Promise.resolve(getFixtureReviewQueue(status))
  return request<ReviewQueue>(`/review-queue${qs({ status })}`)
}

/** Решение по инциденту (§11.1 `POST /api/review-queue/{id}`) → обновлённый `ReviewItem`. */
export function postReviewDecision(
  id: string,
  decision: 'validated' | 'dismissed',
  note?: string,
): Promise<ReviewItem> {
  if (USE_FIXTURES) {
    const item = applyFixtureReviewDecision(id, decision, note)
    return item
      ? Promise.resolve(item)
      : Promise.reject(new ApiError(404, `Incident ${id} not found`))
  }
  return request<ReviewItem>(`/review-queue/${encodeURIComponent(id)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, note }),
  })
}
