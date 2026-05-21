# Промпт 2 — Data Layer (Streamlit)

Задача: настроить слой данных для Streamlit-приложения — **НЕ** FastAPI-сервер, а Python-модули для загрузки CSV, моделей и сохранения действий.

Рабочая директория: `05_video_telematics_single_window/` (или корень проекта, где лежит `app/`).

---

## 1. Пакетная структура

Убедись, что `app/__init__.py` существует (пустой файл), чтобы Python видел пакет.

## 2. Модуль `app/data_loader.py`

Проверь, что модуль содержит две функции:

### `load_csv_files(data_dir: Path) -> dict[str, pd.DataFrame]`

- Рекурсивно обходит `data_dir` и загружает **все** CSV-файлы.
- Ключи словаря — относительные пути от `data_dir` (например, `selected_video_alarms.csv`, `work_rest_single_vehicle/track_points.csv`).
- Значения — соответствующие `pd.DataFrame`.
- Если директория не существует — создаёт её (на случай первого запуска) и возвращает пустой словарь.

### `save_action(output_dir: Path, row_id: str, action: str, comment: str) -> None`

- Дописывает строку в `output_dir / "actions.csv"`.
- Поля: `created_at` (ISO с секундами), `row_id`, `action`, `comment`.
- Создаёт директорию и файл при первом вызове.
- При повторном вызове дописывает без перезаписи заголовка.

## 3. Модуль `app/models.py`

Создай (или проверь) модуль с датаклассами, описывающими предметную область. Используй `dataclasses.dataclass`:

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Alarm:
    alarm_id: str
    vehicle_id: str
    alarm_time: datetime
    alarm_type: str
    speed_kmh: float = 0.0
    latitude: float | None = None
    longitude: float | None = None
    risk_score: int = 0

@dataclass
class VideoFile:
    alarm_id: str
    video_file_id: str
    channel: int
    media_relative_path: str
    file_size_bytes: int = 0
    duration_seconds: float = 0.0

@dataclass
class TrackPoint:
    vehicle_id: str
    timestamp_utc: datetime
    latitude: float
    longitude: float
    speed_kmh: float
    heading: float = 0.0

@dataclass
class TrackSummary:
    vehicle_id: str
    period_start: datetime
    period_end: datetime
    total_distance_km: float = 0.0
    max_speed_kmh: float = 0.0
    avg_speed_kmh: float = 0.0

@dataclass
class Vehicle:
    vehicle_id: str
    plate_number: str = ""
    vehicle_type: str = ""
    brand: str = ""
    model: str = ""

@dataclass
class DashboardMetric:
    label: str
    value: str

@dataclass
class Action:
    created_at: datetime
    row_id: str
    action: str
    comment: str = ""
```

**Важно**: `TrackPoint` и `TrackSummary` — два разных датакласса, не путать с одним `Track`.

## 4. Тест загрузки данных

Запусти из рабочей директории и убедись, что вывод соответствует ожидаемому:

```bash
cd 05_video_telematics_single_window
python -c "
from pathlib import Path
from app.data_loader import load_csv_files
ds = load_csv_files(Path('data'))
print(f'Loaded {len(ds)} datasets, {sum(len(d) for d in ds.values())} total rows')
for name, df in sorted(ds.items()):
    print(f'  {name}: {len(df)} rows x {len(df.columns)} cols')
"
```

**Ожидаемый результат**: 7 датасетов (или больше, если вложенные), 7000+ строк суммарно.

## 5. Тест сохранения действий

```bash
python -c "
from pathlib import Path
from app.data_loader import save_action
save_action(Path('output'), 'test-001', 'mark_reviewed', 'Test comment')
print('Action saved')
"
```

Проверь, что `output/actions.csv` создан и содержит одну строку.

## 6. Чек-лист успешного выполнения

- [ ] `app/__init__.py` существует (пустой)
- [ ] `app/data_loader.py` содержит `load_csv_files()` и `save_action()`
- [ ] `app/models.py` содержит все 7 датаклассов
- [ ] Тест загрузки показывает 7+ датасетов и 7000+ строк
- [ ] Тест сохранения создаёт `output/actions.csv`
- [ ] Импорты внутри `app/` используют относительные пути (`.data_loader`, `.models`, `.constants`)

## Примечания

- **НЕ** используй FastAPI, uvicorn, HTTP-эндпоинты.
- **НЕ** добавляй CORS, роутинг, middleware.
- Весь код — чистые Python-модули без веб-фреймворков.
- Работаем оффлайн: локальные CSV + локальная файловая система.
- Стиль кода: PEP 8, аннотации типов, `from __future__ import annotations`.
