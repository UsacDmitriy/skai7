from __future__ import annotations

__all__ = [
    "build_risk_table",
    "build_vehicle_summary",
    "get_incident_report",
]

"""Модуль риск-таблицы для Details-вкладки Streamlit-приложения SKAI Unified Incident Window."""

import pandas as pd

_ALARM_TYPE_LABELS: dict[str, str] = {
    "Drowsiness": "Засыпание",
    "Overspeeding": "Превышение скорости",
    "HarshBraking": "Резкое торможение",
    "HarshAcceleration": "Резкое ускорение",
    "HarshCornering": "Резкий поворот",
    "PhoneUsage": "Использование телефона",
    "Smoking": "Курение",
    "SeatBelt": "Ремень безопасности",
    "DriverSubstitution": "Подмена водителя",
    "LaneDeparture": "Выезд с полосы",
    "ForwardCollision": "Опасное сближение",
    "Distraction": "Отвлечение",
    "DangerousDistance": "Опасная дистанция",
    "SharpAcceleration": "Резкое ускорение",
    "Sabotage": "Саботаж камеры",
    "Yawning": "Зевание",
}

_SPEED_LIMIT_KMH = 90
_CRITICAL_TYPES = frozenset({"Sabotage", "Drowsiness", "DangerousDistance"})


def _resolve_df(datasets: dict[str, pd.DataFrame], key: str) -> pd.DataFrame | None:
    df = datasets.get(key)
    if df is not None:
        return df
    return datasets.get(f"{key}.csv")


