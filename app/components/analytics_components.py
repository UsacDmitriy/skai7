from __future__ import annotations

"""Компоненты аналитики для SKAI Hackathon."""

import streamlit as st

from app.constants import COLORS


def render_driver_report_card(incident: dict, vehicle: dict | None = None) -> None:
    """Карточка водителя: имя, ID, стаж, ТС, score безопасности."""
    with st.container(border=True):
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("### 👤")
        with col2:
            driver = incident.get("driver", "Неизвестный")
            driver_id = incident.get("driver_id", "—")
            plate = incident.get("vehicle_plate", "—")
            st.markdown(f"### {driver}")
            st.caption(f"ID: {driver_id} · Стаж: 12 лет · ТС: {plate}")

        score = incident.get("score", 0)
        st.markdown(f"**Score безопасности:** {score} / 100")
        st.progress(score / 100, text=f"{score}%")


def render_violations_table(incidents: list[dict]) -> None:
    """Таблица нарушений: дата, время, тип, скорость, score, видео."""
    import pandas as pd

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
    """Столбчатая диаграмма: топ ТС по количеству нарушений."""
    import altair as alt
    import pandas as pd
    from collections import Counter

    plates = Counter(i["vehicle_plate"] for i in incidents)

    df = pd.DataFrame([
        {"plate": plate, "count": count}
        for plate, count in plates.most_common(10)
    ])

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("plate:N", sort="-y", title="Госномер"),
            y=alt.Y("count:Q", title="Нарушений"),
            color=alt.Color("count:Q", legend=None),
            tooltip=["plate", "count"],
        )
        .properties(height=320, title="Топ ТС по нарушениям")
    )
    st.altair_chart(chart, use_container_width=True)


def render_confirmation_modal(query: str, params: dict) -> bool:
    """Модальное окно подтверждения NL-запроса. Возвращает True если подтверждено."""
    with st.container(border=True):
        st.markdown("### Я понял запрос так:")
        for key, value in params.items():
            st.markdown(f"✓ **{key}:** {value}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Подтвердить", use_container_width=True):
                return True
        with col2:
            if st.button("✏ Исправить", use_container_width=True):
                return False
    return False


def render_speed_chart(telemetry: list[dict], speed_limit: int = 90) -> None:
    """График скорости по данным телеметрии."""
    import altair as alt
    import pandas as pd

    df = pd.DataFrame(telemetry)
    if df.empty:
        st.info("Нет данных телеметрии")
        return

    line = (
        alt.Chart(df)
        .mark_line(point=True, color=COLORS["primary"])
        .encode(
            x=alt.X("ts_offset:Q", title="Смещение от события (сек)"),
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

    chart = (line + limit_line + event_line).properties(
        height=300, title="Скорость и акселерометр"
    )
    st.altair_chart(chart, use_container_width=True)


def render_video_slide_panel(incident: dict) -> None:
    """Панель с видео при клике на нарушение."""
    if not incident.get("video_available"):
        st.warning("Видео недоступно для этого инцидента")
        return

    video_path = incident.get("cam_front_url", "")
    if video_path:
        st.video(video_path)
    else:
        st.info("Путь к видео не указан")