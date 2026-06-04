// f2 · API types — точная калька Pydantic-схем контракта.
// Источник истины: prompts/v2-fullstack/00-CONTRACT.md §3.1 (P0) + §7.5 (full-scope P1/P2).
// ЕДИНСТВЕННЫЙ владелец доменных типов фронта — этот файл. f3–f13 их только используют.

// ───────────────────────────────────────────────────────────── P0 · enums (§3.1)

export type Severity = 'critical' | 'high' | 'medium' | 'low'

// DIAGNOSTIC — алярмы сенсорной диагностики (камера офлайн и т.п.), бейдж «⚙ Диагностика» (contract-change #1).
export type Source = 'DMS' | 'ADAS' | 'TELEMATICS' | 'COMBINED' | 'DIAGNOSTIC'

export type Status = 'active' | 'in_progress' | 'validated' | 'closed'

export type CameraStatus = 'online' | 'offline' | 'warning'

/** Видеоканалы (§3.2): ch1 ADAS·Фронт · ch5 DMS·Салон · ch2 СНЗ·Доп · ch3 СНЗ·Кузов. */
export type VideoChannel = 1 | 2 | 3 | 5

// ───────────────────────────────────────────────────────── P0 · домен incidents (§3.1)

export interface Camera {
  id: string
  label: string
  status: CameraStatus
  hasVideo: boolean
  /** окно недоступности для no-video / offline / warning */
  offline_from: string | null
  offline_to: string | null
}

export interface TelemetryPoint {
  ts_offset: number
  speed: number
  /** ax = производная скорости (§2), не 0 */
  ax: number
  ay: number
}

export interface IncidentSummary {
  id: string
  alarm_type: string
  alarm_code: string
  alarm_label_ru: string
  source: Source
  severity: Severity
  risk_level: Severity
  risk_score: number
  ts: string
  vehicle_plate: string
  driver: string
  vehicle_model: string
  speed_kmh: number
  lat: number | null
  lon: number | null
  address: string | null
  video_available: boolean
  status: Status
}

/** Доп. видеоканалы (ch2/ch3) для блока «Другие камеры». */
export interface CamExtra {
  channel: number
  url: string
}

export interface IncidentDetail extends IncidentSummary {
  ts_end: string
  unit_id: string
  unit_name: string
  driver_id: string
  driver_phone: string
  // из driver_reference (§7.1)
  driver_region: string
  driver_department: string
  driver_safety_score: number
  speed_limit_kmh: number
  is_night: boolean
  continuous_driving_min: number
  events_last_7d: number
  // «версия события · уверенность %» (enrichment §2)
  confidence: number
  event_version: string | null
  // no-video: DMS-сенсор работал ещё N сек после offline
  sensor_active_after_sec: number | null
  mileage_km: number
  movement_duration: string
  video_count: number
  cam_front_url: string | null
  cam_dms_url: string | null
  cam_extra: CamExtra[]
  evidence_summary: string
  cameras: Camera[]
  telemetry: TelemetryPoint[]
}

// ───────────────────────────────────────────────────────── P0 · vehicles + actions

// VehicleSummary не пин-схема в §3.1 (§3.3: «список ТС из video_events__vehicles + обогащение
// driver/model»). Минимальный набор, согласованный с naming-конвенцией контракта.
export interface VehicleSummary {
  vehicle_plate: string
  unit_id: string
  unit_name: string
  vehicle_model: string
  driver: string
  alarms_count: number
  risk_score: number
}

/** Действия журнала (§3.4 POST /api/actions). */
export type ActionType =
  | 'mark_reviewed'
  | 'create_task'
  | 'export_report'
  | 'request_archive'
  | 'call_driver'
  | 'notify_hr'
  | 'validate'
  | 'stop_vehicle'

/** Тело запроса POST /api/actions. */
export interface ActionInput {
  incident_id: string
  action: ActionType
  comment?: string
}

/** Ответ POST /api/actions (echo + рантайм-статус инцидента). */
export interface Action {
  id: string
  created_at: string
  incident_id: string
  action: ActionType
  comment: string
  status: Status
}

// ───────────────────────────────────────────────── full-scope · reports/NLU (§7.5)

