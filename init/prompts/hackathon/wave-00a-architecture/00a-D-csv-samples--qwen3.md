# Волна 00a-D — CSV-сэмплы для фронта
> 🤖 **Модель: `qwen/qwen3-coder:free`** | обработка CSV
> 💰 **Бюджет:** прочитать только первые строки CSV (~2K токенов) | $0
> ⚠️ Результат → code/frontend/src/data/

## Зачем

Фронтенду нужны сэмплы данных для разработки. Полные CSV (959k строк) нельзя грузить в браузер.
Нужно создать маленькие JSON-файлы с 5-50 строками реальных данных.

## Промпт

Прочитай ТОЛЬКО первые строки этих файлов (НЕ весь CSV):
  datasets/ready/video_events/selected_video_alarms.csv (первые 10 строк)
  datasets/ready/video_events/video_files.csv (первые 10 строк)
  datasets/ready/navigation_problem_tracks/track_points.csv (первые 50 строк)
  datasets/ready/sensor_diagnostics/sensor_graph_points.csv (первые 30 строк)

Создай 3 файла в code/frontend/src/data/:

### 1. code/frontend/src/data/videoAlarms.ts
```ts
// Сэмпл из selected_video_alarms.csv + video_files.csv (объединённые)
export interface VideoAlarmSample {
  alarmId: string
  vehicleCode: string
  type: string           // из CSV: Type
  begin: string          // из CSV: Begin
  end: string            // из CSV: End
  speed: number          // из CSV: Speed
  address: string        // из CSV: Address
  videoCount: number     // из CSV: VideoCount
  cameraIds: number[]    // из CSV: CameraIds
  videos: {
    channel: number
    durationSec: number
    path: string         // media_relative_path
  }[]
}

export const videoAlarmsSample: VideoAlarmSample[] = [
  // 5-10 реальных строк из CSV
]
```

### 2. code/frontend/src/data/trackPoints.ts
```ts
// Сэмпл из track_points.csv
export interface TrackPointSample {
  vehicleId: string
  date: string
  timestamp: string
  latitude: number
  longitude: number
  speedKmh: number
}

export const trackPointsSample: TrackPointSample[] = [
  // 50 реальных точек трека
]
```

### 3. code/frontend/src/data/sensorSample.ts
```ts
// Сэмпл из sensor_graph_points.csv
export interface SensorSample {
  vehicleId: string
  date: string
  sensorId: string
  sensorName: string
  sensorGroup: string
  timestampUtc: string
  value: number
}

export const sensorSamples: SensorSample[] = [
  // 30 реальных точек для одного датчика
]
```

ВАЖНО:
- Имена полей в TypeScript = camelCase (vehicleId), в CSV = snake_case (vehicle_id)
- НЕ выдумывай данные — бери реальные строки из CSV
- Если CSV недоступен — создай заглушку с комментарием "// REAL DATA PENDING"
