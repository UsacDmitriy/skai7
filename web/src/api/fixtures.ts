/**
 * f3 · Статичные фикстуры, повторяющие контракт ответов (§3.1 + §7.5).
 * Источник эталонной формы — `data/mock/incidents.py` / `data/mock/vehicles.py`,
 * перенесённые в TS с канон-маппингом имён (§3.1):
 *   score → risk_score · event_source → source · alarm_type_label → alarm_label_ru.
 *
 * Назначение: экраны f4+ разрабатываются и демонстрируются без запущенного FastAPI
 * (через флаг `VITE_USE_FIXTURES=true`, см. client.ts).
 *
 * Формы СТРОГО соответствуют типам f2 (= §3.1). Любое расхождение ломает экраны.
 */
import type {
  DriverReport,
  FleetHealthResponse,
  FleetReport,
  FuelVehicleCard,
  FuelVehicleSummary,
  IncidentDetail,
  IncidentFilters,
  IncidentSummary,
  NavProblemVehicle,
  RebRecovery,
  SabotageEvent,
  SensorVehicleCard,
  SensorVehicleSummary,
  Ticket,
  TripDossier,
  VehicleReport,
  VehicleSummary,
} from './types'

// ── Детали инцидентов (полная форма IncidentDetail) ───────────────────────────
// Из них же выводится лента INCIDENTS (summary) — единый источник, без рассинхрона.

