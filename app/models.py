"""Модели данных для SKAI Hackathon MVP — dataclass-описания CSV-структур."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

import pandas as pd

# --- Type aliases ---
ActionType = Literal["mark_reviewed", "create_task", "export_report"]
Datasets = dict[str, pd.DataFrame]


@dataclass
class Alarm:
    """Событие видеоаналитики — строка из selected_video_alarms.csv."""
    alarm_id: str
    dataset_vehicle_code: str = ""
    telemetry_id: str = ""
    terminal_id: str = ""
    unit_id: str = ""
    unit_name: str = ""
    unit_state_number: str = ""
    event_begin: str = ""
    event_end: str = ""
    event_type: str = ""
    speed: Optional[float] = None
    address: Optional[str] = None
    video_count: int = 0
    video_size_bytes: int = 0
    camera_ids: str = ""
    requested_camera_ids: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@dataclass
class VideoFile:
    """Видеофайл — строка из video_files.csv."""
    alarm_id: str
    video_file_id: str = ""
    channel: int = 0
    media_relative_path: str = ""
    duration_seconds: float = 0.0
    video_width: int = 0
    video_height: int = 0
    video_codec: str = ""
    download_status: str = ""
    size_bytes: int = 0
    created_at_utc: str = ""
    event_type: str = ""
    event_begin_utc: str = ""
    event_end_utc: str = ""
    unit_id: str = ""
    unit_name: str = ""
    unit_state_number: str = ""


@dataclass
class TrackPoint:
    """Точка трека — строка из track_points.csv."""
    alarm_id: str
    timestamp_utc: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    speed_kmh: float = 0.0
    angle: float = 0.0
    course: str = ""
    ew: str = ""
    period_type: str = ""
    point_index: int = 0
    dataset_vehicle_code: str = ""
    unit_id: str = ""
    unit_state_number: str = ""
    event_type: str = ""


@dataclass
class TrackSummary:
    """Сводка трека — строка из track_summary.csv."""
    alarm_id: str
    dataset_vehicle_code: str = ""
    unit_id: str = ""
    unit_name: str = ""
    unit_state_number: str = ""
    event_type: str = ""
    event_begin_utc: str = ""
    event_end_utc: str = ""
    total_parking_duration: str = ""
    total_movement_duration: str = ""
    total_mileage_km: float = 0.0
    movement_mileage_km: float = 0.0
    track_period_count: int = 0
    track_point_count: int = 0
    max_speed_point_count: int = 0
    raw_track_path: str = ""


@dataclass
class Vehicle:
    """Сводка по ТС — строка из vehicles.csv."""
    dataset_vehicle_code: str
    unit_id: str = ""
    unit_name: str = ""
    unit_state_number: str = ""
    alarm_count: int = 0
    alarm_types: str = ""
    video_metadata_count: int = 0
    downloaded_video_count: int = 0
    track_window_count: int = 0
    track_point_count: int = 0
    total_track_mileage_km: float = 0.0
    downloaded_video_bytes: int = 0
    downloaded_video_duration_seconds: float = 0.0


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
