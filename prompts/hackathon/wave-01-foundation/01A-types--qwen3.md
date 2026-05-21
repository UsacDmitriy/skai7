# 01A · types.ts
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 1

**Файл:** `code/frontend/src/types.ts`
**Только этот файл.**

Передавать: `data/mock/incidents.json` — поля должны совпадать.

```ts
// Уровень риска
export type RiskLevel = 'critical' | 'high' | 'medium' | 'low';

// Тип источника данных
export type EventSource = 'DMS' | 'ADAS' | 'TELEMATICS' | 'COMBINED';

// Статус источника
export type SourceStatus = 'online' | 'offline' | 'warning' | 'unknown';

// Действия диспетчера
export type ActionType =
  | 'request_archive' | 'create_ticket'
  | 'generate_report'  | 'call_driver';

// Типы событий (совпадает с alarm_type в incidents.json)
// Покрывают все 5 демо-кейсов из hackathon/ideas/00-product-concept.md:
// DMS_DROWSY (А777ВВ 77), CRASH_SENSOR (В345КМ 97), DMS_PHONE (Е902СТ 150),
// HARSH_BRAKING (Н124УУ 199), DRIVER_SUBSTITUTION (К451МА 77)
export type EventType =
  | 'DMS_DROWSY' | 'DMS_PHONE' | 'DMS_SEATBELT' | 'DMS_SMOKING'
  | 'ADAS_FCW'   | 'ADAS_HMW'  | 'ADAS_LDW'
  | 'CRASH_SENSOR'
  | 'HARSH_BRAKING' | 'HARSH_CORNERING' | 'OVERSPEED'
  | 'CAMERA_OFFLINE' | 'DRIVER_SUBSTITUTION';

// Точка телеметрии — поля совпадают с incidents.json[].telemetry[]
export interface TelemetryPoint {
  ts_offset:  number;   // offsetSec от момента события
  speed:      number;   // км/ч (из CAN)
  ax:         number;   // акселерометр X, м/с²
  ay:         number;   // акселерометр Y, м/с²
}

export interface Camera {
  id:       string;      // 'CAM-01'
  label:    string;      // 'ADAS · Передняя'
  status:   SourceStatus;
  hasVideo: boolean;
}

export interface Vehicle {
  id:                   string;
  plate:                string;
  model:                string;
  driver:               string;
  cameras:              Camera[];
  telematics_status:    SourceStatus;
  archive_status:       SourceStatus;
  calibration_required: boolean;
  connection_status:    SourceStatus;
}

// Инцидент — поля совпадают с data/mock/incidents.json
export interface Incident {
  id:                    string;      // 'inc-001'
  alarm_type:            EventType;
  alarm_type_label:      string;      // 'Засыпание за рулём (микросон)'
  vehicle_plate:         string;      // 'А777ВВ 77'
  vehicle_model:         string;
  driver:                string;      // 'Иванов Алексей Петрович'
  driver_id:             string;
  ts:                    string;      // ISO datetime
  speed_kmh:             number;
  speed_limit_kmh:       number;
  lat:                   number;
  lon:                   number;
  address:               string;
  continuous_driving_min: number;
  is_night:              boolean;
  events_last_7d:        number;
  score:                 number;      // 0–100
  score_breakdown:       object;
  status:                'active' | 'in_progress' | 'validated' | 'closed';
  video_available:       boolean;     // ключевое поле для кейса А/Б
  cam_front_url:         string;
  cam_dms_url:           string;
  telemetry:             TelemetryPoint[];
  evidence_summary:      string;
  risk_level:            RiskLevel;
  event_source:          EventSource;
}
```

**Check:** `tsc --noEmit` без ошибок. Поля совпадают с `data/mock/incidents.json`.