const DETAILS: IncidentDetail[] = [
  {
    // inc-001 · засыпание, есть видео (2 канала), CAM-03 offline
    id: 'inc-001',
    alarm_type: 'DMS_DROWSY',
    alarm_code: 'DMS_DROWSY',
    alarm_label_ru: 'Засыпание за рулём (микросон)',
    source: 'DMS',
    severity: 'critical',
    risk_level: 'critical',
    risk_score: 97,
    ts: '2026-04-02T00:36:43',
    ts_end: '2026-04-02T00:37:01',
    vehicle_plate: 'А777ВВ 77',
    unit_id: 'UNIT-001',
    unit_name: 'ГАЗон NEXT · А777ВВ 77',
    driver: 'Иванов Алексей Петрович',
    driver_id: 'DRV-2841',
    driver_phone: '+79261234187',
    driver_region: 'Москва',
    driver_department: 'Логистика · Север-1',
    driver_safety_score: 41,
    vehicle_model: 'ГАЗон NEXT',
    speed_kmh: 72,
    speed_limit_kmh: 90,
    lat: 55.7512,
    lon: 37.6184,
    address: 'ул. Тверская, 12',
    is_night: true,
    continuous_driving_min: 178,
    events_last_7d: 3,
    confidence: 92,
    event_version: 'Микросон: голова опустилась ниже уровня руля >4 с.',
    sensor_active_after_sec: null,
    mileage_km: 4520.5,
    movement_duration: '02:58:00',
    video_count: 2,
    video_available: true,
    cam_front_url: 'datasets/media/video_events/cam1_front.mp4',
    cam_dms_url: 'datasets/media/video_events/cam2_dms.mp4',
    cam_extra: [],
    status: 'active',
    evidence_summary:
      'Обнаружено засыпание за рулём (микросон). Голова водителя опустилась ниже уровня руля на 4+ секунды.',
    cameras: [
      { id: 'CAM-01', label: 'ADAS · Передняя', status: 'online', hasVideo: true, offline_from: null, offline_to: null },
      { id: 'CAM-02', label: 'DMS · Салон', status: 'online', hasVideo: true, offline_from: null, offline_to: null },
      { id: 'CAM-03', label: 'CH3 · Правая', status: 'offline', hasVideo: false, offline_from: '2026-04-01T19:10:00', offline_to: null },
    ],
    telemetry: [
      { ts_offset: -60, speed: 75, ax: 0.1, ay: -0.2 },
      { ts_offset: -30, speed: 72, ax: 0.0, ay: 0.1 },
      { ts_offset: 0, speed: 72, ax: -0.3, ay: 0.5 },
      { ts_offset: 15, speed: 70, ax: -0.1, ay: 0.0 },
      { ts_offset: 30, speed: 73, ax: 0.2, ay: -0.1 },
    ],
  },
  {
    // inc-002 · датчик удара (54→0), есть видео, COMBINED
    id: 'inc-002',
    alarm_type: 'CRASH_SENSOR',
    alarm_code: 'CRASH_SENSOR',
    alarm_label_ru: 'Подозрение на ДТП — датчик удара',
    source: 'COMBINED',
    severity: 'critical',
    risk_level: 'critical',
    risk_score: 84,
    ts: '2026-04-02T03:12:00',
    ts_end: '2026-04-02T03:12:30',
    vehicle_plate: 'В345КМ 97',
    unit_id: 'UNIT-002',
    unit_name: 'КамАЗ-5490 · В345КМ 97',
    driver: 'Петров Дмитрий Сергеевич',
    driver_id: 'DRV-3912',
    driver_phone: '+79262345091',
    driver_region: 'Московская обл.',
    driver_department: 'Логистика · Центр',
    driver_safety_score: 58,
    vehicle_model: 'КамАЗ-5490',
    speed_kmh: 54,
    speed_limit_kmh: 60,
    lat: 55.7558,
    lon: 37.6173,
    address: 'M-7 «Волга», 124 км',
    is_night: true,
    continuous_driving_min: 94,
    events_last_7d: 1,
    confidence: 88,
    event_version: 'Резкое снижение скорости 54→0 за 4 с, пик акселерометра 4.2 м/с².',
    sensor_active_after_sec: null,
    mileage_km: 8750.2,
    movement_duration: '01:34:00',
    video_count: 2,
    video_available: true,
    cam_front_url: 'datasets/media/video_events/cam1_crash.mp4',
    cam_dms_url: 'datasets/media/video_events/cam2_crash.mp4',
    cam_extra: [],
    status: 'in_progress',
    evidence_summary:
      'Зафиксировано резкое снижение скорости с 54 км/ч до 0 за 4 секунды. Акселерометр: пик 4.2 м/с².',
    cameras: [
      { id: 'CAM-01', label: 'ADAS · Передняя', status: 'online', hasVideo: true, offline_from: null, offline_to: null },
      { id: 'CAM-02', label: 'DMS · Салон', status: 'online', hasVideo: true, offline_from: null, offline_to: null },
      { id: 'CAM-03', label: 'CH3 · Задняя', status: 'offline', hasVideo: false, offline_from: '2026-04-02T01:00:00', offline_to: null },
    ],
    telemetry: [
      { ts_offset: -60, speed: 55, ax: 0.0, ay: 0.1 },
      { ts_offset: -30, speed: 54, ax: 0.1, ay: -0.1 },
      { ts_offset: -15, speed: 54, ax: 0.0, ay: 0.0 },
      { ts_offset: 0, speed: 0, ax: 4.2, ay: -2.1 },
      { ts_offset: 15, speed: 0, ax: 0.0, ay: 0.0 },
      { ts_offset: 30, speed: 0, ax: 0.0, ay: 0.0 },
    ],
  },
  {
    // inc-003 · телефон, НЕТ видео (placeholder + sensor_active_after_sec)
    id: 'inc-003',
    alarm_type: 'DMS_PHONE',
    alarm_code: 'DMS_PHONE',
    alarm_label_ru: 'Использование телефона во время движения',
    source: 'TELEMATICS',
    severity: 'high',
    risk_level: 'high',
    risk_score: 76,
    ts: '2026-05-15T10:15:00',
    ts_end: '2026-05-15T10:15:20',
    vehicle_plate: 'Е902СТ 150',
    unit_id: 'UNIT-003',
    unit_name: 'ГАЗель NEXT · Е902СТ 150',
    driver: 'Сидоров Владимир Николаевич',
    driver_id: 'DRV-4501',
    driver_phone: '+79263456012',
    driver_region: 'Москва',
    driver_department: 'Доставка · Юг',
    driver_safety_score: 49,
    vehicle_model: 'ГАЗель NEXT',
    speed_kmh: 88,
    speed_limit_kmh: 60,
    lat: 55.73,
    lon: 37.59,
    address: 'пр-т Мира, 45',
    is_night: false,
    continuous_driving_min: 45,
    events_last_7d: 5,
    confidence: 66, // no-video: −10 к базовой уверенности (§2)
    event_version: 'DMS зафиксировал использование телефона; видео не передано в архив.',
    sensor_active_after_sec: 7,
    mileage_km: 3200.8,
    movement_duration: '00:45:00',
    video_count: 0,
    video_available: false,
    cam_front_url: null,
    cam_dms_url: null,
    cam_extra: [],
    status: 'in_progress',
    evidence_summary:
      'Зафиксировано по данным DMS-камеры. Видео недоступно — камера не передала данные в архив.',
    cameras: [
      { id: 'CAM-01', label: 'ADAS · Передняя', status: 'online', hasVideo: true, offline_from: null, offline_to: null },
      { id: 'CAM-02', label: 'DMS · Салон', status: 'online', hasVideo: true, offline_from: null, offline_to: null },
      { id: 'CAM-03', label: 'CH3 · Задняя', status: 'offline', hasVideo: false, offline_from: '2026-05-15T10:14:53', offline_to: null },
    ],
    telemetry: [
      { ts_offset: -60, speed: 86, ax: 0.1, ay: 0.2 },
      { ts_offset: -30, speed: 88, ax: 0.0, ay: 0.0 },
      { ts_offset: 0, speed: 88, ax: 0.0, ay: 0.0 },
      { ts_offset: 15, speed: 87, ax: -0.1, ay: 0.1 },
      { ts_offset: 30, speed: 89, ax: 0.2, ay: -0.1 },
    ],
  },
  {
    // inc-004 · резкое торможение, частичное видео (cam_front есть, cam_dms нет), CAM-02 warning
    id: 'inc-004',
    alarm_type: 'HARSH_BRAKING',
    alarm_code: 'HARSH_BRAKING',
    alarm_label_ru: 'Резкое торможение / экстренное ускорение',
    source: 'TELEMATICS',
    severity: 'high',
    risk_level: 'high',
    risk_score: 68,
    ts: '2026-04-02T01:00:00',
    ts_end: '2026-04-02T01:00:18',
    vehicle_plate: 'Н124УУ 199',
    unit_id: 'UNIT-004',
    unit_name: 'МАЗ-5440 · Н124УУ 199',
    driver: 'Козлов Иван Андреевич',
    driver_id: 'DRV-5023',
    driver_phone: '+79264560238',
    driver_region: 'Московская обл.',
    driver_department: 'Логистика · Восток',
    driver_safety_score: 52,
    vehicle_model: 'МАЗ-5440',
    speed_kmh: 108,
    speed_limit_kmh: 90,
    lat: 55.72,
    lon: 37.65,
    address: 'Варшавское ш., 34',
    is_night: true,
    continuous_driving_min: 120,
    events_last_7d: 7,
    confidence: 80,
    event_version: 'Резкое торможение 108→45 км/ч за 3 с с превышением +18 км/ч.',
    sensor_active_after_sec: null,
    mileage_km: 12100.0,
    movement_duration: '02:00:00',
    video_count: 1,
    video_available: true,
    cam_front_url: 'datasets/media/video_events/cam1_brake.mp4',
    cam_dms_url: null,
    cam_extra: [],
    status: 'validated',
    evidence_summary:
      'Резкое торможение со 108 км/ч до 45 км/ч за 3 секунды. Водитель двигался с превышением +18 км/ч.',
    cameras: [
      { id: 'CAM-01', label: 'ADAS · Передняя', status: 'online', hasVideo: true, offline_from: null, offline_to: null },
      { id: 'CAM-02', label: 'DMS · Салон', status: 'warning', hasVideo: false, offline_from: '2026-04-02T00:58:30', offline_to: '2026-04-02T01:01:10' },
    ],
    telemetry: [
      { ts_offset: -60, speed: 110, ax: 0.0, ay: 0.1 },
      { ts_offset: -30, speed: 108, ax: -0.1, ay: 0.2 },
      { ts_offset: -15, speed: 107, ax: 0.0, ay: 0.0 },
      { ts_offset: 0, speed: 45, ax: -5.1, ay: -1.8 },
      { ts_offset: 15, speed: 48, ax: 0.5, ay: 0.3 },
      { ts_offset: 30, speed: 52, ax: 0.2, ay: -0.1 },
    ],
  },
  {
    // inc-005 · подмена водителя, есть видео, closed
    id: 'inc-005',
    alarm_type: 'DRIVER_SUBSTITUTION',
    alarm_code: 'DRIVER_SUBSTITUTION',
    alarm_label_ru: 'Подмена водителя',
    source: 'DMS',
    severity: 'medium',
    risk_level: 'medium',
    risk_score: 54,
    ts: '2026-04-02T01:50:00',
    ts_end: '2026-04-02T01:50:25',
    vehicle_plate: 'К451МА 77',
    unit_id: 'UNIT-005',
    unit_name: 'Volvo FH · К451МА 77',
    driver: 'Новиков Александр Владимирович',
    driver_id: 'DRV-6104',
    driver_phone: '+79265610493',
    driver_region: 'Москва',
    driver_department: 'Логистика · Запад',
    driver_safety_score: 63,
    vehicle_model: 'Volvo FH',
    speed_kmh: 0,
    speed_limit_kmh: 90,
    lat: 55.7,
    lon: 37.55,
    address: 'Каширское ш., 78',
    is_night: true,
    continuous_driving_min: 15,
    events_last_7d: 2,
    confidence: 74,
    event_version: 'DMS: лицо за рулём не совпадает с авторизованным профилем.',
    sensor_active_after_sec: null,
    mileage_km: 6800.3,
    movement_duration: '00:15:00',
    video_count: 2,
    video_available: true,
    cam_front_url: 'datasets/media/video_events/cam1_sub.mp4',
    cam_dms_url: 'datasets/media/video_events/cam2_sub.mp4',
    cam_extra: [],
    status: 'closed',
    evidence_summary:
      'DMS зафиксировала смену водителя без авторизации. Лицо за рулём не совпадает с профилем.',
    cameras: [
      { id: 'CAM-01', label: 'ADAS · Передняя', status: 'online', hasVideo: true, offline_from: null, offline_to: null },
      { id: 'CAM-02', label: 'DMS · Салон', status: 'online', hasVideo: true, offline_from: null, offline_to: null },
    ],
    telemetry: [
      { ts_offset: -60, speed: 65, ax: 0.0, ay: 0.1 },
      { ts_offset: -30, speed: 0, ax: 0.0, ay: 0.0 },
      { ts_offset: 0, speed: 0, ax: 0.0, ay: 0.0 },
      { ts_offset: 15, speed: 0, ax: 0.0, ay: 0.0 },
      { ts_offset: 30, speed: 0, ax: 0.0, ay: 0.0 },
    ],
  },
]

