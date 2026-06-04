/**
 * f2 · TypeScript-типы, пополю повторяющие Pydantic-схемы контракта.
 * Источник истины — `prompts/v2-fullstack/00-CONTRACT.md` §3.1 (домен incidents)
 * и §7.5 (full-scope P1/P2). Любое расхождение ломает экраны.
 *
 * Владелец файла — f2. f3 (fixtures) и f4–f13 только импортируют типы отсюда.
 */

// ── Перечисления (§3.1) ───────────────────────────────────────────────────────

/** Уровень риска / severity. НЕ путать с дизайн-токенами `warning`/`ok`. */
export type Severity = 'critical' | 'high' | 'medium' | 'low'

/** Источник алярма. `DIAGNOSTIC` — сенсорная диагностика (камера офлайн), бейдж «⚙ Диагностика» (contract-change #1). */
export type Source = 'DMS' | 'ADAS' | 'TELEMATICS' | 'COMBINED' | 'DIAGNOSTIC'

/** Жизненный цикл инцидента/заявки. Единый enum (contract-change #1). */
export type Status = 'active' | 'in_progress' | 'validated' | 'closed'

/** Состояние камеры. `warning` = «Нестабильна». */
export type CameraStatus = 'online' | 'offline' | 'warning'

// ── Базовые сущности (§3.1) ───────────────────────────────────────────────────

export interface Camera {
  id: string
  label: string
  status: CameraStatus
  hasVideo: boolean
  /** Окно недоступности для no-video (offline/warning). */
  offline_from: string | null
  offline_to: string | null
}

export interface TelemetryPoint {
  ts_offset: number
  speed: number
  /** Производная скорости (м/с²), §2 — не 0.0, иначе график-акселерометр плоский. */
  ax: number
  ay: number
}

/** Ответ ленты `GET /incidents`. */
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

/** Доп. канал (ch2/ch3) для блока «Другие камеры». */
export interface CamExtra {
  channel: number
  url: string
}

/** Ответ `GET /incidents/{id}` — расширяет IncidentSummary. */
export interface IncidentDetail extends IncidentSummary {
  ts_end: string
  unit_id: string
  unit_name: string
  driver_id: string
  driver_phone: string
  driver_region: string
  driver_department: string
  driver_safety_score: number
  speed_limit_kmh: number
  is_night: boolean
  continuous_driving_min: number
  events_last_7d: number
  /** «Уверенность версии события», 0–100 (enrichment §2). */
  confidence: number
  event_version: string | null
  /** No-video: DMS-сенсор работал ещё N сек после ухода камеры в offline. */
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

// ── Vehicles (§3.3) ───────────────────────────────────────────────────────────

/** Камера в карточке ТС (без оконных полей offline — облегчённая форма). */
export interface VehicleCamera {
  id: string
  label: string
  status: CameraStatus
}

/** Ответ `GET /vehicles` — список ТС из `video_events__vehicles` + обогащение. */
export interface VehicleSummary {
  id: string
  plate: string
  model: string
  driver: string
  division: string
  alarm_count: number
  /** Типы алярмов через `|` (как в датасете). */
  alarm_types: string
  downloaded_video_count: number
  total_track_mileage_km: number
  avg_speed_kmh: number
  cameras: VehicleCamera[]
  telematics_status: string
  archive_status: string
  connection_status: string
  engine_hours: number
  last_maintenance: string
}

// ── Actions (§3.4) ────────────────────────────────────────────────────────────

export type ActionType =
  | 'mark_reviewed'
  | 'create_task'
  | 'export_report'
  | 'request_archive'
  | 'call_driver'
  | 'notify_hr'
  | 'validate'
  | 'stop_vehicle'

/** Тело и ответ `POST /actions`. */
export interface Action {
  incident_id: string
  action: ActionType
  comment: string
  /** Новый статус инцидента в рантайме (возвращается сервисом). */
  status?: Status
  created_at?: string
}

// ── Reports / full-scope (§7.5) ───────────────────────────────────────────────

export interface ReportQuery {
  kind: 'driver' | 'fleet'
  plate?: string
  driver_name?: string
  period_days?: number
  view?: 'drivers' | 'vehicles'
}

/** всего / ВА видео-детекции / телематика / грубых. */
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

/** `GET /reports/driver/{plate}` (идея #2 В-1). */
export interface DriverReport {
  driver: DriverRef
  vehicle_plate: string
  vehicle_model: string
  period: ReportPeriod
  mileage_km: number
  trips: number
  kpi: ReportKPI
  /** Порог: gross>=3 ИЛИ safety_score<60. */
  disciplinary_warning: boolean
  violations: ViolationRow[]
}

export interface FleetByDriverRow {
  driver: DriverRef
  vehicle_plate: string
  vehicle_model: string
  mileage_km: number
  risk_score: number
  gross: number
  total: number
}

export interface FleetByVehicleRow {
  plate: string
  vehicle_model: string
  main_driver: string
  mileage_km: number
  risk_score: number
  gross: number
  total: number
  /** Напр. "2/3". */
  cameras_ok: string
}

/** `GET /reports/fleet` (идея #2 В-2). */
export interface FleetReport {
  period: ReportPeriod
  kpi: ReportKPI
  vehicles_count: number
  by_drivers: FleetByDriverRow[]
  by_vehicles: FleetByVehicleRow[]
}

/** `GET /reports/vehicle/{plate}` — len(cameras)=3. */
export interface VehicleReport {
  plate: string
  vehicle_model: string
  risk_score: number
  cameras: Camera[]
  drivers: DriverRef[]
  period: ReportPeriod
  period_alarms: ViolationRow[]
  mileage_km: number
  trips: number
}

/** `GET /tickets` (идея #6). «Просрочена» — не статус, а оверлей по is_overdue. */
export interface Ticket {
  id: string
  created_at: string
  incident_id: string
  action: string
  comment: string
  status: Status
  deadline: string | null
  is_overdue: boolean
}

/** `GET /alerts/{id}` (идея #5). */
export interface DispatchAlert {
  incident: IncidentDetail
  video_window_sec: number
  requested_at: string
}

export interface TripTimelineEntry {
  ts_offset: number
  alarm_code: string
  label: string
  has_video: boolean
}

/** `GET /trips/{id}` (идея #7). */
export interface TripDossier {
  vehicle_plate: string
  track: TelemetryPoint[]
  timeline: TripTimelineEntry[]
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

/** `GET /reb/{id}` (идея #8). */
export interface RebRecovery {
  vehicle_plate: string
  gps_track: RebGpsPoint[]
  gap_periods: RebGapPeriod[]
  video_frames: RebVideoFrame[]
}

/** Элемент `GET /sabotage` (идея #9). */
export interface SabotageEvent {
  id: string
  vehicle_plate: string
  ts: string
  dms_dark: boolean
  speed_kmh: number
  driver_name: string
  video_url: string
}

// ── Voice/NLU (§7.4) ──────────────────────────────────────────────────────────

/** Ответ `POST /reports/transcribe`. */
export interface Transcription {
  text: string
  lang: string
  confidence: number
}

/** Ответ `POST /reports/query` — обёртка `{query, report}`. */
export interface QueryResult {
  query: ReportQuery
  report: DriverReport | FleetReport
}

// ── Параметры запросов ────────────────────────────────────────────────────────

/** Фильтры `GET /incidents`. */
export interface IncidentFilters {
  severity?: Severity
  source?: Source
  status?: Status
  vehicle_plate?: string
  limit?: number
  offset?: number
}

/** Каналы видео для `GET /incidents/{id}/video/{channel}`. */
export type VideoChannel = 1 | 2 | 3 | 5