def build_risk_table(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Строит risk-таблицу: top-30 алармов с обогащением из других таблиц."""
    alarms_df = _resolve_df(datasets, "selected_video_alarms")
    if alarms_df is None or alarms_df.empty:
        return pd.DataFrame()

    result = alarms_df.sort_values("Speed", ascending=False).copy()

    result = result.drop(columns=["VideoCount"], errors="ignore")

    video_files_df = _resolve_df(datasets, "video_files")
    if video_files_df is not None and "alarm_id" in video_files_df.columns:
        vc = video_files_df.groupby("alarm_id").size().reset_index(name="VideoCount")
        result = result.merge(vc, left_on="AlarmId", right_on="alarm_id", how="left")
        result["VideoCount"] = result["VideoCount"].fillna(0).astype(int)
        result = result.drop(columns=["alarm_id"], errors="ignore")
    else:
        result["VideoCount"] = 0

    track_points_df = _resolve_df(datasets, "track_points")
    if track_points_df is not None and "alarm_id" in track_points_df.columns:
        tp_agg = (
            track_points_df.groupby("alarm_id")
            .agg(TrackPointCount=("speed_kmh", "count"), MaxSpeedKmh=("speed_kmh", "max"))
            .reset_index()
        )
        result = result.merge(tp_agg, left_on="AlarmId", right_on="alarm_id", how="left")
        result["TrackPointCount"] = result["TrackPointCount"].fillna(0).astype(int)
        result["MaxSpeedKmh"] = result["MaxSpeedKmh"].fillna(0.0)
        result = result.drop(columns=["alarm_id"], errors="ignore")
    else:
        result["TrackPointCount"] = 0
        result["MaxSpeedKmh"] = 0.0

    max_speed_df = _resolve_df(datasets, "max_speed_points")
    if max_speed_df is not None and "alarm_id" in max_speed_df.columns:
        msp = max_speed_df.groupby("alarm_id")["speed_kmh"].max().reset_index()
        msp.columns = ["alarm_id", "msp_max"]
        result = result.merge(msp, left_on="AlarmId", right_on="alarm_id", how="left")
        better = result["msp_max"].notna() & (result["msp_max"] > result["MaxSpeedKmh"])
        result.loc[better, "MaxSpeedKmh"] = result.loc[better, "msp_max"]
        result = result.drop(columns=["alarm_id", "msp_max"], errors="ignore")

    vehicles_df = _resolve_df(datasets, "vehicles")
    if vehicles_df is not None and "unit_state_number" in vehicles_df.columns:
        vdf = vehicles_df[["unit_state_number", "alarm_count"]].rename(
            columns={"alarm_count": "VehicleAlarmCount"}
        )
        result = result.merge(vdf, left_on="UnitStateNumber", right_on="unit_state_number", how="left")
        result["VehicleAlarmCount"] = result["VehicleAlarmCount"].fillna(0).astype(int)
        result = result.drop(columns=["unit_state_number"], errors="ignore")
    else:
        result["VehicleAlarmCount"] = 0

    result["TypeLabel"] = result["Type"].map(_ALARM_TYPE_LABELS).fillna(result["Type"])

    result["IsSpeeding"] = result["Speed"] > _SPEED_LIMIT_KMH
    result["HasVideo"] = result["VideoCount"] > 0
    result["HasTrack"] = result["TrackPointCount"] > 0
    result["IsCritical"] = result["IsSpeeding"] & result["Type"].isin(_CRITICAL_TYPES)

    output_cols = [
        "AlarmId",
        "UnitStateNumber",
        "Type",
        "TypeLabel",
        "Speed",
        "Begin",
        "End",
        "Address",
        "VideoCount",
        "TrackPointCount",
        "MaxSpeedKmh",
        "VehicleAlarmCount",
        "IsSpeeding",
        "HasVideo",
        "HasTrack",
        "IsCritical",
    ]
    return result.head(30)[output_cols].reset_index(drop=True)


def build_vehicle_summary(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Сводка по машинам: госномер, всего алармов, типы, видео, пробег, средняя скорость."""
    vehicles_df = _resolve_df(datasets, "vehicles")
    if vehicles_df is None or vehicles_df.empty:
        return pd.DataFrame()

    result = vehicles_df[
        ["unit_state_number", "alarm_count", "alarm_types", "downloaded_video_count", "total_track_mileage_km"]
    ].copy()
    result.columns = ["UnitStateNumber", "AlarmCount", "AlarmTypes", "VideoCount", "TotalMileageKm"]

    alarms_df = _resolve_df(datasets, "selected_video_alarms")
    if alarms_df is not None and "UnitStateNumber" in alarms_df.columns:
        avg = alarms_df.groupby("UnitStateNumber")["Speed"].mean().reset_index()
        avg.columns = ["UnitStateNumber", "AvgSpeedKmh"]
        result = result.merge(avg, on="UnitStateNumber", how="left")
        result["AvgSpeedKmh"] = result["AvgSpeedKmh"].fillna(0.0).round(1)
    else:
        result["AvgSpeedKmh"] = 0.0

    return result.sort_values("AlarmCount", ascending=False).reset_index(drop=True)


def get_incident_report(datasets: dict[str, pd.DataFrame], alarm_id: str) -> dict:
    """Формирует полный отчёт по инциденту для выбранного alarm_id."""
    alarms_df = _resolve_df(datasets, "selected_video_alarms")
    video_files_df = _resolve_df(datasets, "video_files")
    track_points_df = _resolve_df(datasets, "track_points")
    track_summary_df = _resolve_df(datasets, "track_summary")
    max_speed_df = _resolve_df(datasets, "max_speed_points")
    vehicles_df = _resolve_df(datasets, "vehicles")

    alarm: dict = {}
    if alarms_df is not None and "AlarmId" in alarms_df.columns:
        mask = alarms_df["AlarmId"] == alarm_id
        if mask.any():
            row = alarms_df[mask].iloc[0]
            alarm = {
                "AlarmId": row.get("AlarmId", ""),
                "UnitStateNumber": row.get("UnitStateNumber", ""),
                "Type": row.get("Type", ""),
                "TypeLabel": _ALARM_TYPE_LABELS.get(row.get("Type", ""), row.get("Type", "")),
                "Speed": row.get("Speed", 0),
                "Begin": str(row.get("Begin", "")),
                "End": str(row.get("End", "")),
                "Address": row.get("Address", ""),
                "Latitude": row.get("Latitude", None),
                "Longitude": row.get("Longitude", None),
            }

    videos: list[dict] = []
    if video_files_df is not None and alarm_id in video_files_df.get("alarm_id", pd.Series(dtype=str)).values:
        vdf = video_files_df[video_files_df["alarm_id"] == alarm_id]
        video_cols = ["video_file_id", "channel", "media_relative_path", "duration_seconds"]
        available = [c for c in video_cols if c in vdf.columns]
        videos = vdf[available].to_dict("records")

    track_summary: dict = {}
    if track_summary_df is not None and "alarm_id" in track_summary_df.columns:
        tmask = track_summary_df["alarm_id"] == alarm_id
        if tmask.any():
            ts = track_summary_df[tmask].iloc[0]
            track_summary = {
                "total_mileage_km": ts.get("total_mileage_km", 0),
                "track_point_count": ts.get("track_point_count", 0),
                "total_movement_duration": ts.get("total_movement_duration", 0),
                "total_parking_duration": ts.get("total_parking_duration", 0),
            }

    track_points_count = 0
    max_speed = 0.0
    if track_points_df is not None and "alarm_id" in track_points_df.columns:
        tpmask = track_points_df["alarm_id"] == alarm_id
        track_points_count = int(tpmask.sum())
        if tpmask.any():
            max_speed = float(track_points_df.loc[tpmask, "speed_kmh"].max())

    if max_speed_df is not None and "alarm_id" in max_speed_df.columns:
        mspmask = max_speed_df["alarm_id"] == alarm_id
        if mspmask.any():
            msp_max = float(max_speed_df.loc[mspmask, "speed_kmh"].max())
            if msp_max > max_speed:
                max_speed = msp_max

    vehicle: dict = {}
    unit_sn = alarm.get("UnitStateNumber", "")
    if unit_sn and vehicles_df is not None and "unit_state_number" in vehicles_df.columns:
        vmask = vehicles_df["unit_state_number"] == unit_sn
        if vmask.any():
            vh = vehicles_df[vmask].iloc[0]
            vehicle = {
                "unit_state_number": vh.get("unit_state_number", ""),
                "alarm_count": vh.get("alarm_count", 0),
                "alarm_types": vh.get("alarm_types", ""),
                "downloaded_video_count": vh.get("downloaded_video_count", 0),
                "total_track_mileage_km": vh.get("total_track_mileage_km", 0),
            }

    return {
        "alarm": alarm,
        "videos": videos,
        "track_summary": track_summary,
        "track_points_count": track_points_count,
        "max_speed": max_speed,
        "vehicle": vehicle,
    }
