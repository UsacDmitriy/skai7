# Волна 00a-B — Data Contract (Python dataclasses)
> 🤖 **Модель: `moonshotai/kimi-k2.6`** | датаклассы на основе реальных CSV-колонок
> 💰 **Контекст: заголовки CSV + 2-3 строки данных** (~3K токенов, ~$0.04)
> ⚠️ Запускать после 00a-A. Результат → `app/models.py`

## Что передать в сессию

Вставить текстом (именно в таком порядке):

### 1. Заголовки CSV-файлов (обязательно)

```
=== selected_video_alarms.csv ===
dataset_vehicle_code,AlarmId,TelemetryId,TerminalId,UnitId,UnitName,UnitStateNumber,Begin,End,Type,Speed,Address,VideoCount,VideoSizeBytes,CameraIds,RequestedCameraIds,Latitude,Longitude

=== video_files.csv ===
dataset_vehicle_code,alarm_id,telemetry_id,video_file_id,channel,created_at_utc,event_type,event_begin_utc,event_end_utc,unit_id,unit_name,unit_state_number,expected_size_from_alarm_bytes,download_endpoint_attempted,local_path,download_status,size_bytes,download_http_status,content_type,server_filename,media_filename,media_relative_path,duration_seconds,video_width,video_height,video_codec

=== track_points.csv ===
alarm_id,dataset_vehicle_code,unit_id,unit_state_number,event_type,event_begin_utc,period_index,period_type,point_index,timestamp_utc,latitude,longitude,speed_kmh,angle,course,ew

=== track_summary.csv ===
alarm_id,dataset_vehicle_code,unit_id,unit_name,unit_state_number,event_type,event_begin_utc,event_end_utc,total_parking_duration,total_movement_duration,total_mileage_km,movement_mileage_km,movement_distance_navigation_km,break_distance_navigation_km,distance_odometer_km,track_period_count,track_point_count,max_speed_point_count,raw_track_path

=== vehicles.csv ===
dataset_vehicle_code,unit_id,unit_name,unit_state_number,alarm_count,alarm_types,video_metadata_count,downloaded_video_count,track_window_count,track_point_count,total_track_mileage_km,downloaded_video_bytes,downloaded_video_duration_seconds
```

### 2. Примеры строк (2 на файл — для понимания типов данных)

```
=== selected_video_alarms.csv (первые 2 строки) ===
T780RN198,7dc1110a-8f27-4cac-9d68-b6b602f346ca,3b389090-78b4-4d9b-89c3-e5e5b1740593,f85c73b1-81d2-4f41-9bd6-d8deea54d862,0cfa33e2-7331-49d2-8ed6-fe5b58ba699c,Т 780 РН 198  15133,Т780РН198,2026-05-14T20:42:21Z,2026-05-14T20:42:29Z,Distraction,32.0,,3,1044707,"[1, 2]","[1, 2, 3]",,
M477YM790,f3c9d4ee-9948-45aa-90ad-75d75b7bb13f,6c80138e-5be4-42aa-a450-61433847b632,,,M477YM790,M477YM790,2026-05-14T21:50:04Z,2026-05-14T21:50:13Z,SeatBelt,16.0,,1,413647,"[2]","[1, 2, 3]",,

=== video_files.csv (первые 2 строки) ===
M477YM790,03012ab5-5dcd-4f30-bbfa-5ce12499e4ea,a0eef84a-8f2a-42da-89ea-b54702e6e37a,e3ee071d-ccdc-49b7-a307-4c9ca8df1b8f,3,2026-05-14T23:37:50.481808Z,Yawning,2026-05-14T23:37:22Z,2026-05-14T23:37:32Z,b5f05f9a-b7b9-442c-bccf-a86469c499f1,M477YM790,M477YM790,2095419,GET https://vasign.skai.online/media-files/data/{video_file_id},datasets/media/video_events/M477YM790__202605142337__Yawning__alarm_03012ab5__ch3__e3ee071d-ccdc-49b7-a307-4c9ca8df1b8f.mp4,downloaded,859313,200,video/mp4,,M477YM790__202605142337__Yawning__alarm_03012ab5__ch3__e3ee071d-ccdc-49b7-a307-4c9ca8df1b8f.mp4,datasets/media/video_events/M477YM790__202605142337__Yawning__alarm_03012ab5__ch3__e3ee071d-ccdc-49b7-a307-4c9ca8df1b8f.mp4,10.075,288,352,h264
M477YM790,03012ab5-5dcd-4f30-bbfa-5ce12499e4ea,a0eef84a-8f2a-42da-89ea-b54702e6e37a,68803941-fd41-4d84-90a1-a2bcee5fc8c7,1,2026-05-14T23:37:44.307592Z,Yawning,2026-05-14T23:37:22Z,2026-05-14T23:37:32Z,b5f05f9a-b7b9-442c-bccf-a86469c499f1,M477YM790,M477YM790,2095419,GET https://vasign.skai.online/media-files/data/{video_file_id},datasets/media/video_events/M477YM790__202605142337__Yawning__alarm_03012ab5__ch1__68803941-fd41-4d84-90a1-a2bcee5fc8c7.mp4,downloaded,731733,200,video/mp4,,M477YM790__202605142337__Yawning__alarm_03012ab5__ch1__68803941-fd41-4d84-90a1-a2bcee5fc8c7.mp4,datasets/media/video_events/M477YM790__202605142337__Yawning__alarm_03012ab5__ch1__68803941-fd41-4d84-90a1-a2bcee5fc8c7.mp4,12.079,352,288,h264

=== track_points.csv (первые 2 строки) ===
03012ab5-5dcd-4f30-bbfa-5ce12499e4ea,M477YM790,b5f05f9a-b7b9-442c-bccf-a86469c499f1,M477YM790,Yawning,2026-05-14T23:37:22Z,0,3,0,2026-05-14T23:45:10+00:00,55.705531,37.764176,6.0,0.0,101.40243189677648,False
03012ab5-5dcd-4f30-bbfa-5ce12499e4ea,M477YM790,b5f05f9a-b7b9-442c-bccf-a86469c499f1,M477YM790,Yawning,2026-05-14T23:37:22Z,1,2,0,2026-05-14T23:45:10+00:00,55.705531,37.764176,6.0,96.48307369481758,101.40243189677648,False

=== track_summary.csv (первые 2 строки) ===
03012ab5-5dcd-4f30-bbfa-5ce12499e4ea,M477YM790,b5f05f9a-b7b9-442c-bccf-a86469c499f1,M477YM790,M477YM790,Yawning,2026-05-14T23:37:22Z,2026-05-14T23:37:32Z,00:00:15,00:07:07,8.31459651367194,5.43405059364947,5.43405059364947,2.8692844747296977,0.0,3,35,1,datasets/raw/video_events/tracks/03012ab5-5dcd-4f30-bbfa-5ce12499e4ea.json
05977363-5b3f-4bd0-8a62-401d7a84be17,V224BB125,35465f3f-e01b-4f1b-a750-39a40af5bdff,В224ВВ125,В224ВВ125,SeatBelt,2026-05-14T21:14:34Z,2026-05-14T21:16:06Z,00:10:41,00:20:51,7.46338472524222,7.446452627415349,7.446452627415349,0.0,0.0,3,83,2,datasets/raw/video_events/tracks/05977363-5b3f-4bd0-8a62-401d7a84be17.json

=== vehicles.csv (первые 2 строки) ===
A079AM250,879edff3-be37-478e-a665-8c674a8661b4,A079AM250,A079AM250,3,DangerousDistance|SeatBelt|Yawning,9,9,3,290,31.893058792670857,5921013,96.60000000000001
K279HM154,2d9e6091-b3d5-49f6-ad23-21e0101909fa,К279ХМ154,К279ХМ154,2,Drowsiness,2,2,2,103,39.5780939997384,2993696,22.151
```