export type ReportKind = 'driver' | 'fleet'
export type ReportView = 'drivers' | 'vehicles'

export interface ReportQuery {
  kind: ReportKind
  plate?: string
  driver_name?: string
  period_days?: number // default 3
  view?: ReportView
}

/** всего / ВА видео-детекции / телематика / грубых */
export interface ReportKPI {
  total: number
  video_da: number
  telematics: number
  gross: number
}

export interface ReportPeriod {
  from: string
  to: string
  days: number
}

export interface ViolationRow {
  id: string
  ts: string
  alarm_code: string
  alarm_label_ru: string
  source: Source
  severity: Severity
  is_gross: boolean
}

export interface DriverRef {
  driver_id: string
  driver_name: string
  role: 'main' | 'secondary'
  trips: number
  safety_score: number
  risk_score: number
}

export interface DriverReport {
  driver: DriverRef
  vehicle_plate: string
  vehicle_model: string
  period: ReportPeriod
  mileage_km: number
  trips: number
  kpi: ReportKPI
  // порог: gross>=3 ИЛИ safety_score<60
  disciplinary_warning: boolean
  // клик по строке → IncidentDetail (killer-feature)
  violations: ViolationRow[]
}

/** Строка агрегата FleetReport.by_drivers. */
export interface FleetDriverRow {
  driver: DriverRef
  vehicle_plate: string
  vehicle_model: string
  mileage_km: number
  risk_score: number
  gross: number
  total: number
}

/** Строка агрегата FleetReport.by_vehicles. */
export interface FleetVehicleRow {
  plate: string
  vehicle_model: string
  main_driver: string
  mileage_km: number
  risk_score: number
  gross: number
  total: number
  cameras_ok: string // напр. "2/3"
}

export interface FleetReport {
  period: ReportPeriod
  kpi: ReportKPI
  vehicles_count: number
  by_drivers: FleetDriverRow[]
  by_vehicles: FleetVehicleRow[]
}

export interface VehicleReport {
  plate: string
  vehicle_model: string
  risk_score: number
  cameras: Camera[] // len = 3
  drivers: DriverRef[]
  period: ReportPeriod
  period_alarms: ViolationRow[]
  mileage_km: number
  trips: number
}

export interface Ticket {
  id: string
  created_at: string
  incident_id: string
  action: string
  comment: string
  // единый enum Status (§3.1): active=«Новая» · in_progress=«В работе» · validated=«Проверена» · closed=«Закрыта»
  status: Status
  deadline: string | null
  // is_overdue = deadline<now И status∉{closed}; «Просрочена» — оверлей, не статус
  is_overdue: boolean
}

export interface DispatchAlert {
  incident: IncidentDetail
  video_window_sec: number // =15
  requested_at: string
}

export interface TripTimelineItem {
  ts_offset: number
  alarm_code: string
  label: string
  has_video: boolean
}

export interface TripDossier {
  vehicle_plate: string
  track: TelemetryPoint[]
  timeline: TripTimelineItem[]
}

export interface RebGpsPoint {
  lat: number
  lon: number
  ts: string
}

export interface RebGapPeriod {
  start: string
  end: string
  duration_sec: number
}

export interface RebVideoFrame {
  ts: string
  channel: number
  url: string
}

export interface RebRecovery {
  vehicle_plate: string
  gps_track: RebGpsPoint[]
  gap_periods: RebGapPeriod[]
  video_frames: RebVideoFrame[]
}

export interface SabotageEvent {
  id: string
  vehicle_plate: string
  ts: string
  dms_dark: boolean
  speed_kmh: number
  driver_name: string
  video_url: string
}

// ───────────────────────────────────────────────── вспомогательные I/O-типы

/** Query-параметры GET /api/incidents (§3.2). */
export interface IncidentFilters {
  severity?: Severity
  source?: Source
  status?: Status
  vehicle_plate?: string
  limit?: number // =100
  offset?: number // =0
}

/** Ответ POST /api/reports/transcribe (§7.4). */
export interface TranscribeResult {
  text: string
  lang: string
  confidence: number
}

/** Ответ POST /api/reports/query (§7.4): NLU-разбор + отчёт. */
export interface QueryReportResult {
  query: ReportQuery
  report: DriverReport | FleetReport
}
