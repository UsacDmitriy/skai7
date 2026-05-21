# Волна 00a-D — Python-сэмплы для тестов
> 🤖 **Модель: `qwen/qwen3-coder:free`** | чтение CSV, генерация Python
> 💰 **Бюджет:** прочитать первые строки CSV (~5K токенов) | $0
> ⚠️ Результат → `sample_data/` (3 .py файла)

## Зачем

Для тестов и прототипа фронтенда нужны реальные сэмплы данных в виде Python-структур.
Полные CSV (до 6636 строк track_points, 22 машины, 55 алармов) нельзя грузить в контекст.
Нужно создать 3 Python-модуля с 3–50 строками реальных данных, готовых к `from sample_data.sample_alarms import sample_alarms`.

## Промпт

Ты — Python-скриптер. Твоя задача: прочитать ПЕРВЫЕ строки реальных CSV и создать 3 Python-файла с сэмплами.

### Шаг 1 — Прочитай CSV (только первые строки)

Прочитай ТОЛЬКО первые строки этих файлов (НЕ весь CSV, используй `head` или читай построчно с остановкой):

| Файл | Сколько строк прочитать |
|---|---|
| `data/selected_video_alarms.csv` | первые 10 строк (всего их ~55) |
| `data/track_points.csv` | первые 60 строк (всего ~6636) |
| `data/vehicles.csv` | первые 10 строк (всего их ~22) |

### Шаг 2 — Создай директорию

```bash
mkdir -p sample_data
```

### Шаг 3 — Создай 3 Python-файла

#### 3.1. `sample_data/sample_alarms.py`

Возьми 3–5 **разных** алармов из `selected_video_alarms.csv` (разные машины, разные типы событий).

CSV → поля Python (snake_case, оригинальные имена колонок):

| Колонка CSV | Поле Python | Тип |
|---|---|---|
| `AlarmId` | `alarm_id` | `str` |
| `UnitStateNumber` | `unit_state_number` | `str` |
| `UnitName` | `unit_name` | `str` |
| `Type` | `event_type` | `str` |
| `Begin` | `event_begin_utc` | `str` (ISO) |
| `Speed` | `speed` | `float` |
| `Address` | `address` | `str` (пустая → `""`) |
| `Latitude` | `latitude` | `float` (пустая → `None`) |
| `Longitude` | `longitude` | `float` (пустая → `None`) |
| `VideoCount` | `video_count` | `int` |
| `CameraIds` | `camera_ids` | `list[int]` — распарсить JSON-строку `"[1, 2]"` |
| `RequestedCameraIds` | `requested_camera_ids` | `list[int]` |

Формат файла:

```python
"""Sample alarms from selected_video_alarms.csv — 3-5 real rows."""

__all__ = ["sample_alarms"]

sample_alarms = [
    {
        "alarm_id": "7dc1110a-8f27-4cac-9d68-b6b602f346ca",
        "unit_state_number": "Т780РН198",
        "unit_name": "Т 780 РН 198  15133",
        "event_type": "Distraction",
        "event_begin_utc": "2026-05-14T20:42:21Z",
        "speed": 32.0,
        "address": "",
        "latitude": None,
        "longitude": None,
        "video_count": 3,
        "camera_ids": [1, 2],
        "requested_camera_ids": [1, 2, 3],
    },
    # ... ещё 2–4 записи (НЕ выдумывай — бери из CSV)
]
```

#### 3.2. `sample_data/sample_track.py`

Возьми **один** alarm_id и собери 30–50 его трек-поинтов из `track_points.csv`.
Выбери аларм, у которого есть точки в данных (например `03012ab5-5dcd-4f30-bbfa-5ce12499e4ea` для M477YM790 или `05977363-5b3f-4bd0-8a62-401d7a84be17` для В224ВВ125).

CSV → поля Python:

| Колонка CSV | Поле Python | Тип |
|---|---|---|
| `alarm_id` | `alarm_id` | `str` |
| `timestamp_utc` | `timestamp_utc` | `str` (ISO) |
| `latitude` | `latitude` | `float` |
| `longitude` | `longitude` | `float` |
| `speed_kmh` | `speed_kmh` | `float` |
| `angle` | `angle` | `float` |
| `course` | `course` | `float` |
| `period_type` | `period_type` | `str` — значение как в CSV: `"1"`, `"2"` или `"3"` |
| `period_index` | `period_index` | `int` |
| `point_index` | `point_index` | `int` |
| `unit_state_number` | `unit_state_number` | `str` |
| `event_type` | `event_type` | `str` |
| `ew` | `ew` | `bool` — `True`/`False` из CSV |