/** Детали инцидента по id (для GET /incidents/{id}). */
export const INCIDENT_DETAILS: Record<string, IncidentDetail> =
  Object.fromEntries(DETAILS.map((d) => [d.id, d]))

/** Проекция IncidentDetail → IncidentSummary (поля ленты §3.1). */
function toSummary(d: IncidentDetail): IncidentSummary {
  return {
    id: d.id,
    alarm_type: d.alarm_type,
    alarm_code: d.alarm_code,
    alarm_label_ru: d.alarm_label_ru,
    source: d.source,
    severity: d.severity,
    risk_level: d.risk_level,
    risk_score: d.risk_score,
    ts: d.ts,
    vehicle_plate: d.vehicle_plate,
    driver: d.driver,
    vehicle_model: d.vehicle_model,
    speed_kmh: d.speed_kmh,
    lat: d.lat,
    lon: d.lon,
    address: d.address,
    video_available: d.video_available,
    status: d.status,
  }
}

/** Лента инцидентов (для GET /incidents). ≥5 записей. */
export const INCIDENTS: IncidentSummary[] = DETAILS.map(toSummary)

// ── Vehicles (порт data/mock/vehicles.py) ─────────────────────────────────────

export const VEHICLES: VehicleSummary[] = [
  {
    id: 'veh-001',
    plate: 'А777ВВ 77',
    model: 'ГАЗон NEXT',
    driver: 'Иванов Алексей Петрович',
    division: 'Логистика · Север-1',
    alarm_count: 12,
    alarm_types: 'DMS_DROWSY|OVERSPEED|HARSH_BRAKING',
    downloaded_video_count: 24,
    total_track_mileage_km: 4520.5,
    avg_speed_kmh: 68.3,
    cameras: [
      { id: 'CAM-01', label: 'ADAS · Передняя', status: 'online' },
      { id: 'CAM-02', label: 'DMS · Салон', status: 'online' },
      { id: 'CAM-03', label: 'CH3 · Правая', status: 'offline' },
    ],
    telematics_status: 'online',
    archive_status: 'available',
    connection_status: 'online',
    engine_hours: 12450,
    last_maintenance: '2026-01-15',
  },
  {
    id: 'veh-002',
    plate: 'В345КМ 97',
    model: 'КамАЗ-5490',
    driver: 'Петров Дмитрий Сергеевич',
    division: 'Логистика · Центр',
    alarm_count: 8,
    alarm_types: 'CRASH_SENSOR|HARSH_CORNERING',
    downloaded_video_count: 16,
    total_track_mileage_km: 8750.2,
    avg_speed_kmh: 72.1,
    cameras: [
      { id: 'CAM-01', label: 'ADAS · Передняя', status: 'online' },
      { id: 'CAM-02', label: 'DMS · Салон', status: 'online' },
      { id: 'CAM-03', label: 'CH3 · Задняя', status: 'offline' },
    ],
    telematics_status: 'online',
    archive_status: 'available',
    connection_status: 'online',
    engine_hours: 8900,
    last_maintenance: '2026-03-01',
  },
  {
    id: 'veh-003',
    plate: 'Е902СТ 150',
    model: 'ГАЗель NEXT',
    driver: 'Сидоров Владимир Николаевич',
    division: 'Доставка · Юг',
    alarm_count: 15,
    alarm_types: 'DMS_PHONE|OVERSPEED|DMS_SEATBELT',
    downloaded_video_count: 8,
    total_track_mileage_km: 3200.8,
    avg_speed_kmh: 82.4,
    cameras: [
      { id: 'CAM-01', label: 'ADAS · Передняя', status: 'online' },
      { id: 'CAM-02', label: 'DMS · Салон', status: 'online' },
      { id: 'CAM-03', label: 'CH3 · Задняя', status: 'offline' },
    ],
    telematics_status: 'online',
    archive_status: 'warning',
    connection_status: 'online',
    engine_hours: 5600,
    last_maintenance: '2025-12-20',
  },
  {
    id: 'veh-004',
    plate: 'Н124УУ 199',
    model: 'МАЗ-5440',
    driver: 'Козлов Иван Андреевич',
    division: 'Логистика · Восток',
    alarm_count: 21,
    alarm_types: 'HARSH_BRAKING|OVERSPEED|HARSH_ACCELERATION',
    downloaded_video_count: 30,
    total_track_mileage_km: 12100.0,
    avg_speed_kmh: 76.8,
    cameras: [
      { id: 'CAM-01', label: 'ADAS · Передняя', status: 'online' },
      { id: 'CAM-02', label: 'DMS · Салон', status: 'warning' },
    ],
    telematics_status: 'online',
    archive_status: 'available',
    connection_status: 'online',
    engine_hours: 15300,
    last_maintenance: '2026-02-10',
  },
  {
    id: 'veh-005',
    plate: 'К451МА 77',
    model: 'Volvo FH',
    driver: 'Новиков Александр Владимирович',
    division: 'Логистика · Запад',
    alarm_count: 5,
    alarm_types: 'DRIVER_SUBSTITUTION|DMS_SMOKING',
    downloaded_video_count: 10,
    total_track_mileage_km: 6800.3,
    avg_speed_kmh: 70.5,
    cameras: [
      { id: 'CAM-01', label: 'ADAS · Передняя', status: 'online' },
      { id: 'CAM-02', label: 'DMS · Салон', status: 'online' },
    ],
    telematics_status: 'online',
    archive_status: 'available',
    connection_status: 'online',
    engine_hours: 7200,
    last_maintenance: '2026-04-01',
  },
]

