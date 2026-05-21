# 01A · models.py
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 1

**Файл:** `app/models.py`
**Только этот файл.**

Поля должны совпадать с CSV-колонками из `data/`: `selected_video_alarms.csv`, `video_files.csv`, `track_points.csv`, `track_summary.csv`, `vehicles.csv`.

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

import pandas as pd

# Type aliases
ActionType = Literal["mark_reviewed", "create_task", "export_report"]
Datasets = dict[str, pd.DataFrame]

@dataclass
class Alarm:
    """Событие видеоаналитики — одна строка из selected_video_alarms.csv."""
    alarm_id: str
    unit_state_number: str
    unit_name: str
    event_type: str
    event_begin_utc: str
    event_end_utc: str
    speed: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    video_count: int = 0
    video_size_bytes: int = 0
    camera_ids: str = ""
    address: Optional[str] = None
    telemetry_id: str = ""
    terminal_id: str = ""
    unit_id: str = ""

@dataclass
class VideoFile:
    """Видеофайл — одна строка из video_files.csv."""
    alarm_id: str
    video_file_id: str
    channel: int
    media_relative_path: str
    duration_seconds: float = 0.0
    video_width: int = 0
    video_height: int = 0
    video_codec: str = ""
    download_status: str = ""
    size_bytes: int = 0

@dataclass
class TrackPoint:
    """Точка трека — одна строка из track_points.csv."""
    alarm_id: str
    timestamp_utc: str
    latitude: float
    longitude: float
    speed_kmh: float
    angle: float = 0.0
    course: str = ""
    period_type: str = ""
    point_index: int = 0
    unit_state_number: str = ""

@dataclass
class TrackSummary:
    """Сводка трека — одна строка из track_summary.csv."""
    alarm_id: str
    unit_state_number: str
    event_type: str
    total_mileage_km: float = 0.0
    total_movement_duration: str = ""
    track_point_count: int = 0
    max_speed_point_count: int = 0

@dataclass
class Vehicle:
    """Сводка по ТС — одна строка из vehicles.csv."""
    unit_state_number: str
    unit_name: str
    alarm_count: int = 0
    alarm_types: str = ""
    downloaded_video_count: int = 0
    track_point_count: int = 0
    total_track_mileage_km: float = 0.0

@dataclass
class DashboardMetric:
    """Одна KPI-метрика для дашборда."""
    label: str
    value: str
    delta: Optional[str] = None

@dataclass
class Action:
    """Запись действия диспетчера."""
    created_at: str
    row_id: str
    action: ActionType
    comment: str = ""

__all__ = [
    "Alarm",
    "VideoFile",
    "TrackPoint",
    "TrackSummary",
    "Vehicle",
    "DashboardMetric",
    "Action",
    "ActionType",
    "Datasets",
]
```

**Check:** `python -c "from app.models import Alarm, VideoFile, TrackPoint, TrackSummary, Vehicle"` без ошибок. Поля совпадают с CSV-колонками из `data/`.
