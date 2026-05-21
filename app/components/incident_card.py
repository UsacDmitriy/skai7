from __future__ import annotations

import streamlit as st
from app.constants import COLORS, SEVERITY_COLORS, SOURCE_LABELS


def render_incident_card(
    incident: dict,
    is_selected: bool = False,
    compact: bool = False,
) -> None:
    """Карточка инцидента. compact=True для топ-5 рисков (live monitor)."""
    risk_level = incident.get("risk_level", "low")
    sev = SEVERITY_COLORS.get(risk_level, SEVERITY_COLORS["low"])

    border_color = sev["border"]
    bg = COLORS["primary_50"] if is_selected else COLORS["surface"]

    plate = incident.get("vehicle_plate", "—")
    driver = incident.get("driver", "—")
    event_type = incident.get("alarm_type_label", incident.get("alarm_type", "—"))
    source = incident.get("event_source", "")
    source_label = SOURCE_LABELS.get(source, source)
    score = incident.get("score", 0)
    speed = incident.get("speed_kmh", 0)
    is_night = incident.get("is_night", False)
    ts = incident.get("ts", "")

    html = f"""
    <div style="
        background: {bg};
        border: 1px solid {COLORS['border']};
        border-left: 4px solid {border_color};
        border-radius: 6px;
        padding: 12px;
        margin-bottom: 8px;
        cursor: pointer;
    ">
        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <span style="font-weight: 600; color: {COLORS['text']};">{plate}</span>
            <span style="font-size: 10px; background: #EDE9FE; color: #7C3AED; padding: 1px 6px; border-radius: 8px;">{source_label}</span>
        </div>
        <div style="font-size: 12px; color: {COLORS['muted']}; margin-bottom: 4px;">{driver}</div>
        <div style="font-weight: 500; color: {sev['text']}; margin-bottom: 6px;">{event_type}</div>
        <div style="display: flex; justify-content: space-between; font-size: 11px;">
            <span>
                <span style="background: #F1F5F9; padding: 2px 6px; border-radius: 4px; margin-right: 4px;">⚡ {speed} км/ч</span>
                {f'<span style="background: #F1F5F9; padding: 2px 6px; border-radius: 4px;">🌙 Ночь</span>' if is_night else ''}
            </span>
            <span style="font-weight: 700; color: {sev['text']};">Score {score}</span>
        </div>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)
