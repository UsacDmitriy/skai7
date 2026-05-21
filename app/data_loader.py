from __future__ import annotations

"""Модуль загрузки CSV и сохранения действий диспетчера."""

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


@st.cache_data
def load_csv_files(data_dir: Path) -> dict[str, pd.DataFrame]:
    """Читает все CSV из data_dir. Возвращает {имя_файла: DataFrame}."""
    data_dir.mkdir(parents=True, exist_ok=True)
    datasets: dict[str, pd.DataFrame] = {}

    for path in sorted(data_dir.rglob("*.csv")):
        key = path.relative_to(data_dir).as_posix()
        if key.endswith(".csv"):
            key = key[:-4]
        try:
            datasets[key] = pd.read_csv(path)
        except Exception as e:
            st.warning(f"Ошибка загрузки {key}: {e}")

    return datasets


def save_action(output_dir: Path, row_id: str, action: str, comment: str = "") -> None:
    """Сохраняет действие в output/actions.csv."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "actions.csv"

    record = pd.DataFrame([{
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "row_id": row_id,
        "action": action,
        "comment": comment,
    }])

    record.to_csv(path, mode="a", header=not path.exists(), index=False)


def load_or_mock(data_dir: Path) -> dict[str, pd.DataFrame]:
    """Загружает CSV или возвращает мок-данные."""
    datasets = load_csv_files(data_dir)

    if not datasets:
        try:
            from data.mock.incidents import INCIDENTS
            from data.mock.vehicles import VEHICLES

            incidents_df = pd.DataFrame(INCIDENTS)
            vehicles_df = pd.DataFrame(VEHICLES)

            datasets = {
                "selected_video_alarms": incidents_df.rename(columns={
                    "alarm_type": "Type",
                    "speed_kmh": "Speed",
                    "ts": "Begin",
                    "vehicle_plate": "UnitStateNumber",
                    "driver": "UnitName",
                    "lat": "Latitude",
                    "lon": "Longitude",
                }),
                "video_files": pd.DataFrame([{
                    "alarm_id": "inc-001",
                    "channel": 1,
                    "media_relative_path": "datasets/media/video_events/cam1.mp4",
                    "duration_seconds": 45.0,
                }]),
                "vehicles": vehicles_df.rename(columns={
                    "plate": "unit_state_number",
                }),
                "track_points": pd.DataFrame(),
                "max_speed_points": pd.DataFrame(),
            }
        except ImportError:
            pass

    return datasets


__all__ = ["load_csv_files", "save_action", "load_or_mock"]