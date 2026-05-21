from __future__ import annotations

import altair as alt
import pandas as pd

__all__ = [
    "build_alarm_type_bar_chart",
    "build_speed_scatter_chart",
    "build_track_speed_chart",
    "build_vehicle_mileage_bar_chart",
]

CHART_HEIGHT = 320


def _empty_chart(message: str = "Нет данных") -> alt.Chart:
    source = pd.DataFrame({"text": [message]})
    return (
        alt.Chart(source)
        .mark_text(size=16, color="#64748B")
        .encode(text="text:N")
        .properties(width=600, height=200)
    )


def build_alarm_type_bar_chart(
    distribution: pd.DataFrame,
    label_map: dict[str, str] | None = None,
    chart_colors: list[str] | None = None,
) -> alt.Chart:
    if distribution.empty:
        return _empty_chart()

    df = distribution.copy()
    if "count" in df.columns and "Count" not in df.columns:
        df = df.rename(columns={"count": "Count"})

    df["Label"] = df["Type"].map(label_map if label_map else {}).fillna(df["Type"])

    colors = chart_colors or ["#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4"]

    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("Label:N", sort="-y", title="Тип аларма", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("Count:Q", title="Количество"),
            color=alt.Color("Label:N", title=None, scale=alt.Scale(range=colors), legend=None),
            tooltip=["Label:N", "Count:Q"],
        )
        .properties(height=CHART_HEIGHT, title="Распределение типов алармов")
    )


def build_speed_scatter_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    color_col: str | None = None,
    chart_colors: list[str] | None = None,
) -> alt.Chart:
    if df.empty or x_col not in df.columns or y_col not in df.columns:
        return _empty_chart()

    sample = df.head(5000)
    colors = chart_colors or ["#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4"]

    if color_col and color_col in sample.columns:
        chart = (
            alt.Chart(sample)
            .mark_circle(size=60, opacity=0.7)
            .encode(
                x=alt.X(f"{x_col}:Q", title=x_col),
                y=alt.Y(f"{y_col}:Q", title=y_col),
                color=alt.Color(f"{color_col}:N", title=color_col, scale=alt.Scale(range=colors)),
                tooltip=[x_col, y_col, color_col],
            )
        )
    else:
        chart = (
            alt.Chart(sample)
            .mark_circle(size=60, opacity=0.7)
            .encode(
                x=alt.X(f"{x_col}:Q", title=x_col),
                y=alt.Y(f"{y_col}:Q", title=y_col),
                tooltip=[x_col, y_col],
            )
        )

    return chart.properties(height=CHART_HEIGHT)


def build_track_speed_chart(
    track_points: pd.DataFrame,
    alarm_id: str = "",
    chart_colors: list[str] | None = None,
) -> alt.Chart:
    if track_points.empty:
        return _empty_chart()

    df = track_points.copy()
    if "timestamp_utc" in df.columns:
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)

    color = (chart_colors or ["#3B82F6"])[0]
    title = f"Скорость трека — {alarm_id[:8]}…" if alarm_id else "Скорость по треку"

    return (
        alt.Chart(df)
        .mark_line(point=alt.OverlayMarkDef(size=30), color=color, strokeWidth=2)
        .encode(
            x=alt.X("timestamp_utc:T", title="Время (UTC)"),
            y=alt.Y("speed_kmh:Q", title="Скорость (км/ч)"),
            tooltip=["timestamp_utc:T", "speed_kmh:Q"],
        )
        .properties(height=CHART_HEIGHT, title=title)
    )


def build_vehicle_mileage_bar_chart(
    vehicles_df: pd.DataFrame,
    chart_colors: list[str] | None = None,
) -> alt.Chart:
    if vehicles_df.empty or "total_track_mileage_km" not in vehicles_df.columns:
        return _empty_chart()

    df = vehicles_df.copy()
    df = df.sort_values("total_track_mileage_km", ascending=False).head(15)
    label_col = "unit_state_number" if "unit_state_number" in df.columns else df.columns[0]
    colors = chart_colors or ["#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4"]

    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(f"{label_col}:N", sort="-y", title="Госномер"),
            y=alt.Y("total_track_mileage_km:Q", title="Пробег (км)"),
            color=alt.Color("total_track_mileage_km:Q", title="Пробег", scale=alt.Scale(scheme="blues"), legend=None),
            tooltip=[f"{label_col}:N", "total_track_mileage_km:Q"],
        )
        .properties(height=CHART_HEIGHT, title="Пробег по машинам (Top-15)")
    )
