from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.constants import PAGE_TITLE, PAGE_ICON, LAYOUT, ALARM_TYPE_LABELS, COLORS, SPEED_LIMIT_KMH
from app.data_loader import load_csv_files
from app.screens.incident_card import render_incident_card_screen
from app.screens.incident import render_incident_tab
from app.screens.monitor import render_monitor_tab
from app.screens.report import render_interactive_report

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_DATA_DIR = PROJECT_ROOT / "sample_data"
OUTPUT_DIR = PROJECT_ROOT / "output"


def _init_session_state() -> None:
    defaults = {
        "datasets": {},
        "active_tab": "📋 Лента событий",
        "selected_incident": None,
        "selected_alarm_id": None,
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
        "📊 Интерактивный отчёт",
        "📝 Заявки",
    ]
    active = st.sidebar.radio("Навигация", tabs, key="active_tab")

    data_tab, live_tab, detail_tab, report_tab, actions_tab = st.tabs(tabs)
    with data_tab:
        render_data_tab(datasets)
    with live_tab:
        render_monitor_tab(datasets, ALARM_TYPE_LABELS)
    with detail_tab:
        render_incident_tab(datasets, ALARM_TYPE_LABELS, COLORS, SPEED_LIMIT_KMH)
    with report_tab:
        render_interactive_report(datasets, ALARM_TYPE_LABELS, COLORS, SPEED_LIMIT_KMH)
    with actions_tab:
        render_actions_tab(datasets)


if __name__ == "__main__":
    main()
