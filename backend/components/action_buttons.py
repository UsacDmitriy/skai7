from __future__ import annotations

import streamlit as st
from backend.constants import COLORS
from backend.data_loader import save_action


def render_action_buttons(incident: dict) -> None:
    """Кнопки действий: запросить видео, создать заявку, отчёт, позвонить."""
    st.markdown("### Действия")

    incident_id = incident.get("id", "")
    video_available = incident.get("video_available", True)

    # Инициализация состояний
    if f"action_ticket_{incident_id}" not in st.session_state:
        st.session_state[f"action_ticket_{incident_id}"] = False
    if f"action_archive_{incident_id}" not in st.session_state:
        st.session_state[f"action_archive_{incident_id}"] = False

    # Кнопки
    if not video_available:
        archive_requested = st.session_state[f"action_archive_{incident_id}"]
        if archive_requested:
            st.success("✓ Запрос отправлен. Ожидайте 15–30 минут.")
        else:
            if st.button("📋 Запросить архивное видео", use_container_width=True, type="primary"):
                save_action(incident_id, "request_archive", f"Запрос архива для {incident_id}")
                st.session_state[f"action_archive_{incident_id}"] = True
                st.rerun()
    else:
        if st.button("📋 Запросить видео за период", use_container_width=True):
            save_action(incident_id, "request_archive", f"Запрос видео за период для {incident_id}")
            st.rerun()

    ticket_created = st.session_state[f"action_ticket_{incident_id}"]
    if ticket_created:
        st.success("✓ Заявка создана")
    else:
        if st.button("🔧 Создать заявку", use_container_width=True, type="primary"):
            save_action(incident_id, "create_task", f"Создана заявка по инциденту {incident_id}")
            st.session_state[f"action_ticket_{incident_id}"] = True
            st.rerun()

    if st.button("📄 Сформировать отчёт", use_container_width=True):
        save_action(incident_id, "export_report", f"Сформирован отчёт по {incident_id}")
        st.rerun()

    if st.button("📞 Вызвать водителя", use_container_width=True):
        save_action(incident_id, "call_driver", f"Вызов водителя по {incident_id}")
        st.rerun()

    if st.button("📹 Позвонить через камеру", use_container_width=True, type="secondary"):
        st.session_state["call_status"] = "connecting"
        st.rerun()

    if st.session_state.get("call_status") == "connecting":
        st.info("⏳ Подключение...")
