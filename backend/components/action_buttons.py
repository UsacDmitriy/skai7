from __future__ import annotations

import streamlit as st
from backend.components.driver_call import render_driver_call_button
from backend.data_loader import save_action


def render_action_bar(
    alarm_id: str,
    unit_sn: str,
    output_dir,
    *,
    datasets: dict | None = None,
    show_report: bool = True,
    show_task: bool = True,
    show_reviewed: bool = True,
    show_card: bool = False,
    show_monitor: bool = False,
    show_call: bool = True,
    on_card_click=None,
    on_monitor_click=None,
) -> None:
    """Компактная панель действий над инцидентом.

    Используется единообразно в мониторе, карточке и отчёте.
    """
    prefix = f"{alarm_id[:8]}_{unit_sn}" if alarm_id else ""
    cols = []
    buttons = []

    if show_reviewed:
        cols.append("reviewed")
    if show_task:
        cols.append("task")
    if show_report:
        cols.append("report")
    if show_card:
        cols.append("card")
    if show_monitor:
        cols.append("monitor")

    if not cols:
        return

    col_widgets = st.columns(len(cols))

    for col_widget, key in zip(col_widgets, cols):
        with col_widget:
            if key == "reviewed":
                if st.button("✅ Проверено", use_container_width=True, key=f"ab_reviewed_{alarm_id}"):
                    save_action(output_dir, row_id=prefix, action="mark_reviewed")
                    st.toast("Помечено как проверено")
            elif key == "task":
                if st.button("📋 Заявка", use_container_width=True, key=f"ab_task_{alarm_id}"):
                    save_action(output_dir, row_id=prefix, action="create_task")
                    st.toast("Заявка создана")
            elif key == "report":
                if st.button("📄 Отчёт", use_container_width=True, key=f"ab_report_{alarm_id}"):
                    save_action(output_dir, row_id=prefix, action="export_report")
                    st.toast("Отчёт сохранён")
            elif key == "card":
                if st.button("🔍 Карточка", use_container_width=True, key=f"ab_card_{alarm_id}"):
                    st.session_state["active_tab"] = "🔍 Карточка инцидента"
                    if on_card_click:
                        on_card_click()
                    st.rerun()
            elif key == "monitor":
                if st.button("🛡 Монитор", use_container_width=True, key=f"ab_monitor_{alarm_id}"):
                    st.session_state["active_tab"] = "🛡 Живой мониторинг"
                    if on_monitor_click:
                        on_monitor_click()
                    st.rerun()

    if show_call and unit_sn and datasets is not None:
        render_driver_call_button(unit_sn, datasets, key_prefix=f"ab_{alarm_id}")