Формат файла:

```python
"""Sample track points from track_points.csv — 30-50 points for one alarm."""

__all__ = ["sample_track_points"]

sample_track_points = [
    {
        "alarm_id": "03012ab5-5dcd-4f30-bbfa-5ce12499e4ea",
        "unit_state_number": "M477YM790",
        "event_type": "Yawning",
        "timestamp_utc": "2026-05-14T23:45:10+00:00",
        "latitude": 55.705531,
        "longitude": 37.764176,
        "speed_kmh": 6.0,
        "angle": 0.0,
        "course": 101.40243189677648,
        "period_type": "3",
        "period_index": 0,
        "point_index": 0,
        "ew": False,
    },
    # ... ещё 29–49 точек (реальные, из CSV)
]
```

#### 3.3. `sample_data/sample_vehicles.py`

Возьми 5–7 машин из `vehicles.csv` (разные по alarm_count: от 1 до 6).

CSV → поля Python:

| Колонка CSV | Поле Python | Тип |
|---|---|---|
| `dataset_vehicle_code` | `dataset_vehicle_code` | `str` |
| `unit_id` | `unit_id` | `str` |
| `unit_name` | `unit_name` | `str` |
| `unit_state_number` | `unit_state_number` | `str` |
| `alarm_count` | `alarm_count` | `int` |
| `alarm_types` | `alarm_types` | `str` — как в CSV: `"Drowsiness\|Yawning"` (с `\|`) |
| `video_metadata_count` | `video_metadata_count` | `int` |
| `downloaded_video_count` | `downloaded_video_count` | `int` |
| `track_window_count` | `track_window_count` | `int` |
| `track_point_count` | `track_point_count` | `int` |
| `total_track_mileage_km` | `total_track_mileage_km` | `float` |
| `downloaded_video_bytes` | `downloaded_video_bytes` | `int` |
| `downloaded_video_duration_seconds` | `downloaded_video_duration_seconds` | `float` |

Формат файла:

```python
"""Sample vehicles from vehicles.csv — 5-7 real rows."""

__all__ = ["sample_vehicles"]

sample_vehicles = [
    {
        "dataset_vehicle_code": "A079AM250",
        "unit_id": "879edff3-be37-478e-a665-8c674a8661b4",
        "unit_name": "A079AM250",
        "unit_state_number": "A079AM250",
        "alarm_count": 3,
        "alarm_types": "DangerousDistance|SeatBelt|Yawning",
        "video_metadata_count": 9,
        "downloaded_video_count": 9,
        "track_window_count": 3,
        "track_point_count": 290,
        "total_track_mileage_km": 31.893058792670857,
        "downloaded_video_bytes": 5921013,
        "downloaded_video_duration_seconds": 96.60000000000001,
    },
    # ... ещё 4–6 машин (НЕ выдумывай — бери из CSV)
]
```

## Правила

1. **НЕ выдумывай данные** — бери реальные строки из CSV. Если поле пустое — ставь `None` или `""` по типу.
2. **Имена полей snake_case** — как в заголовках CSV (не camelCase, не PascalCase).
3. **Используй Python-синтаксис** — никакого TypeScript, никаких `interface`.
4. **`__all__` обязателен** — в каждом файле должна быть строка `__all__ = ["..."]`.
5. **Парси JSON-строки** — `CameraIds` и `RequestedCameraIds` хранятся как JSON-массивы в CSV (например `"[1, 2]"`). В Python должен быть настоящий `list[int]`.
6. **Создай `sample_data/`** — если директории нет, создай её перед записью файлов.
7. **НЕ читай CSV целиком** — только первые N строк. Используй `head -N` или `csv.reader` с `break`.

## Приёмка

- [ ] `python3 -c "from sample_data.sample_alarms import sample_alarms; print(len(sample_alarms))"` → 3–5
- [ ] `python3 -c "from sample_data.sample_track import sample_track_points; print(len(sample_track_points))"` → 30–50
- [ ] `python3 -c "from sample_data.sample_vehicles import sample_vehicles; print(len(sample_vehicles))"` → 5–7
- [ ] Все `camera_ids` и `requested_camera_ids` — настоящие `list[int]`, не строки
- [ ] Все `latitude`/`longitude` — `float` или `None`, не строки
- [ ] Нет выдуманных данных — все значения из CSV
