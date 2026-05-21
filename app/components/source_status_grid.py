from __future__ import annotations

import streamlit as st
from app.constants import COLORS


def render_source_status(cameras: list[dict]) -> None:
    """Статус камер: CAM-01 · [● Работает], CAM-02 · [● Нет сигнала], ..."""
    st.markdown("**СТАТУС КАМЕР**")

    for cam in cameras:
        cam_id = cam.get("id", "—")
        cam_label = cam.get("label", cam_id)
        status = cam.get("status", "unknown")

        status_config = {
            "online": ("●", "Работает", COLORS["ok"]),
            "offline": ("●", "Нет сигнала", COLORS["critical"]),
            "warning": ("●", "Предупреждение", COLORS["warning"]),
            "unknown": ("●", "Неизвестно", COLORS["muted"]),
        }

        dot, text, color = status_config.get(status, status_config["unknown"])

        st.markdown(
            f'📷 **{cam_id}** {cam_label} · '
            f'<span style="color: {color};">{dot} {text}</span>',
            unsafe_allow_html=True,
        )

    st.divider()

    # Состояние комплекса (дополнительно)
    st.markdown("**СОСТОЯНИЕ КОМПЛЕКСА**")

    sources = [
        ("📡", "Связь", "online"),
        ("🔋", "Питание", "online"),
        ("💾", "Архив", "available"),
    ]

    for icon, label, status in sources:
        st.caption(f"{icon} {label} · 🟢 Онлайн")