// ── Reports (минимально валидные, §7.5) ───────────────────────────────────────

const DEMO_PERIOD = { from: '2026-03-30', to: '2026-04-02', days: 3 }

/** GET /reports/driver/{plate} — отчёт по Иванову (А777ВВ 77). */
export const DRIVER_REPORT: DriverReport = {
  driver: {
    driver_id: 'DRV-2841',
    driver_name: 'Иванов Алексей Петрович',
    role: 'main',
    trips: 14,
    safety_score: 41,
    risk_score: 97,
  },
  vehicle_plate: 'А777ВВ 77',
  vehicle_model: 'ГАЗон NEXT',
  period: DEMO_PERIOD,
  mileage_km: 4520.5,
  trips: 14,
  kpi: { total: 12, video_da: 7, telematics: 5, gross: 4 },
  disciplinary_warning: true, // gross>=3 ИЛИ safety_score<60
  violations: [
    {
      id: 'inc-001',
      ts: '2026-04-02T00:36:43',
      alarm_code: 'DMS_DROWSY',
      alarm_label_ru: 'Засыпание за рулём (микросон)',
      source: 'DMS',
      severity: 'critical',
      is_gross: true,
    },
    {
      id: 'inc-006',
      ts: '2026-04-01T22:10:00',
      alarm_code: 'OVERSPEED',
      alarm_label_ru: 'Превышение скорости',
      source: 'TELEMATICS',
      severity: 'high',
      is_gross: true,
    },
    {
      id: 'inc-007',
      ts: '2026-03-31T08:42:00',
      alarm_code: 'HARSH_BRAKING',
      alarm_label_ru: 'Резкое торможение',
      source: 'TELEMATICS',
      severity: 'medium',
      is_gross: false,
    },
  ],
}

/** GET /reports/fleet — агрегаты по парку (В-1/В-2). */
export const FLEET_REPORT: FleetReport = {
  period: DEMO_PERIOD,
  kpi: { total: 61, video_da: 28, telematics: 33, gross: 14 },
  vehicles_count: 5,
  by_drivers: [
    {
      driver: { driver_id: 'DRV-2841', driver_name: 'Иванов Алексей Петрович', role: 'main', trips: 14, safety_score: 41, risk_score: 97 },
      vehicle_plate: 'А777ВВ 77',
      vehicle_model: 'ГАЗон NEXT',
      mileage_km: 4520.5,
      risk_score: 97,
      gross: 4,
      total: 12,
    },
    {
      driver: { driver_id: 'DRV-5023', driver_name: 'Козлов Иван Андреевич', role: 'main', trips: 9, safety_score: 52, risk_score: 68 },
      vehicle_plate: 'Н124УУ 199',
      vehicle_model: 'МАЗ-5440',
      mileage_km: 12100.0,
      risk_score: 68,
      gross: 5,
      total: 21,
    },
    {
      driver: { driver_id: 'DRV-4501', driver_name: 'Сидоров Владимир Николаевич', role: 'main', trips: 11, safety_score: 49, risk_score: 76 },
      vehicle_plate: 'Е902СТ 150',
      vehicle_model: 'ГАЗель NEXT',
      mileage_km: 3200.8,
      risk_score: 76,
      gross: 3,
      total: 15,
    },
  ],
  by_vehicles: [
    { plate: 'А777ВВ 77', vehicle_model: 'ГАЗон NEXT', main_driver: 'Иванов Алексей Петрович', mileage_km: 4520.5, risk_score: 97, gross: 4, total: 12, cameras_ok: '2/3' },
    { plate: 'В345КМ 97', vehicle_model: 'КамАЗ-5490', main_driver: 'Петров Дмитрий Сергеевич', mileage_km: 8750.2, risk_score: 84, gross: 2, total: 8, cameras_ok: '2/3' },
    { plate: 'Н124УУ 199', vehicle_model: 'МАЗ-5440', main_driver: 'Козлов Иван Андреевич', mileage_km: 12100.0, risk_score: 68, gross: 5, total: 21, cameras_ok: '1/2' },
  ],
}

// ── Заявки (§7.5 Ticket, идея #6) ─────────────────────────────────────────────
// Журнал действий (`output/actions.csv`). `is_overdue` — производное поле бэка
// (`deadline < now И status ∉ {closed}`); «Просрочена» — НЕ статус, а оверлей.
// Покрыты все статусы (active/in_progress/validated/closed) и оба исхода overdue.

export const TICKETS: Ticket[] = [
  {
    id: 'tkt-001',
    created_at: '2026-04-02T08:14:00',
    incident_id: 'inc-001',
    action: 'create_task',
    comment: 'Назначить разбор засыпания с водителем',
    status: 'active',
    deadline: '2026-06-30T18:00:00',
    is_overdue: false,
  },
  {
    id: 'tkt-002',
    created_at: '2026-04-02T09:40:00',
    incident_id: 'inc-002',
    action: 'request_archive',
    comment: 'Запросить архив по фронтальной камере',
    status: 'in_progress',
    deadline: '2026-04-10T18:00:00',
    is_overdue: true,
  },
  {
    id: 'tkt-003',
    created_at: '2026-04-03T11:05:00',
    incident_id: 'inc-003',
    action: 'export_report',
    comment: 'Отчёт по водителю выгружен и передан в ОТ',
    status: 'closed',
    deadline: '2026-04-05T18:00:00',
    is_overdue: false,
  },
  {
    id: 'tkt-004',
    created_at: '2026-04-03T15:22:00',
    incident_id: 'inc-004',
    action: 'mark_reviewed',
    comment: 'Событие просмотрено, нарушение подтверждено',
    status: 'validated',
    deadline: null,
    is_overdue: false,
  },
  {
    id: 'tkt-005',
    created_at: '2026-04-04T07:50:00',
    incident_id: 'inc-005',
    action: 'call_driver',
    comment: 'Связаться с водителем по факту резкого торможения',
    status: 'active',
    deadline: '2026-04-08T12:00:00',
    is_overdue: true,
  },
  {
    id: 'tkt-006',
    created_at: '2026-04-04T16:18:00',
    incident_id: 'inc-001',
    action: 'notify_hr',
    comment: 'Передать в HR для дисциплинарной беседы',
    status: 'in_progress',
    deadline: null,
    is_overdue: false,
  },
]