### 3. Примеры из существующего кода проекта (для стиля)

```python
# app/app.py — используется from __future__ import annotations, Optional в других файлах проекта
from __future__ import annotations
import pandas as pd
from pathlib import Path

# app/metrics.py — возвращает dict для метрик дашборда
def build_dashboard_metrics(datasets: dict[str, pd.DataFrame]) -> list[dict[str, str]]:
    ...
    return [{"label": "Events", "value": "42", "delta": "+3"}, ...]
```

---

## Промпт

```
Перед тобой реальные CSV-файлы проекта SKAI Hackathon MVP (телематика + видео в одном окне).

Задача: написать `app/models.py` — полный файл Python-датаклассов для модели данных.

Правила:
1. Использовать `from __future__ import annotations` первой строкой.
2. Использовать `@dataclass` для каждого класса. Никаких TypeScript — только Python.
3. Поля брать ТОЛЬКО из реальных CSV-колонок, которые видны в заголовках выше. Не выдумывать лишних полей.
4. Для nullable-полей использовать `Optional[str]` (например, `speed: float | None`, `address: str | None`, `latitude: float | None`).
5. Добавить type alias:
   - `ActionType = Literal["mark_reviewed", "create_task", "export_report"]`
   - `Datasets = dict[str, pd.DataFrame]`
6. Каждый dataclass — с JSDoc-стиль docstring (одна строка, что описывает эта сущность).
7. Добавить `__all__` — список всех экспортируемых имён.
8. Порядок классов в файле:

   **Alarm** — из selected_video_alarms.csv:
   - alarm_id: str
   - unit_state_number: str
   - unit_name: str
   - event_type: str (значения: Drowsiness, Distraction, Overspeeding, HarshBraking, HarshAcceleration, SharpAcceleration, SharpTurn, SeatBelt, Yawning, Smoking, Phone, DangerousDistance, DriverSubstitution, etc.)
   - event_begin_utc: str
   - event_end_utc: str
   - speed: float | None
   - latitude: float | None
   - longitude: float | None
   - video_count: int
   - video_size_bytes: int
   - camera_ids: str
   - address: str | None

   **VideoFile** — из video_files.csv:
   - alarm_id: str
   - video_file_id: str
   - channel: int
   - media_relative_path: str
   - duration_seconds: float
   - video_width: int
   - video_height: int
   - video_codec: str
   - download_status: str
   - size_bytes: int

   **TrackPoint** — из track_points.csv:
   - alarm_id: str
   - timestamp_utc: str
   - latitude: float
   - longitude: float
   - speed_kmh: float
   - angle: float
   - course: float
   - period_type: str
   - point_index: int

   **TrackSummary** — из track_summary.csv:
   - alarm_id: str
   - unit_state_number: str
   - event_type: str
   - total_mileage_km: float
   - total_movement_duration: str
   - track_point_count: int
   - max_speed_point_count: int

   **Vehicle** — из vehicles.csv:
   - unit_state_number: str
   - unit_name: str
   - alarm_count: int
   - alarm_types: str (значения разделены | например "Drowsiness|SeatBelt")
   - downloaded_video_count: int
   - track_point_count: int
   - total_track_mileage_km: float

   **DashboardMetric** — вычисляемая метрика для UI, не из CSV:
   - label: str
   - value: str
   - delta: str | None

   **Action** — действие диспетчера, записывается в output/actions.csv:
   - created_at: str
   - row_id: str
   - action: ActionType
   - comment: str

9. Сохранить результат в `app/models.py`.

Только код файла app/models.py. Без объяснений.
```
