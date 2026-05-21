from __future__ import annotations

from pathlib import Path

import streamlit as st

from backend.constants import PAGE_TITLE, PAGE_ICON, LAYOUT, ALARM_TYPE_LABELS, COLORS, SPEED_LIMIT_KMH
from backend.data_loader import load_csv_files
from backend.screens.incident_card import render_incident_card_screen
from backend.screens.incident import render_incident_tab
from backend.screens.monitor import render_monitor_tab
from backend.screens.report import render_interactive_report

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
    alarms_df = datasets.get("selected_video_alarms")
    if alarms_df is None or alarms_df.empty:
        st.info("Вкладка «Данные» — загрузка и просмотр CSV файлов")
        if datasets:
            for name, df in datasets.items():
                with st.expander(name, expanded=False):
                    st.dataframe(df.head(20), use_container_width=True)
        return

    # Event list for quick access
    if "AlarmId" in alarms_df.columns and "UnitStateNumber" in alarms_df.columns:
        st.subheader("Список событий")
        sorted_df = alarms_df.dropna(subset=["Speed"]).sort_values("Speed", ascending=False)
        event_options = []
        event_map = {}
        for _, row in sorted_df.iterrows():
            aid = str(row.get("AlarmId", ""))
            veh = str(row.get("UnitStateNumber", "—"))
            typ = str(row.get("Type", ""))
            spd = float(row.get("Speed", 0))
            lbl = f"{veh} · {typ} · {spd:.0f} км/ч"
            event_options.append(lbl)
            event_map[lbl] = aid

        sel_lbl = st.selectbox("Событие", options=event_options, key="data_event_select")
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            if st.button("🔍 Открыть карточку"):
                st.session_state["selected_alarm_id"] = event_map[sel_lbl]
                st.session_state["active_tab"] = "🔍 Карточка инцидента"
                st.rerun()
        with c2:
            if st.button("📊 Отчёт по водителю"):
                aid = event_map[sel_lbl]
                unit_sn = str(alarms_df[alarms_df["AlarmId"] == aid]["UnitStateNumber"].values[0])
                st.session_state["report_driver_id"] = unit_sn
                st.session_state["report_preset"] = "driver_3d"
                st.session_state["report_query_text"] = f"Нарушения {unit_sn}"
                st.session_state["report_confirmed"] = True
                st.session_state["report_show_confirm"] = False
                st.session_state["active_tab"] = "📊 Интерактивный отчёт"
                st.rerun()
        with c3:
            if st.button("🛡 Открыть в мониторе"):
                st.session_state["selected_alarm_id"] = event_map[sel_lbl]
                st.session_state["active_tab"] = "🛡 Живой мониторинг"
                st.rerun()

    st.markdown("---")
    st.info("Просмотр CSV файлов (фильтр по выбранному событию)")
    selected_alarm_id = event_map.get(sel_lbl) if "sel_lbl" in locals() else None
    if datasets:
        for name, df in datasets.items():
            display_df = df
            if selected_alarm_id and name in ("max_speed_points", "track_points", "track_summary", "track_periods", "video_files"):
                if "alarm_id" in df.columns:
                    display_df = df[df["alarm_id"] == selected_alarm_id]
            if selected_alarm_id and name == "selected_video_alarms":
                if "AlarmId" in df.columns:
                    display_df = df[df["AlarmId"] == selected_alarm_id]
            with st.expander(name, expanded=False):
                st.dataframe(display_df.head(20), use_container_width=True)


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
    active_tab = st.session_state.get("active_tab", tabs[0])
    try:
        active_index = tabs.index(active_tab)
    except ValueError:
        active_index = 0

    active = st.sidebar.radio("Навигация", tabs, index=active_index)

    if active != active_tab:
        st.session_state["active_tab"] = active
        st.rerun()

    if active == "📋 Лента событий":
        render_data_tab(datasets)
    elif active == "🛡 Живой мониторинг":
        render_monitor_tab(datasets, ALARM_TYPE_LABELS)
    elif active == "🔍 Карточка инцидента":
        render_incident_tab(datasets, ALARM_TYPE_LABELS, COLORS, SPEED_LIMIT_KMH)
    elif active == "📊 Интерактивный отчёт":
        render_interactive_report(datasets, ALARM_TYPE_LABELS, COLORS, SPEED_LIMIT_KMH)
    elif active == "📝 Заявки":
        render_actions_tab(datasets)


if __name__ == "__main__":
    main()
