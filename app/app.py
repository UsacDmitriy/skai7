from __future__ import annotations

import logging
from pathlib import Path

import streamlit as st

from constants import (
    ACTION_LABELS,
    ACTION_TYPES,
    ALARM_TYPE_LABELS,
    COLORS,
    LAYOUT,
    PAGE_ICON,
    PAGE_TITLE,
    SPEED_LIMIT_KMH,
)
from data_loader import load_csv_files, save_action

try:
    from screens.analytics import render_analytics_tab
    from screens.incident import render_incident_tab
    from screens.monitor import render_monitor_tab
except ImportError as exc:
    st.error(f"Не удалось загрузить модули экранов: {exc}")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_DATA_DIR = PROJECT_ROOT / "sample_data"
OUTPUT_DIR = PROJECT_ROOT / "output"

st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout=LAYOUT)


def init_session() -> None:
    defaults = {
        "datasets": {},
        "selected_alarm_id": None,
        "last_action": None,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def render_sidebar(datasets, data_source):
    st.sidebar.caption(f"Источник: {data_source.relative_to(PROJECT_ROOT)}")
    st.sidebar.caption(f"Загружено: {len(datasets)} файлов")

    alarms_df = datasets.get("selected_video_alarms")
    vehicles_df = datasets.get("vehicles")
    video_df = datasets.get("video_files")
    if alarms_df is not None:
        st.sidebar.metric("Алармов", len(alarms_df))
    if vehicles_df is not None:
        st.sidebar.metric("Машин", len(vehicles_df))
    if video_df is not None:
        st.sidebar.metric("Видео", len(video_df))

    if st.session_state.get("last_action"):
        st.sidebar.success(f"Действие: {st.session_state['last_action']}")


def main():
    init_session()

    st.title(PAGE_TITLE)
    st.caption("Телематика + Видео → Контекст → Действие. MVP единого окна инцидентов.")

    data_source = DATA_DIR if any(DATA_DIR.glob("*.csv")) else SAMPLE_DATA_DIR
    if not st.session_state["datasets"]:
        st.session_state["datasets"] = load_csv_files(data_source)
    datasets = st.session_state["datasets"]

    render_sidebar(datasets, data_source)

    monitor_tab, analytics_tab, incident_tab = st.tabs([
        "🗺 Мониторинг",
        "📊 Отчёты",
        "📋 Инцидент",
    ])

    with monitor_tab:
        render_monitor_tab(datasets, ALARM_TYPE_LABELS)

    with analytics_tab:
        render_analytics_tab(datasets, ALARM_TYPE_LABELS, COLORS)

    with incident_tab:
        result = render_incident_tab(datasets, ALARM_TYPE_LABELS, COLORS, SPEED_LIMIT_KMH)
        if result:
            alarm_id, unit_sn = result
            with st.form("incident_action_form", clear_on_submit=True):
                st.markdown("### Действие")
                prefix = f"{alarm_id[:8]}_{unit_sn}" if alarm_id else ""
                row_id = st.text_input("ID записи", value=prefix)
                action_type = st.selectbox(
                    "Тип действия",
                    options=ACTION_TYPES,
                    format_func=lambda t: ACTION_LABELS.get(t, t),
                )
                comment = st.text_area("Комментарий", height=80)
                submitted = st.form_submit_button("Сохранить")

            if submitted:
                save_action(OUTPUT_DIR, row_id=row_id, action=action_type, comment=comment)
                st.session_state["last_action"] = action_type
                st.success("Действие сохранено в ./output/actions.csv")


if __name__ == "__main__":
    main()
