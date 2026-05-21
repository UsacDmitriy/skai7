# 01F-C · analyticsPresets.ts + types/analytics.ts — Мок Идея #2
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 1
> Нужен для: VoiceQueryBox (пресеты) + AnalyticsScreen (типы)

Прочитай AGENTS.md и types.ts.

## 1F-C: frontend/src/data/analyticsPresets.ts

```typescript
const analyticsPresets = [
  // Режим В-1 — конкретный водитель
  {
    icon: '📊',
    label: 'Нарушения Иванова за последние 3 дня',
    query: 'Покажи нарушения по ВА и телематике у Иванова за последние три дня',
    mode: 'single_driver'
  },
  // Режим В-2 — весь парк
  {
    icon: '⚡',
    label: 'Топ нарушителей за май',
    query: 'Топ 5 водителей по нарушениям за май',
    mode: 'fleet'
  },
  {
    icon: '🔴',
    label: 'Грубые нарушения за квартал',
    query: 'Все грубые нарушения за последний квартал',
    mode: 'fleet'
  },
  {
    icon: '📷',
    label: 'Все нарушения по компании за 3 дня',
    query: 'Все нарушения по компании за последние три дня',
    mode: 'fleet'
  },
  {
    icon: '🌙',
    label: 'Ночные поездки этой недели',
    query: 'Все ночные поездки с нарушениями за эту неделю',
    mode: 'fleet'
  },
  {
    icon: '📋',
    label: 'Сравнить двух водителей',
    query: 'Сравни Иванова и Петрова за последний месяц',
    mode: 'single_driver'
  },
]

export default analyticsPresets
```

---


## Тип ParsedQuery (для NLU-ответа)

```typescript
// frontend/src/types/analytics.ts
export type AnalyticsMode = 'single_driver' | 'fleet'

export interface ParsedQuery {
  mode: AnalyticsMode       // NLU определяет: один водитель или парк
  driver?: string           // только для single_driver
  vehicleId?: string
  periodDays: number
  periodLabel: string
  dataTypes: ('va' | 'tel')[]
  confidence: number        // 0–1, показывается в подтверждающем окне
}
```

---

## Типы — frontend/src/types/analytics.ts

```typescript
export type AnalyticsMode = 'single_driver' | 'fleet'

export interface ParsedQuery {
  mode: AnalyticsMode
  driver?: string
  vehicleId?: string
  periodDays: number
  periodLabel: string
  dataTypes: ('va' | 'tel')[]
  confidence: number
}

// FleetVehicle используется в FleetVehiclesList и VehicleMiniDashboard
export interface FleetVehicle {
  vehicleId: string; model: string; riskScore: number;
  totalCount: number; grossCount: number; vaCount: number; telCount: number;
  mileageKm: number; tripsCount: number;
  camerasSummary: string; camerasStatus: 'ok' | 'warning' | 'error';
  cameras: { id: string; type: string; label: string; status: string }[];
  driversInPeriod: { name: string; trips: number; isPrimary: boolean; date?: string }[];
  lastViolations: Violation[];
  lat: number; lng: number;
}

export interface FleetDriver {
  rank: number
  driverName: string
  driverInitials: string
  vehicleId: string
  safetyScore: number
  totalCount: number
  grossCount: number
  vaCount: number
  telCount: number
  mileageKm: number
  lat: number
  lng: number
}
```

---

## 1F-D: data/mock/fleet-vehicles.json

Данные по ТС для режима В-2, вкладка «По ТС».
Ключевое отличие от driver-report: ТС = актив компании,
на одном ТС могут ездить разные водители за период.

