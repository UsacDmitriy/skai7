from __future__ import annotations

import streamlit as st
from backend.constants import COLORS


def render_context_chips(incident: dict) -> None:
    """Чипы: непрерывное вождение, ночная поездка, превышение, нет видео."""
    chips = []

    continuous_min = incident.get("continuous_driving_min", 0)
    if continuous_min > 60:
        hours = continuous_min // 60
        mins = continuous_min % 60
        chips.append({
            "icon": "🟠",
            "text": f"Непрерывное вождение: {hours}ч {mins}мин",
            "bg": "#FEF3C7",
            "color": "#B45309",
        })

    if incident.get("is_night"):
        chips.append({
            "icon": "🔵",
            "text": "Ночная поездка",
            "bg": "#DBEAFE",
            "color": "#1E40AF",
        })

    speed = incident.get("speed_kmh", 0)
    limit = incident.get("speed_limit_kmh", 90)
    if speed > limit:
        over = int(speed - limit)
        chips.append({
            "icon": "⚡",
            "text": f"+{over} км/ч от лимита",
            "bg": "#FEF3C7",
            "color": "#B45309",
        })

    if not incident.get("video_available", True):
        chips.append({
            "icon": "📷",
            "text": "Видео недоступно",
            "bg": "#FEE2E2",
            "color": "#991B1B",
        })

    if incident.get("score", 100) < 70:
        chips.append({
            "icon": "⚠",
            "text": f"Низкий score: {incident['score']}",
            "bg": "#FEF3C7",
            "color": "#B45309",
        })

    if chips:
        html_parts = []
        for chip in chips:
            html_parts.append(
                f'<span style="background: {chip["bg"]}; color: {chip["color"]}; '
                f'padding: 4px 10px; border-radius: 6px; font-size: 12px; margin-right: 6px;">'
                f'{chip["icon"]} {chip["text"]}</span>'
            )
        st.markdown(" ".join(html_parts), unsafe_allow_html=True)
