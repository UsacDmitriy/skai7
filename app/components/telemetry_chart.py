from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st
from app.constants import COLORS


def render_telemetry_chart(
    telemetry: list[dict],
    speed_limit: int = 90,
    height: int = 300,
) -> None:
    """График скорость (синяя линия, левая ось Y) + акселерометр (оранжевая линия, правая ось Y)."""
    if not telemetry:
        st.info("Нет данных телеметрии")
        return

    df = pd.DataFrame(telemetry)

    # Скорость — левая ось
    speed_line = (
        alt.Chart(df)
        .mark_line(point=True, color=COLORS["primary"], strokeWidth=2)
        .encode(
            x=alt.X("ts_offset:Q", title="Смещение от события (сек)", axis=alt.Axis(grid=True)),
            y=alt.Y("speed:Q", title="Скорость (км/ч)", axis=alt.Axis(titleColor=COLORS["primary"])),
            tooltip=["ts_offset:Q", "speed:Q", "ax:Q", "ay:Q"],
        )
    )

    # Акселерометр — правая ось
    accel_line = (
        alt.Chart(df)
        .mark_line(point=True, color=COLORS["high"], strokeWidth=1.5)
        .encode(
            x=alt.X("ts_offset:Q"),
            y=alt.Y("ax:Q", title="Акс. X (м/с²)", axis=alt.Axis(titleColor=COLORS["high"])),
        )
    )

    # Лимит скорости
    limit_df = pd.DataFrame({"y": [speed_limit]})
    limit_line = (
        alt.Chart(limit_df)
        .mark_rule(strokeDash=[4, 4], color=COLORS["critical"], strokeWidth=1)
        .encode(y="y")
    )

    # Линия события t=0
    event_df = pd.DataFrame({"x": [0]})
    event_line = (
        alt.Chart(event_df)
        .mark_rule(strokeDash=[2, 2], color=COLORS["warning"], strokeWidth=1.5)
        .encode(x="x")
    )

    # Объединение
    chart = alt.layer(speed_line, accel_line, limit_line, event_line).resolve_scale(
        y="independent"
    ).properties(
        height=height, title="Скорость и акселерометр"
    ).configure_axis(
        gridColor=COLORS["border"],
        labelFontSize=11,
    )

    st.altair_chart(chart, use_container_width=True)
