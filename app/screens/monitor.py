from __future__ import annotations

import streamlit as st
import pandas as pd


_DARK_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    @keyframes pulse {
        0%, 100% { opacity: 1; box-shadow: 0 0 4px #EF4444; }
        50% { opacity: 0.35; box-shadow: 0 0 12px #EF4444; }
    }

    .stApp {
        background-color: #0F172A;
    }

    .monitor-header {
        background: #0F172A;
        padding: 18px 0 6px 0;
        border-bottom: 1px solid #1E293B;
        margin-bottom: 16px;
    }

    .monitor-header h1 {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 26px;
        color: #F1F5F9;
        margin: 0;
        display: flex;
        align-items: center;
    }

    .pulsing-dot {
        display: inline-block;
        width: 14px;
        height: 14px;
        background: #EF4444;
        border-radius: 50%;
        animation: pulse 1.5s ease-in-out infinite;
        margin-right: 12px;
        vertical-align: middle;
    }

    .kpi-row {
        display: flex;
        gap: 24px;
        margin: 14px 0 4px 0;
    }

    .kpi-card {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 14px 22px;
        text-align: center;
        flex: 1;
    }

    .kpi-card .kpi-label {
        font-family: 'Inter', sans-serif;
        font-size: 12px;
        font-weight: 500;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        margin-bottom: 4px;
    }

    .kpi-card .kpi-value {
        font-family: 'Inter', sans-serif;
        font-size: 28px;
        font-weight: 700;
        color: #F1F5F9;
    }

    .section-title {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 15px;
        color: #E2E8F0;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin: 0 0 12px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid #EF4444;
        display: inline-block;
    }

    .event-card-label {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 15px;
        color: #F1F5F9;
    }

    .event-card-speed {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 20px;
        color: #F87171;
    }

    .event-card-speed.normal {
        color: #60A5FA;
    }

    .event-card-meta {
        font-family: 'Inter', sans-serif;
        font-size: 12px;
        color: #94A3B8;
    }

    .event-card-address {
        font-family: 'Inter', sans-serif;
        font-size: 11px;
        color: #64748B;
    }

    .map-container {
        border: 1px solid #334155;
        border-radius: 12px;
        overflow: hidden;
    }

    .vehicle-table-container {
        margin-top: 20px;
        border: 1px solid #1E293B;
        border-radius: 10px;
        padding: 12px;
        background: #0F172A;
    }

    section[data-testid="stSidebar"] {
        background-color: #0F172A;
    }

    .stButton > button {
        font-family: 'Inter', sans-serif;
        font-size: 12px;
        font-weight: 500;
        border-radius: 6px;
        transition: all 0.15s;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #1E293B;
        border: 1px solid #334155 !important;
        border-radius: 10px;
        padding: 14px;
    }

    div[data-testid="stMetricValue"] {
        color: #F1F5F9 !important;
    }

    div[data-testid="stMetricLabel"] {
        color: #94A3B8 !important;
    }

    div[data-testid="stMetricDelta"] {
        color: #F87171 !important;
    }
</style>
"""


def _inject_dark_theme() -> None:
    st.markdown(_DARK_CSS, unsafe_allow_html=True)


def _render_top_panel(alarms_df: pd.DataFrame, vehicles_df: pd.DataFrame | None) -> None:
    total_alarms = len(alarms_df)
    unique_vehicles = (
        alarms_df["UnitStateNumber"].nunique()
        if "UnitStateNumber" in alarms_df.columns
        else (len(vehicles_df) if vehicles_df is not None else 0)
    )
    avg_speed = alarms_df["Speed"].mean() if "Speed" in alarms_df.columns else 0.0

    st.markdown(
        '<div class="monitor-header">'
        '<h1><span class="pulsing-dot"></span>РИСКОВАННЫЕ ПОЕЗДКИ ОНЛАЙН</h1>'
        '<div class="kpi-row">'
        f'<div class="kpi-card">'
        f'<div class="kpi-label">Активные алармы</div>'
        f'<div class="kpi-value">{total_alarms}</div>'
        f'</div>'
        f'<div class="kpi-card">'
        f'<div class="kpi-label">Всего машин</div>'
        f'<div class="kpi-value">{unique_vehicles}</div>'
        f'</div>'
        f'<div class="kpi-card">'
        f'<div class="kpi-label">Средняя скорость</div>'
        f'<div class="kpi-value">{avg_speed:.0f} км/ч</div>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_top5_events(alarms_df: pd.DataFrame, alarm_type_labels: dict[str, str]) -> None:
    st.markdown('<p class="section-title">ТОП-5 РИСКОВАННЫХ СОБЫТИЙ</p>', unsafe_allow_html=True)

    if "Speed" not in alarms_df.columns:
        st.warning("Нет данных о скорости для ранжирования событий.")
        return

    top5 = alarms_df.dropna(subset=["Speed"]).sort_values("Speed", ascending=False).head(5)

    if top5.empty:
        st.info("Нет событий для отображения.")
        return

    for _, row in top5.iterrows():
        alarm_id = str(row.get("AlarmId", ""))
        unit_sn = str(row.get("UnitStateNumber", "—"))
        raw_type = row.get("Type", "—")
        type_label = alarm_type_labels.get(raw_type, raw_type)
        speed = row.get("Speed", 0)
        begin = row.get("Begin", "—")
        address = row.get("Address", "")
        video_count = int(row.get("VideoCount", 0)) if pd.notna(row.get("VideoCount")) else 0

        speed_class = "normal" if speed <= 90 else ""

        with st.container(border=True):
            cols = st.columns([3, 1])

            with cols[0]:
                st.markdown(
                    f'<p class="event-card-label">{unit_sn} &mdash; {type_label}</p>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<p class="event-card-meta">Начало: {begin}</p>',
                    unsafe_allow_html=True,
                )
                if address and str(address) != "nan":
                    st.markdown(
                        f'<p class="event-card-address">{address}</p>',
                        unsafe_allow_html=True,
                    )
                st.caption(f"Видео: {video_count}")

            with cols[1]:
                st.markdown(
                    f'<p class="event-card-speed {speed_class}">{speed:.0f} км/ч</p>',
                    unsafe_allow_html=True,
                )

            if st.button("Выбрать", key=f"monitor_select_{alarm_id}", use_container_width=True):
                st.session_state["selected_alarm_id"] = alarm_id


def _add_color_column(alarms_df: pd.DataFrame) -> pd.DataFrame:
    df = alarms_df.copy()

    def _pick_color(row: pd.Series) -> str:
        speed = row.get("Speed", 0)
        video_count = row.get("VideoCount", 0)

        if pd.notna(speed) and speed > 90:
            return "#DC2626"
        if pd.notna(video_count) and video_count == 0:
            return "#F59E0B"
        return "#2563EB"

    df["color"] = df.apply(_pick_color, axis=1)
    return df


def _render_map(alarms_df: pd.DataFrame) -> None:
    st.markdown('<p class="section-title">КАРТА СОБЫТИЙ</p>', unsafe_allow_html=True)

    lat_col = None
    lon_col = None

    for col in alarms_df.columns:
        col_lower = col.lower()
        if col_lower in ("latitude", "lat"):
            lat_col = col
        elif col_lower in ("longitude", "lon", "long"):
            lon_col = col

    if lat_col is None or lon_col is None:
        st.info("Нет координат для отображения на карте.")
        return

    map_df = alarms_df.dropna(subset=[lat_col, lon_col]).copy()

    if map_df.empty:
        st.info("Нет доступных координат после фильтрации.")
        return

    map_df = map_df.rename(columns={lat_col: "latitude", lon_col: "longitude"})

    map_df = _add_color_column(map_df)

    st.map(
        map_df,
        latitude="latitude",
        longitude="longitude",
        color="color",
        use_container_width=True,
    )


def _render_vehicle_summary(vehicles_df: pd.DataFrame | None) -> None:
    st.markdown('<p class="section-title">СВОДКА ПО МАШИНАМ</p>', unsafe_allow_html=True)

    if vehicles_df is None or vehicles_df.empty:
        st.info("Нет данных о машинах.")
        return

    display_cols = {
        "unit_state_number": "Госномер",
        "alarm_count": "Всего алармов",
        "alarm_types": "Типы алармов",
        "downloaded_video_count": "Видео скачано",
        "total_track_mileage_km": "Пробег (км)",
    }

    available_cols = {k: v for k, v in display_cols.items() if k in vehicles_df.columns}

    if not available_cols:
        st.info("Недостаточно колонок для отображения сводки.")
        return

    summary = vehicles_df[list(available_cols.keys())].rename(columns=available_cols).copy()

    if "Всего алармов" in summary.columns:
        summary = summary.sort_values("Всего алармов", ascending=False)

    summary = summary.head(20)

    st.dataframe(
        summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Пробег (км)": st.column_config.NumberColumn(format="%.1f"),
        },
    )


def render_monitor_tab(datasets: dict[str, pd.DataFrame], alarm_type_labels: dict[str, str]) -> None:
    if not datasets:
        st.warning("Нет данных")
        return

    _inject_dark_theme()

    alarms_df = datasets.get("selected_video_alarms")
    vehicles_df = datasets.get("vehicles")

    if alarms_df is None or alarms_df.empty:
        st.warning("Нет данных об алармах. Загрузите CSV-файлы в ./data.")
        return

    _render_top_panel(alarms_df, vehicles_df)

    left, right = st.columns([3, 7])

    with left:
        _render_top5_events(alarms_df, alarm_type_labels)

    with right:
        _render_map(alarms_df)

    st.markdown("---")
    _render_vehicle_summary(vehicles_df)