// ── Саботаж камеры (§7.5 SabotageEvent, идея #9) ──────────────────────────────
// Тёмный DMS-кадр (`dms_dark`) при движении (`speed_kmh > 0`) — корреляция-улика.
// Бэк (`v_sabotage`, b11) уже фильтрует `dms_dark=false`/`speed_kmh=0`.

export const SABOTAGE_EVENTS: SabotageEvent[] = [
  {
    id: 'sab-001',
    vehicle_plate: 'А777ВВ 77',
    ts: '2026-04-02T03:14:22',
    dms_dark: true,
    speed_kmh: 64,
    driver_name: 'Иванов Алексей Петрович',
    video_url: '',
  },
  {
    id: 'sab-002',
    vehicle_plate: 'В045КК 77',
    ts: '2026-04-01T22:48:10',
    dms_dark: true,
    speed_kmh: 81,
    driver_name: 'Петров Сергей Николаевич',
    video_url: '',
  },
  {
    id: 'sab-003',
    vehicle_plate: 'Н124УУ 199',
    ts: '2026-03-31T19:05:37',
    dms_dark: true,
    speed_kmh: 47,
    driver_name: 'Козлов Иван Андреевич',
    video_url: '',
  },
]

// ── Trip dossier (§7.5, идея #7) ──────────────────────────────────────────────
// TelemetryPoint без координат (§7.5) — карта f10 строит синтетику по последовательности.

export const TRIP_DOSSIER: TripDossier = {
  vehicle_plate: 'А777ВВ 77',
  track: [
    { ts_offset: -120, speed: 64, ax: 0.1, ay: -0.1 },
    { ts_offset: -90, speed: 70, ax: 0.2, ay: 0.0 },
    { ts_offset: -60, speed: 75, ax: 0.1, ay: -0.2 },
    { ts_offset: -30, speed: 72, ax: 0.0, ay: 0.1 },
    { ts_offset: 0, speed: 0, ax: -4.5, ay: 0.6 },
    { ts_offset: 30, speed: 18, ax: 0.4, ay: -0.1 },
    { ts_offset: 60, speed: 40, ax: 0.2, ay: 0.0 },
    { ts_offset: 90, speed: 55, ax: 0.1, ay: 0.1 },
    { ts_offset: 120, speed: 60, ax: 0.0, ay: -0.1 },
  ],
  timeline: [
    { ts_offset: -90, alarm_code: 'OVERSPEED', label: 'Превышение скорости', has_video: true },
    { ts_offset: -30, alarm_code: 'HARSH_CORNERING', label: 'Резкий манёвр', has_video: false },
    { ts_offset: 0, alarm_code: 'CRASH_SENSOR', label: 'Подозрение на ДТП — датчик удара', has_video: true },
    { ts_offset: 60, alarm_code: 'HARSH_BRAKING', label: 'Резкое торможение', has_video: true },
  ],
}

// ── Хелперы (повторяют сигнатуры клиента f2) ──────────────────────────────────

/** Деталь инцидента по id или undefined (как getIncident до сетевой ошибки). */
export function getFixtureIncident(id: string): IncidentDetail | undefined {
  return INCIDENT_DETAILS[id]
}

/** Досье рейса по id; `trip-001` — демо-рейс, иначе undefined (→ 404 как на API). */
export function getFixtureTrip(id: string): TripDossier | undefined {
  return id === 'trip-001' ? TRIP_DOSSIER : undefined
}

/** Лента инцидентов с фильтрами (сигнатура listIncidents). */
export function listFixtureIncidents(
  filters?: IncidentFilters,
): IncidentSummary[] {
  let rows = INCIDENTS
  if (filters?.severity) rows = rows.filter((r) => r.severity === filters.severity)
  if (filters?.source) rows = rows.filter((r) => r.source === filters.source)
  if (filters?.status) rows = rows.filter((r) => r.status === filters.status)
  if (filters?.vehicle_plate)
    rows = rows.filter((r) => r.vehicle_plate === filters.vehicle_plate)
  const offset = filters?.offset ?? 0
  const limit = filters?.limit ?? 100
  return rows.slice(offset, offset + limit)
}

// ── Отчёт по ТС (§7.5 VehicleReport, идея #2 В-3) ──────────────────────────────
// Закрывает дыру: getVehicleReport раньше шёл в сеть и в фикстур-режиме (демо-сирота).

/** GET /reports/vehicle/{plate} — карточка ТС А777ВВ 77 (len(cameras)=3, §7.5). */
export const VEHICLE_REPORT: VehicleReport = {
  plate: 'А777ВВ 77',
  vehicle_model: 'ГАЗон NEXT',
  risk_score: 97,
  cameras: [
    { id: 'CAM-01', label: 'ADAS · Передняя', status: 'online', hasVideo: true, offline_from: null, offline_to: null },
    { id: 'CAM-02', label: 'DMS · Салон', status: 'online', hasVideo: true, offline_from: null, offline_to: null },
    { id: 'CAM-03', label: 'CH3 · Правая', status: 'offline', hasVideo: false, offline_from: '2026-04-01T19:10:00', offline_to: null },
  ],
  drivers: [
    { driver_id: 'DRV-2841', driver_name: 'Иванов Алексей Петрович', role: 'main', trips: 14, safety_score: 41, risk_score: 97 },
    { driver_id: 'DRV-2902', driver_name: 'Морозов Сергей Иванович', role: 'secondary', trips: 3, safety_score: 71, risk_score: 38 },
  ],
  period: DEMO_PERIOD,
  period_alarms: [
    { id: 'inc-001', ts: '2026-04-02T00:36:43', alarm_code: 'DMS_DROWSY', alarm_label_ru: 'Засыпание за рулём (микросон)', source: 'DMS', severity: 'critical', is_gross: true },
    { id: 'inc-006', ts: '2026-04-01T22:10:00', alarm_code: 'OVERSPEED', alarm_label_ru: 'Превышение скорости', source: 'TELEMATICS', severity: 'high', is_gross: true },
  ],
  mileage_km: 4520.5,
  trips: 14,
}

