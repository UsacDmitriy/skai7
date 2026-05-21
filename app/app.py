from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.constants import PAGE_TITLE, PAGE_ICON, LAYOUT, ALARM_TYPE_LABELS, COLORS, SPEED_LIMIT_KMH
from app.data_loader import load_csv_files, save_action

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_DATA_DIR = PROJECT_ROOT / "sample_data"
OUTPUT_DIR = PROJECT_ROOT / "output"


def _init_session_state() -> None:
    defaults = {
        "datasets": {},
        "active_tab": "📋 Лента событий",
        "selected_incident": None,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def render_data_tab(datasets: dict) -> None:
    st.info("Вкладка «Данные» — загрузка и просмотр CSV файлов")
    if datasets:
        for name, df in datasets.items():
            with st.expander(name, expanded=False):
                st.dataframe(df.head(20), use_container_width=True)


def render_dashboard_tab(datasets: dict) -> None:
    st.info("Вкладка «Dashboard» — появится в wave-03")
    alarms_df = datasets.get("selected_video_alarms")
    if alarms_df is not None and not alarms_df.empty:
        st.metric("Всего алармов", len(alarms_df))


def render_analysis_tab(datasets: dict) -> None:
    st.info("Вкладка «Аналитика» — появится в wave-04")


def render_incidents_tab(datasets: dict) -> None:
    st.info("Вкладка «Инциденты» — появится в wave-04")


def render_actions_tab(datasets: dict) -> None:
    st.info("Вкладка «Заявки» — появится в wave-05")


def main() -> None:
    _init_session_state()

    st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout=LAYOUT)

    st.title(PAGE_TITLE)
    st.caption("Data → Logic → UI → Action. Keep it small, explainable, and demo-ready.")

    data_source = DATA_DIR if any(DATA_DIR.glob("*.csv")) else SAMPLE_DATA_DIR
    if not st.session_state["datasets"]:
        st.session_state["datasets"] = load_csv_files(data_source)
    datasets = st.session_state["datasets"]

    st.sidebar.caption(f"Чтение CSV из: {data_source.relative_to(PROJECT_ROOT)}")

    tabs = [
        "📋 Лента событий",
        "🛡 Живой мониторинг",
        "🔍 Карточка инцидента",
        "📊 Аналитика",
        "📝 Заявки",
    ]
    active = st.sidebar.radio("Навигация", tabs, key="active_tab")

    data_tab, live_tab, detail_tab, analytics_tab, actions_tab = st.tabs(tabs)
    with data_tab:
        render_data_tab(datasets)
    with live_tab:
        render_dashboard_tab(datasets)
    with detail_tab:
        render_analysis_tab(datasets)
    with analytics_tab:
        render_incidents_tab(datasets)
    with actions_tab:
        render_actions_tab(datasets)


if __name__ == "__main__":
    main()