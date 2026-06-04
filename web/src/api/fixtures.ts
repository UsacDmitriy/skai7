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
  FleetReport,
  IncidentDetail,
  IncidentFilters,
  IncidentSummary,
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

// ── Хелперы (повторяют сигнатуры клиента f2) ──────────────────────────────────

/** Деталь инцидента по id или undefined (как getIncident до сетевой ошибки). */
export function getFixtureIncident(id: string): IncidentDetail | undefined {
  return INCIDENT_DETAILS[id]
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
