from __future__ import annotations

"""Модуль загрузки CSV и сохранения действий диспетчера."""

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

CITY_COORDS = {
    "москва": (55.7558, 37.6173),
    "санкт-петербург": (59.9343, 30.3351),
    "екатеринбург": (56.8389, 60.6057),
    "уфа": (54.7388, 55.9721),
    "березники": (59.4087, 56.8205),
    "новосибирск": (55.0084, 82.9357),
    "норильск": (69.3558, 88.2027),
    "химки": (55.8897, 37.4497),
    "десногорск": (54.1739, 33.2826),
    "сибирские уралы": (57.1553, 65.5619),
    "невский округ": (59.9343, 30.3351),
}


def _enrich_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """Добавляет моковые координаты на основе городов из Address."""
    result = df.copy()

    has_lat = "latitude" in result.columns or "Latitude" in result.columns
    has_lon = "longitude" in result.columns or "Longitude" in result.columns or "long" in result.columns or "Long" in result.columns

    lat_col = "Latitude" if "Latitude" in result.columns else "latitude"
    lon_col = "Longitude" if "Longitude" in result.columns else "longitude"

    if lat_col not in result.columns:
        result[lat_col] = None
    if lon_col not in result.columns:
        result[lon_col] = None

    import random
    random.seed(42)

    for idx, row in result.iterrows():
        lat_is_empty = pd.isna(row.get(lat_col)) or str(row.get(lat_col, "")).strip() == ""
        lon_is_empty = pd.isna(row.get(lon_col)) or str(row.get(lon_col, "")).strip() == ""

        if lat_is_empty and lon_is_empty and "Address" in row.index:
            address = str(row.get("Address", "")).lower().strip()
            for city, (lat, lon) in CITY_COORDS.items():
                if city in address:
                    jitter_lat = lat + random.uniform(-0.02, 0.02)
                    jitter_lon = lon + random.uniform(-0.02, 0.02)
                    result.at[idx, lat_col] = round(jitter_lat, 6)
                    result.at[idx, lon_col] = round(jitter_lon, 6)
                    break

    still_empty = result[
        (pd.isna(result[lat_col]) | (result[lat_col] == "")) &
        (pd.isna(result[lon_col]) | (result[lon_col] == ""))
    ]

    moscow_lat, moscow_lon = CITY_COORDS["москва"]
    for idx in still_empty.index:
        jitter_lat = moscow_lat + random.uniform(-0.05, 0.05)
        jitter_lon = moscow_lon + random.uniform(-0.05, 0.05)
        result.at[idx, lat_col] = round(jitter_lat, 6)
        result.at[idx, lon_col] = round(jitter_lon, 6)

    return result


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
            df = pd.read_csv(path)
            if "selected_video_alarms" in key:
                df = _enrich_coordinates(df)
            datasets[key] = df
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