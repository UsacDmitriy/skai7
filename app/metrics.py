from __future__ import annotations

import pandas as pd

__all__ = [
    "build_dashboard_metrics",
    "build_risk_table",
    "get_alarm_details",
    "get_alarm_types_distribution",
]


def build_dashboard_metrics(datasets: dict[str, pd.DataFrame]) -> list[dict[str, str]]:
    alarms_df = datasets.get("selected_video_alarms")
    vehicles_df = datasets.get("vehicles")
    video_files_df = datasets.get("video_files")

    total_alarms = len(alarms_df) if alarms_df is not None else 0
    total_vehicles = (
        len(vehicles_df)
        if vehicles_df is not None
        else (alarms_df["UnitStateNumber"].nunique() if alarms_df is not None else 0)
    )
    total_videos = len(video_files_df) if video_files_df is not None else 0
    avg_speed = round(float(alarms_df["Speed"].mean()), 1) if alarms_df is not None else 0
    max_speed = float(alarms_df["Speed"].max()) if alarms_df is not None else 0
    alarm_types = int(alarms_df["Type"].nunique()) if alarms_df is not None else 0

    return [
        {"label": "Всего алармов", "value": str(total_alarms)},
        {"label": "Всего машин", "value": str(total_vehicles)},
        {"label": "Всего видеофайлов", "value": str(total_videos)},
        {"label": "Средняя скорость (км/ч)", "value": str(avg_speed)},
        {"label": "Макс. скорость (км/ч)", "value": str(max_speed)},
        {"label": "Типов алармов", "value": str(alarm_types)},
    ]


def build_risk_table(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    alarms_df = datasets.get("selected_video_alarms")
    if alarms_df is None:
        return pd.DataFrame()

    risk_cols = [
        "AlarmId",
        "UnitStateNumber",
        "Type",
        "Speed",
        "Begin",
        "Address",
        "VideoCount",
    ]
    available_cols = [col for col in risk_cols if col in alarms_df.columns]
    if not available_cols:
        return pd.DataFrame()

    result = alarms_df.sort_values("Speed", ascending=False).head(20)
    return result[available_cols].reset_index(drop=True)


def get_alarm_details(datasets: dict[str, pd.DataFrame], alarm_id: str) -> dict:
    alarms_df = datasets.get("selected_video_alarms")
    video_files_df = datasets.get("video_files")
    track_points_df = datasets.get("track_points")
    track_summary_df = datasets.get("track_summary")
    max_speed_points_df = datasets.get("max_speed_points")
    vehicles_df = datasets.get("vehicles")

    alarm_row = None
    vehicle = None
    if alarms_df is not None:
        mask = alarms_df["AlarmId"] == alarm_id
        if mask.any():
            alarm_row = alarms_df[mask].iloc[0]
            unit_sn = alarm_row.get("UnitStateNumber")
            if unit_sn is not None and vehicles_df is not None:
                vmask = vehicles_df["unit_state_number"] == unit_sn
                if vmask.any():
                    vehicle = vehicles_df[vmask].iloc[0]

    videos = pd.DataFrame()
    if video_files_df is not None:
        videos = video_files_df[video_files_df["alarm_id"] == alarm_id].reset_index(drop=True)

    track_points = pd.DataFrame()
    if track_points_df is not None:
        tp = track_points_df[track_points_df["alarm_id"] == alarm_id]
        if not tp.empty and "timestamp_utc" in tp.columns:
            tp = tp.sort_values("timestamp_utc").head(200)
        track_points = tp.reset_index(drop=True)

    track_summary = None
    if track_summary_df is not None:
        tsmask = track_summary_df["alarm_id"] == alarm_id
        if tsmask.any():
            track_summary = track_summary_df[tsmask].iloc[0]

    max_speed_points = pd.DataFrame()
    if max_speed_points_df is not None:
        max_speed_points = max_speed_points_df[
            max_speed_points_df["alarm_id"] == alarm_id
        ].reset_index(drop=True)

    return {
        "alarm_row": alarm_row,
        "videos": videos,
        "track_points": track_points,
        "track_summary": track_summary,
        "max_speed_points": max_speed_points,
        "vehicle": vehicle,
    }


def get_alarm_types_distribution(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    alarms_df = datasets.get("selected_video_alarms")
    if alarms_df is None or "Type" not in alarms_df.columns:
        return pd.DataFrame(columns=["Type", "Count"])

    dist = alarms_df["Type"].value_counts().reset_index()
    dist.columns = ["Type", "Count"]
    return dist
