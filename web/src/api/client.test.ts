import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type {
  DriverReport,
  FleetReport,
  IncidentDetail,
  IncidentSummary,
} from './types'

/**
 * f2 · API-клиент в режиме фикстур (`VITE_USE_FIXTURES=true`).
 * Проверяем, что методы отдают фикстуры f3 **без сети** (fetch не зовётся) и что
 * рантайм-форма ответов согласована с контрактом §3.1/§7.5.
 *
 * `USE_FIXTURES` фиксируется на уровне модуля при импорте — поэтому стабим env и
 * импортируем клиента динамически после `resetModules`, чтобы флаг точно сработал.
 */
async function loadClient() {
  vi.resetModules()
  vi.stubEnv('VITE_USE_FIXTURES', 'true')
  return import('./client')
}

async function loadVoice() {
  vi.resetModules()
  vi.stubEnv('VITE_USE_FIXTURES', 'true')
  return import('./voice')
}

let fetchSpy: ReturnType<typeof vi.fn>

beforeEach(() => {
  // Любой выход в сеть в режиме фикстур — провал теста.
  fetchSpy = vi.fn(() => Promise.reject(new Error('network call in fixtures mode')))
  vi.stubGlobal('fetch', fetchSpy)
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('client (fixtures) · incidents/vehicles/actions §3.2–§3.4', () => {
  it('listIncidents → ≥5 фикстур без сети, форма §3.1', async () => {
    const client = await loadClient()
    const rows = await client.listIncidents()
    expect(fetchSpy).not.toHaveBeenCalled()
    expect(rows.length).toBeGreaterThanOrEqual(5)

    const r: IncidentSummary = rows[0]
    expect(r).toMatchObject({
      id: expect.any(String),
      alarm_code: expect.any(String),
      alarm_label_ru: expect.any(String),
      source: expect.any(String),
      severity: expect.any(String),
      risk_score: expect.any(Number),
      vehicle_plate: expect.any(String),
    })
    expect(typeof r.video_available).toBe('boolean')
    expect(['critical', 'high', 'medium', 'low']).toContain(r.severity)
    expect(['active', 'in_progress', 'validated', 'closed']).toContain(r.status)
  })

  it('listIncidents применяет фильтры (severity) на фикстурах', async () => {
    const client = await loadClient()
    const critical = await client.listIncidents({ severity: 'critical' })
    expect(critical.length).toBeGreaterThan(0)
    expect(critical.every((r) => r.severity === 'critical')).toBe(true)
  })

  it('getIncident → IncidentDetail (форма §3.1), 404 на неизвестный id', async () => {
    const client = await loadClient()
    const inc: IncidentDetail = await client.getIncident('inc-001')
    expect(fetchSpy).not.toHaveBeenCalled()
    expect(inc.id).toBe('inc-001')
    expect(Array.isArray(inc.cameras)).toBe(true)
    expect(Array.isArray(inc.telemetry)).toBe(true)
    expect(Array.isArray(inc.cam_extra)).toBe(true)
    expect(inc.telemetry[0]).toMatchObject({
      ts_offset: expect.any(Number),
      speed: expect.any(Number),
      ax: expect.any(Number),
      ay: expect.any(Number),
    })

    await expect(client.getIncident('does-not-exist')).rejects.toMatchObject({
      status: 404,
    })
  })

  it('getTelemetry → точки телеметрии конкретного инцидента', async () => {
    const client = await loadClient()
    const tele = await client.getTelemetry('inc-001')
    expect(tele.length).toBeGreaterThan(0)
    expect(tele.every((p) => typeof p.ts_offset === 'number')).toBe(true)
  })

  it('videoUrl собирает эндпоинт канала (не сырой путь)', async () => {
    const client = await loadClient()
    expect(client.videoUrl('inc-001', 5)).toBe('/api/incidents/inc-001/video/5')
  })

  it('listVehicles → список ТС без сети', async () => {
    const client = await loadClient()
    const vehicles = await client.listVehicles()
    expect(fetchSpy).not.toHaveBeenCalled()
    expect(vehicles.length).toBeGreaterThan(0)
    expect(vehicles[0]).toMatchObject({ plate: expect.any(String), model: expect.any(String) })
  })

  it('postAction эхо-ответ со статусом, без сети', async () => {
    const client = await loadClient()
    const res = await client.postAction({
      incident_id: 'inc-001',
      action: 'mark_reviewed',
      comment: '',
    })
    expect(fetchSpy).not.toHaveBeenCalled()
    expect(res.status).toBeDefined()
    expect(['active', 'in_progress', 'validated', 'closed']).toContain(res.status)
  })
})

describe('client (fixtures) · reports/tickets/alerts/trips/sabotage §7.4–§7.5', () => {
  it('driverReport → DriverReport (kpi §7.5, violations)', async () => {
    const client = await loadClient()
    const report: DriverReport = await client.driverReport('А777ВВ 77')
    expect(fetchSpy).not.toHaveBeenCalled()
    expect(report.kpi).toMatchObject({
      total: expect.any(Number),
      video_da: expect.any(Number),
      telematics: expect.any(Number),
      gross: expect.any(Number),
    })
    expect(typeof report.disciplinary_warning).toBe('boolean')
    expect(Array.isArray(report.violations)).toBe(true)
    expect(report.violations[0]).toMatchObject({ id: expect.any(String), is_gross: expect.any(Boolean) })
  })

  it('fleetReport → FleetReport (by_drivers/by_vehicles)', async () => {
    const client = await loadClient()
    const report: FleetReport = await client.fleetReport()
    expect(report.vehicles_count).toBeGreaterThan(0)
    expect(Array.isArray(report.by_drivers)).toBe(true)
    expect(Array.isArray(report.by_vehicles)).toBe(true)
    expect(report.by_vehicles[0].cameras_ok).toMatch(/^\d+\/\d+$/)
  })

  it('getTickets → заявки с единым enum Status и is_overdue', async () => {
    const client = await loadClient()
    const tickets = await client.getTickets()
    expect(fetchSpy).not.toHaveBeenCalled()
    expect(tickets.length).toBeGreaterThan(0)
    for (const t of tickets) {
      expect(['active', 'in_progress', 'validated', 'closed']).toContain(t.status)
      expect(typeof t.is_overdue).toBe('boolean')
    }
  })

  it('getAlert → DispatchAlert (incident + окно), 404 на неизвестный id', async () => {
    const client = await loadClient()
    const alert = await client.getAlert('inc-001')
    expect(alert.incident.id).toBe('inc-001')
    expect(alert.video_window_sec).toBe(15)
    await expect(client.getAlert('nope')).rejects.toMatchObject({ status: 404 })
  })

  it('getTrip → TripDossier для trip-001, 404 иначе', async () => {
    const client = await loadClient()
    const trip = await client.getTrip('trip-001')
    expect(trip.vehicle_plate).toBeTruthy()
    expect(Array.isArray(trip.track)).toBe(true)
    expect(Array.isArray(trip.timeline)).toBe(true)
    await expect(client.getTrip('trip-999')).rejects.toMatchObject({ status: 404 })
  })

  it('getSabotage → события (dms_dark + speed>0)', async () => {
    const client = await loadClient()
    const events = await client.getSabotage()
    expect(fetchSpy).not.toHaveBeenCalled()
    expect(events.length).toBeGreaterThan(0)
    expect(events.every((e) => e.dms_dark === true && e.speed_kmh > 0)).toBe(true)
  })
})

describe('voice (fixtures) · transcribe/queryReport §7.4', () => {
  it('transcribe → детерминированная расшифровка без сети', async () => {
    const voice = await loadVoice()
    const t = await voice.transcribe(new Blob([]))
    expect(fetchSpy).not.toHaveBeenCalled()
    expect(t).toMatchObject({ text: expect.any(String), lang: 'ru', confidence: expect.any(Number) })
  })

  it('queryReport → {query, report}; driver-запрос даёт DriverReport', async () => {
    const voice = await loadVoice()
    const res = await voice.queryReport('дисциплина Иванова за неделю')
    expect(fetchSpy).not.toHaveBeenCalled()
    expect(res.query.kind).toBe('driver')
    expect('violations' in res.report).toBe(true)
  })

  it('queryReport → fleet-запрос даёт FleetReport (view по тексту)', async () => {
    const voice = await loadVoice()
    const res = await voice.queryReport('рейтинг по тс по парку')
    expect(res.query.kind).toBe('fleet')
    expect(res.query.view).toBe('vehicles')
    expect('by_vehicles' in res.report).toBe(true)
  })
})