// ── Волна 3 · тёмные данные (fuel / sensors / navigation / fleet-health, §9) ───
// Реалистичные значения (числа сходятся), без Date.now(). 2–3 реальных госномера
// на домен. Госномера резолвятся с нормализацией (strip пробелов + upper, §9.1).

/** Нормализация госномера для lookup (strip пробелов + upper, как в §9.1). */
function normPlate(plate: string): string {
  return plate.replace(/\s+/g, '').toUpperCase()
}

// fuel (10 ТС в покрытии; здесь 2 реальных). Карточки — источник, summary — проекция.
const FUEL_CARD_LIST: FuelVehicleCard[] = [
  {
    // А144ЕВ193 — пример из w3-10: ЗИС > карта на 22.5 л (>4 л → severity), статус review.
    vehicle_id: 'А144ЕВ193',
    model: 'КамАЗ-65115',
    vin: 'XTC651150P1234567',
    fuel_volume_zis_l: 820.5,
    fuel_volume_card_l: 798.0,
    volume_delta_zis_minus_card_l: 22.5,
    refuel_count_zis: 12,
    transaction_count_card: 11,
    period_start: '2026-03-01',
    period_end: '2026-03-31',
    recon_status: 'review',
    summary: {
      fuel_spent_l: 796.0,
      total_mileage_km: 2840.0,
      average_consumption_l_per_100km: 28.0, // 796 / 2840 * 100
      average_speed_kmh: 42.5,
      fuelings_count: 12,
      defuelings_count: 2,
    },
    reconciliation: [
      {
        row_id: 'fr-144-01',
        transaction_ts: '2026-03-04T08:12:00',
        event_ts: '2026-03-04T08:15:00',
        transaction_volume_l: 60.0,
        sensor_volume_l: 60.0,
        volume_delta_l: 0.0,
        time_delta_min: 3.0,
        amount_rub: 4200.0,
        status: 'matched',
        reason: null,
      },
      {
        row_id: 'fr-144-02',
        transaction_ts: '2026-03-12T19:40:00',
        event_ts: '2026-03-12T20:08:00',
        transaction_volume_l: 70.0,
        sensor_volume_l: 47.5,
        volume_delta_l: 22.5,
        time_delta_min: 28.0,
        amount_rub: 4900.0,
        status: 'review',
        reason: 'Расхождение объёма >20 л и времени >25 мин',
      },
      {
        row_id: 'fr-144-03',
        transaction_ts: '2026-03-20T07:05:00',
        event_ts: null,
        transaction_volume_l: 55.0,
        sensor_volume_l: null,
        volume_delta_l: null,
        time_delta_min: null,
        amount_rub: 3850.0,
        status: 'missing_sensor_event',
        reason: 'Транзакция по карте без события датчика',
      },
    ],
    events: [
      {
        event_id: 'fe-144-01',
        event_ts: '2026-03-04T08:15:00',
        event_name: 'Заправка',
        volume_l: 60.0,
        before_l: 18.0,
        after_l: 78.0,
        lat: 45.0355,
        lon: 38.975,
        address: 'Краснодар, ул. Новороссийская, 2',
      },
      {
        event_id: 'fe-144-02',
        event_ts: '2026-03-18T02:40:00',
        event_name: 'Слив',
        volume_l: -45.0,
        before_l: 70.0,
        after_l: 25.0,
        lat: 45.12,
        lon: 39.02,
        address: null,
      },
    ],
  },
  {
    // Т218НА123 — сверка чистая (Δ 1.1 л), статус matched.
    vehicle_id: 'Т218НА123',
    model: 'ГАЗ-3309',
    vin: 'X9633090P0456712',
    fuel_volume_zis_l: 540.0,
    fuel_volume_card_l: 538.9,
    volume_delta_zis_minus_card_l: 1.1,
    refuel_count_zis: 8,
    transaction_count_card: 8,
    period_start: '2026-03-01',
    period_end: '2026-03-31',
    recon_status: 'matched',
    summary: {
      fuel_spent_l: 539.0,
      total_mileage_km: 2160.0,
      average_consumption_l_per_100km: 25.0, // 539 / 2160 * 100 ≈ 24.95
      average_speed_kmh: 38.0,
      fuelings_count: 8,
      defuelings_count: 0,
    },
    reconciliation: [
      {
        row_id: 'fr-218-01',
        transaction_ts: '2026-03-06T09:20:00',
        event_ts: '2026-03-06T09:22:00',
        transaction_volume_l: 65.0,
        sensor_volume_l: 64.5,
        volume_delta_l: 0.5,
        time_delta_min: 2.0,
        amount_rub: 4550.0,
        status: 'matched',
        reason: null,
      },
    ],
    events: [
      {
        event_id: 'fe-218-01',
        event_ts: '2026-03-06T09:22:00',
        event_name: 'Заправка',
        volume_l: 65.0,
        before_l: 12.0,
        after_l: 77.0,
        lat: 51.66,
        lon: 39.2,
        address: 'Воронеж, Московский пр-т, 144',
      },
    ],
  },
]

/** Карточки топлива по нормализованному госномеру (GET /api/fuel/{plate}). */
export const FUEL_CARDS: Record<string, FuelVehicleCard> = Object.fromEntries(
  FUEL_CARD_LIST.map((c) => [normPlate(c.vehicle_id), c]),
)

/** Проекция FuelVehicleCard → FuelVehicleSummary (поля ленты §9.2). */
function toFuelSummary(c: FuelVehicleCard): FuelVehicleSummary {
  return {
    vehicle_id: c.vehicle_id,
    model: c.model,
    vin: c.vin,
    fuel_volume_zis_l: c.fuel_volume_zis_l,
    fuel_volume_card_l: c.fuel_volume_card_l,
    volume_delta_zis_minus_card_l: c.volume_delta_zis_minus_card_l,
    refuel_count_zis: c.refuel_count_zis,
    transaction_count_card: c.transaction_count_card,
    period_start: c.period_start,
    period_end: c.period_end,
    recon_status: c.recon_status,
  }
}

/** Список топлива (GET /api/fuel). */
export const FUEL_VEHICLES: FuelVehicleSummary[] = FUEL_CARD_LIST.map(toFuelSummary)

