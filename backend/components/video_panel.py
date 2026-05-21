from __future__ import annotations

import streamlit as st
from backend.constants import COLORS


def render_video_panel(
    incident: dict,
    num_cameras: int = 2,
) -> None:
    """Видео-панель: если видео есть — показываем путь к mp4, иначе — placeholder."""
    video_available = incident.get("video_available", False)

    if video_available:
        st.markdown("**ВИДЕО СОБЫТИЯ**")

        cam_labels = [
            ("CAM-01", "ADAS · Передняя", incident.get("cam_front_url", "")),
            ("CAM-02", "DMS · Салон", incident.get("cam_dms_url", "")),
        ]

        for cam_id, label, url in cam_labels[:num_cameras]:
            st.caption(f"**{cam_id} · {label}**")
            if url:
                st.info(f"Видео: `{url}`")
            else:
                st.info("Путь к видео не указан")
            st.progress(35)
            st.caption("00:36:43                                   01:45")
    else:
        st.markdown(
            f"""
            <div style="
                background: {COLORS['bg']};
                border: 2px dashed {COLORS['border']};
                border-radius: 8px;
                padding: 40px 20px;
                text-align: center;
                min-height: 240px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            ">
                <div style="font-size: 48px; color: #CBD5E1; margin-bottom: 16px;">📷</div>
                <div style="font-size: 16px; font-weight: 600; color: {COLORS['muted']};">Видео недоступно</div>
                <div style="font-size: 13px; color: #94A3B8; margin-top: 8px;">CAM-03 не передала данные в архив</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if "archive_requested" not in st.session_state:
            st.session_state["archive_requested"] = False

        if not st.session_state["archive_requested"]:
            if st.button("📋 Запросить архивное видео", use_container_width=True):
                st.session_state["archive_requested"] = True
                st.rerun()
        else:
            st.success("✓ Запрос отправлен. Ожидайте 15–30 минут.")