```json
{
  "mode": "fleet_vehicles",
  "periodLabel": "14–16.05.2026",
  "vehicles": [
    {
      "rank": 1,
      "vehicleId": "А777ВВ 77",
      "model": "Scania R450",
      "riskScore": 68,
      "totalCount": 7,
      "grossCount": 1,
      "vaCount": 4,
      "telCount": 3,
      "mileageKm": 487,
      "tripsCount": 5,
      "driveTimeMin": 620,
      "cameras": [
        {"id": "CAM-01", "type": "ADAS", "label": "Передняя", "status": "online"},
        {"id": "CAM-02", "type": "DMS",  "label": "Салон",    "status": "online"},
        {"id": "CAM-03", "type": "CH3",  "label": "Боковая",  "status": "offline"}
      ],
      "camerasSummary": "2/3 работают",
      "camerasStatus": "warning",
      "driversInPeriod": [
        {"name": "Иванов А.П.", "trips": 4, "isPrimary": true},
        {"name": "Козлов И.А.", "trips": 1, "isPrimary": false, "date": "14.05"}
      ],
      "lastViolations": [
        {"date": "16.05", "time": "13:40", "type": "Отвлечение внимания",
         "source": "va", "severity": "high"},
        {"date": "15.05", "time": "21:15", "type": "Превышение +9 км/ч",
         "source": "tel", "severity": "medium"},
        {"date": "15.05", "time": "09:05", "type": "Ремень безопасности",
         "source": "va", "severity": "high"}
      ],
      "lat": 55.762, "lng": 37.634
    },
    {
      "rank": 2,
      "vehicleId": "В345КМ 97",
      "model": "MAN TGX",
      "riskScore": 72,
      "totalCount": 6,
      "grossCount": 2,
      "vaCount": 3,
      "telCount": 3,
      "mileageKm": 612,
      "tripsCount": 3,
      "driveTimeMin": 540,
      "cameras": [
        {"id": "CAM-01", "type": "ADAS", "label": "Передняя", "status": "online"},
        {"id": "CAM-02", "type": "DMS",  "label": "Салон",    "status": "online"},
        {"id": "CAM-03", "type": "CH3",  "label": "Боковая",  "status": "online"}
      ],
      "camerasSummary": "3/3 работают",
      "camerasStatus": "ok",
      "driversInPeriod": [
        {"name": "Петров Д.С.", "trips": 3, "isPrimary": true}
      ],
      "lastViolations": [],
      "lat": 55.748, "lng": 37.601
    },
    {
      "rank": 3,
      "vehicleId": "Е902СТ 150",
      "model": "Volvo FH",
      "riskScore": 76,
      "totalCount": 4,
      "grossCount": 0,
      "vaCount": 2,
      "telCount": 2,
      "mileageKm": 534,
      "tripsCount": 4,
      "driveTimeMin": 498,
      "cameras": [
        {"id": "CAM-01", "type": "ADAS", "label": "Передняя", "status": "online"},
        {"id": "CAM-02", "type": "DMS",  "label": "Салон",    "status": "online"},
        {"id": "CAM-03", "type": "CH3",  "label": "Боковая",  "status": "offline"}
      ],
      "camerasSummary": "CAM-03 offline",
      "camerasStatus": "error",
      "driversInPeriod": [
        {"name": "Сидоров В.Н.", "trips": 4, "isPrimary": true}
      ],
      "lastViolations": [],
      "lat": 55.739, "lng": 37.589
    },
    {
      "rank": 4,
      "vehicleId": "Н124УУ 199",
      "model": "DAF XF",
      "riskScore": 81,
      "totalCount": 3,
      "grossCount": 0,
      "vaCount": 0,
      "telCount": 3,
      "mileageKm": 698,
      "tripsCount": 5,
      "driveTimeMin": 660,
      "cameras": [
        {"id": "CAM-01", "type": "ADAS", "label": "Передняя", "status": "online"},
        {"id": "CAM-02", "type": "DMS",  "label": "Салон",    "status": "online"},
        {"id": "CAM-03", "type": "CH3",  "label": "Боковая",  "status": "online"}
      ],
      "camerasSummary": "3/3 работают",
      "camerasStatus": "ok",
      "driversInPeriod": [
        {"name": "Козлов И.А.", "trips": 4, "isPrimary": true},
        {"name": "Иванов А.П.", "trips": 1, "isPrimary": false, "date": "14.05"}
      ],
      "lastViolations": [],
      "lat": 55.755, "lng": 37.622
    },
    {
      "rank": 5,
      "vehicleId": "М213ОО 77",
      "model": "Kamaz 5490",
      "riskScore": 84,
      "totalCount": 3,
      "grossCount": 0,
      "vaCount": 1,
      "telCount": 2,
      "mileageKm": 509,
      "tripsCount": 3,
      "driveTimeMin": 420,
      "cameras": [
        {"id": "CAM-01", "type": "ADAS", "label": "Передняя", "status": "online"},
        {"id": "CAM-02", "type": "DMS",  "label": "Салон",    "status": "warning"},
        {"id": "CAM-03", "type": "CH3",  "label": "Боковая",  "status": "online"}
      ],
      "camerasSummary": "2/3 работают",
      "camerasStatus": "warning",
      "driversInPeriod": [
        {"name": "Степанов Д.В.", "trips": 3, "isPrimary": true}
      ],
      "lastViolations": [],
      "lat": 55.741, "lng": 37.598
    }
  ]
}
```

**Ключевая бизнес-логика:**
- ТС = актив компании. Один водитель ≠ один автомобиль.
- На А777ВВ 77 за период ездили два водителя: Иванов (4 рейса) и Козлов (1 рейс).
- Нарушения считаются за ТС, но с привязкой к водителю в момент события.
- Статус камер критичен: CAM-03 offline у Е902СТ 150 — часть нарушений могла не записаться.
- Роли: логисты смотрят «По ТС», служба безопасности — «По водителям».


**Check:**
```bash
npx tsc --noEmit
# Нет ошибок по типам ParsedQuery, FleetDriver, FleetVehicle
```