/** Карточка топлива по госномеру или undefined (→ 404). */
export function getFixtureFuel(plate: string): FuelVehicleCard | undefined {
  return FUEL_CARDS[normPlate(plate)]
}

// sensors (7 ТС в покрытии; здесь 2 реальных: online с разрывом + stale без данных).
const SENSOR_CARD_LIST: SensorVehicleCard[] = [
  {
    // Т671КР31 — пример из w3-10: CAN−GPS разрыв 540 км (1840 − 1300).
    public_unit_id: 'd3b07384-d9a0-4c9b-8f21-2a7c0e9f5a10',
    vehicle_label: 'КамАЗ-43118 · Т671КР31',
    plate: 'Т671КР31',
    gps_total_distance_km: 1300.0,
    distance_odometer_km: 1840.0,
    distance_gap_odometer_minus_gps_km: 540.0,
    max_speed_kmh: 92.0,
    average_speed_kmh: 38.0,
    satellite_amount: 14,
    online_status: 'online',
    sensor_count: 6,
    daily_mileage: [
      { date: '2026-03-25', distance_km: 240.0 },
      { date: '2026-03-26', distance_km: 310.0 },
      { date: '2026-03-27', distance_km: 180.0 },
      { date: '2026-03-28', distance_km: 0.0 },
      { date: '2026-03-29', distance_km: 270.0 },
      { date: '2026-03-30', distance_km: 195.0 },
      { date: '2026-03-31', distance_km: 105.0 },
    ],
    engine: {
      first_ignition_on: '2026-03-31T05:12:00',
      last_ignition_off: '2026-03-31T19:48:00',
      ignition_duration: '14:36:00',
      idle_duration: '02:10:00',
    },
    fuel_level: { first_fuel_level: 210.0, last_fuel_level: 160.0, delta_fuel_level: -50.0 },
    snapshot: {
      speed_kmh: 0.0,
      fuel_volume: 160.0,
      satellite_amount: 12,
      timestamp_utc: '2026-03-31T19:48:30',
      last_valid_navigation_timestamp: '2026-03-31T19:30:00',
      odometer_mileage: 1840.0,
      longitude: 39.72,
      latitude: 47.22,
    },
  },
  {
    // Х905ОР37 — stale (last_valid_nav = null), CAN−GPS разрыв отсутствует («нет данных»).
    public_unit_id: 'a47f1c20-6b8e-4d3a-9e15-3c0d8b2f6e44',
    vehicle_label: 'ГАЗ-3309 · Х905ОР37',
    plate: 'Х905ОР37',
    gps_total_distance_km: 410.0,
    distance_odometer_km: 425.0,
    distance_gap_odometer_minus_gps_km: null, // нет CAN−GPS данных → «нет данных», не 0
    max_speed_kmh: 78.0,
    average_speed_kmh: 31.5,
    satellite_amount: 9,
    online_status: 'stale',
    sensor_count: 4,
    daily_mileage: [
      { date: '2026-03-25', distance_km: 70.0 },
      { date: '2026-03-26', distance_km: 55.0 },
      { date: '2026-03-27', distance_km: 90.0 },
      { date: '2026-03-28', distance_km: 60.0 },
      { date: '2026-03-29', distance_km: 45.0 },
      { date: '2026-03-30', distance_km: 50.0 },
      { date: '2026-03-31', distance_km: 40.0 },
    ],
    engine: {
      first_ignition_on: '2026-03-31T06:40:00',
      last_ignition_off: '2026-03-31T15:20:00',
      ignition_duration: '08:40:00',
      idle_duration: '01:05:00',
    },
    fuel_level: { first_fuel_level: 95.0, last_fuel_level: 80.0, delta_fuel_level: -15.0 },
    snapshot: {
      speed_kmh: 0.0,
      fuel_volume: 80.0,
      satellite_amount: 6,
      timestamp_utc: '2026-03-31T15:20:10',
      last_valid_navigation_timestamp: null, // → online_status = stale (§9.3/§9.5)
      odometer_mileage: 425.0,
      longitude: 44.52,
      latitude: 48.71,
    },
  },
]

/** Карточки сенсоров по нормализованному госномеру (GET /api/sensors/{plate}). */
export const SENSOR_CARDS: Record<string, SensorVehicleCard> = Object.fromEntries(
  SENSOR_CARD_LIST.filter((c) => c.plate).map((c) => [normPlate(c.plate as string), c]),
)

/** Проекция SensorVehicleCard → SensorVehicleSummary (поля ленты §9.2). */
function toSensorSummary(c: SensorVehicleCard): SensorVehicleSummary {
  return {
    public_unit_id: c.public_unit_id,
    vehicle_label: c.vehicle_label,
    plate: c.plate,
    gps_total_distance_km: c.gps_total_distance_km,
    distance_odometer_km: c.distance_odometer_km,
    distance_gap_odometer_minus_gps_km: c.distance_gap_odometer_minus_gps_km,
    max_speed_kmh: c.max_speed_kmh,
    average_speed_kmh: c.average_speed_kmh,
    satellite_amount: c.satellite_amount,
    online_status: c.online_status,
    sensor_count: c.sensor_count,
  }
}

/** Список сенсоров (GET /api/sensors). */
export const SENSOR_VEHICLES: SensorVehicleSummary[] = SENSOR_CARD_LIST.map(toSensorSummary)

/** Карточка сенсоров по госномеру или undefined (→ 404). */
export function getFixtureSensor(plate: string): SensorVehicleCard | undefined {
  return SENSOR_CARDS[normPlate(plate)]
}

// navigation (5 ТС в покрытии; здесь 2 matched в видеопарке + 1 unmatched).
// reb_link_id = public_unit_id; unmatched → reb_link_id = null (не кликабельно).
const NAV_REB_O802 = 'a1f0c2d4-7b3e-4e21-9c8a-0d5e6f701234'
const NAV_REB_S725 = 'b2e1d3c5-8c4f-4f32-ad9b-1e6f70812345'

