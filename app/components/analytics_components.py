from __future__ import annotations

from collections import Counter

import altair as alt
import pandas as pd
import streamlit as st
from app.constants import COLORS


def render_driver_report_card(incident: dict, vehicle: dict | None = None) -> None:
    """Карточка водителя."""
    with st.container(border=True):
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("### 👤")
        with col2:
            driver = incident.get("driver", "Неизвестный")
            driver_id = incident.get("driver_id", "—")
            plate = incident.get("vehicle_plate", "—")
            st.markdown(f"### {driver}")
            st.caption(f"ID: {driver_id} · ТС: {plate}")

        score = incident.get("score", 0)
        st.markdown(f"**Score безопасности:** {score} / 100")
        st.progress(score / 100, text=f"{score}%")


def render_violations_table(incidents: list[dict]) -> None:
    """Таблица нарушений."""
    rows = []
    for inc in incidents:
        rows.append({
            "Дата": inc.get("ts", "")[:10],
            "Время": inc.get("ts", "")[11:19],
            "Тип": inc.get("alarm_type_label", ""),
            "Скорость": f"{inc.get('speed_kmh', 0)} км/ч",
            "Score": inc.get("score", 0),
            "Видео": "✅" if inc.get("video_available") else "❌",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_fleet_bar_chart(incidents: list[dict]) -> None:
    """Столбчатая диаграмма топ-10 ТС по нарушениям."""
    plates = Counter(i["vehicle_plate"] for i in incidents)
    df = pd.DataFrame(
        [{"plate": plate, "count": count} for plate, count in plates.most_common(10)]
    )

    if df.empty:
        st.info("Нет данных для графика")
        return

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("plate:N", sort="-y", title="Госномер"),
            y=alt.Y("count:Q", title="Нарушений"),
            color=alt.Color("count:Q", legend=None, scale=alt.Scale(scheme="blues")),
            tooltip=["plate", "count"],
        )
        .properties(height=320, title="Топ ТС по нарушениям")
    )
    st.altair_chart(chart, use_container_width=True)


def render_confirmation_modal(query: str, params: dict) -> bool:
    """Модальное окно подтверждения NL-запроса."""
    with st.container(border=True):
        st.markdown("### Я понял запрос так:")
        for key, value in params.items():
            st.markdown(f"✓ **{key}:** {value}")

        col1, col2 = st.columns(2)
        with col1:
            confirm = st.button("✅ Подтвердить", use_container_width=True)
        with col2:
            cancel = st.button("✏ Исправить", use_container_width=True)
        return confirm


def render_speed_chart(
    telemetry: list[dict],
    speed_limit: int = 90,
    title: str = "Скорость",
) -> None:
    """График скорости."""
    df = pd.DataFrame(telemetry)
    if df.empty:
        st.info("Нет данных телеметрии")
        return

    line = (
        alt.Chart(df)
        .mark_line(point=True, color=COLORS["primary"])
        .encode(
            x=alt.X("ts_offset:Q", title="Смещение (сек)"),
            y=alt.Y("speed:Q", title="Скорость (км/ч)"),
            tooltip=["ts_offset", "speed"],
        )
    )

    limit_line = (
        alt.Chart(pd.DataFrame({"y": [speed_limit]}))
        .mark_rule(strokeDash=[4, 4], color=COLORS["critical"])
        .encode(y="y")
    )

    event_line = (
        alt.Chart(pd.DataFrame({"x": [0]}))
        .mark_rule(strokeDash=[2, 2], color=COLORS["warning"])
        .encode(x="x")
    )

    chart = (line + limit_line + event_line).properties(height=300, title=title)
    st.altair_chart(chart, use_container_width=True)


def render_fleet_map(incidents: list[dict]) -> None:
    """Карта парка с маркерами ТС."""
    points = []
    for inc in incidents:
        lat = inc.get("lat")
        lon = inc.get("lon")
        if lat and lon:
            points.append({
                "lat": lat,
                "lon": lon,
                "plate": inc.get("vehicle_plate", ""),
                "risk": inc.get("risk_level", "low"),
                "score": inc.get("score", 0),
            })

    if not points:
        st.info("Нет координат для отображения на карте")
        return

    df = pd.DataFrame(points)
    st.map(df, latitude="lat", longitude="lon", size=10)


def render_fleet_drivers_list(incidents: list[dict]) -> None:
    """Список водителей с рейтингом."""
    rows = []
    for inc in incidents:
        rows.append({
            "Водитель": inc.get("driver", ""),
            "ТС": inc.get("vehicle_plate", ""),
            "Score": inc.get("score", 0),
            "Нарушений за 7д": inc.get("events_last_7d", 0),
            "Статус": inc.get("status", ""),
        })

    df = pd.DataFrame(rows).sort_values("Score", ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)


__all__ = [
    "render_driver_report_card",
    "render_violations_table",
    "render_fleet_bar_chart",
    "render_confirmation_modal",
    "render_speed_chart",
    "render_fleet_map",
    "render_fleet_drivers_list",
]