/** Список проблемных треков (GET /api/navigation). */
export const NAV_PROBLEMS: NavProblemVehicle[] = [
  {
    public_unit_id: NAV_REB_O802,
    plate: 'О802УЕ198',
    vehicle_label: 'МАЗ-6312 · О802УЕ198',
    brand: 'МАЗ',
    problem_description:
      'Систематическая потеря GPS на участке трассы М-4: 4 разрыва за смену, суммарно ~1.5 ч без сигнала.',
    match_status: 'matched',
    gap_count: 4,
    total_periods: 11,
    total_gap_duration_sec: 5400,
    reb_link_id: NAV_REB_O802,
    in_video_fleet: true,
  },
  {
    public_unit_id: NAV_REB_S725,
    plate: 'С725АТ159',
    vehicle_label: 'КамАЗ-65207 · С725АТ159',
    brand: 'КамАЗ',
    problem_description:
      'Кратковременные пропадания спутников в городской застройке: 2 разрыва, ~31 мин суммарно.',
    match_status: 'matched',
    gap_count: 2,
    total_periods: 7,
    total_gap_duration_sec: 1860,
    reb_link_id: NAV_REB_S725,
    in_video_fleet: true,
  },
  {
    // unmatched: public_unit_id=null → reb_link_id=null (строка не кликабельна в РЭБ, §9.5).
    public_unit_id: null,
    plate: null,
    vehicle_label: 'Газель(ТМ)',
    brand: null,
    problem_description:
      'ТС не сматчено со справочником: трек содержит 1 длинный разрыв, привязка к РЭБ недоступна.',
    match_status: 'unmatched',
    gap_count: 1,
    total_periods: 3,
    total_gap_duration_sec: 600,
    reb_link_id: null,
    in_video_fleet: false,
  },
]

/** Сводка навигации по госномеру или undefined (→ 404). */
export function getFixtureNavProblem(plate: string): NavProblemVehicle | undefined {
  const key = normPlate(plate)
  return NAV_PROBLEMS.find((n) => n.plate && normPlate(n.plate) === key)
}

// reb (закрывает дыру п.2: getReb в фикстур-режиме раньше шёл в сеть).
// Ключ = reb_link_id (= public_unit_id) matched-навигационных ТС.
export const REB_RECOVERY: Record<string, RebRecovery> = {
  [NAV_REB_O802]: {
    vehicle_plate: 'О802УЕ198',
    gps_track: [
      { lat: 47.21, lon: 39.7, ts: '2026-03-31T09:00:00' },
      { lat: 47.25, lon: 39.78, ts: '2026-03-31T09:05:00' },
      // разрыв 09:06–09:24 (GPS потерян)
      { lat: 47.34, lon: 39.95, ts: '2026-03-31T09:24:00' },
      { lat: 47.38, lon: 40.02, ts: '2026-03-31T09:29:00' },
    ],
    gap_periods: [
      { start: '2026-03-31T09:05:00', end: '2026-03-31T09:24:00', duration_sec: 1140 },
    ],
    video_frames: [
      { ts: '2026-03-31T09:10:00', channel: 1, url: '' },
      { ts: '2026-03-31T09:16:00', channel: 2, url: '' },
    ],
  },
  [NAV_REB_S725]: {
    vehicle_plate: 'С725АТ159',
    gps_track: [
      { lat: 58.0, lon: 56.24, ts: '2026-03-30T14:00:00' },
      { lat: 58.02, lon: 56.3, ts: '2026-03-30T14:04:00' },
      // разрыв 14:05–14:15
      { lat: 58.05, lon: 56.39, ts: '2026-03-30T14:15:00' },
    ],
    gap_periods: [
      { start: '2026-03-30T14:04:00', end: '2026-03-30T14:15:00', duration_sec: 660 },
    ],
    video_frames: [{ ts: '2026-03-30T14:09:00', channel: 1, url: '' }],
  },
}

/** РЭБ-восстановление по id (= reb_link_id) или undefined (→ 404). */
export function getFixtureReb(id: string): RebRecovery | undefined {
  return REB_RECOVERY[id]
}

// fleet-health (объединение disjoint-доменов; «—» = null; покрытие 10/7/5/2, §9.0).
export const FLEET_HEALTH: FleetHealthResponse = {
  coverage: { fuel: 10, sensors: 7, navigation: 5, in_video_fleet: 2 },
  rows: [
    {
      plate: 'А144ЕВ193',
      vehicle_label: 'КамАЗ-65115',
      in_video_fleet: false,
      has_fuel: true,
      has_sensors: false,
      has_nav: false,
      volume_delta_zis_minus_card_l: 22.5,
      recon_status: 'review',
      distance_gap_odometer_minus_gps_km: null,
      online_status: null,
      gap_count: null,
      reb_link_id: null,
    },
    {
      plate: 'Т218НА123',
      vehicle_label: 'ГАЗ-3309',
      in_video_fleet: false,
      has_fuel: true,
      has_sensors: false,
      has_nav: false,
      volume_delta_zis_minus_card_l: 1.1,
      recon_status: 'matched',
      distance_gap_odometer_minus_gps_km: null,
      online_status: null,
      gap_count: null,
      reb_link_id: null,
    },
    {
      plate: 'Т671КР31',
      vehicle_label: 'КамАЗ-43118 · Т671КР31',
      in_video_fleet: false,
      has_fuel: false,
      has_sensors: true,
      has_nav: false,
      volume_delta_zis_minus_card_l: null,
      recon_status: null,
      distance_gap_odometer_minus_gps_km: 540.0,
      online_status: 'online',
      gap_count: null,
      reb_link_id: null,
    },
    {
      plate: 'Х905ОР37',
      vehicle_label: 'ГАЗ-3309 · Х905ОР37',
      in_video_fleet: false,
      has_fuel: false,
      has_sensors: true,
      has_nav: false,
      volume_delta_zis_minus_card_l: null,
      recon_status: null,
      distance_gap_odometer_minus_gps_km: null, // нет CAN−GPS данных → «нет данных»
      online_status: 'stale',
      gap_count: null,
      reb_link_id: null,
    },
    {
      plate: 'О802УЕ198',
      vehicle_label: 'МАЗ-6312 · О802УЕ198',
      in_video_fleet: true,
      has_fuel: false,
      has_sensors: false,
      has_nav: true,
      volume_delta_zis_minus_card_l: null,
      recon_status: null,
      distance_gap_odometer_minus_gps_km: null,
      online_status: null,
      gap_count: 4,
      reb_link_id: NAV_REB_O802,
    },
    {
      plate: 'С725АТ159',
      vehicle_label: 'КамАЗ-65207 · С725АТ159',
      in_video_fleet: true,
      has_fuel: false,
      has_sensors: false,
      has_nav: true,
      volume_delta_zis_minus_card_l: null,
      recon_status: null,
      distance_gap_odometer_minus_gps_km: null,
      online_status: null,
      gap_count: 2,
      reb_link_id: NAV_REB_S725,
    },
  ],
}
