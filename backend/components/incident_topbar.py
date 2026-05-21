from __future__ import annotations

import streamlit as st
from backend.constants import COLORS, SEVERITY_COLORS, SOURCE_LABELS


def render_incident_topbar(incident: dict) -> None:
    """Шапка: ← Назад + госномер + водитель + severity badge + score + источник."""
    plate = incident.get("vehicle_plate", "—")
    driver = incident.get("driver", "—")
    risk_level = incident.get("risk_level", "low")
    score = incident.get("score", 0)
    source = incident.get("event_source", "")
    source_label = SOURCE_LABELS.get(source, source)

    sev = SEVERITY_COLORS.get(risk_level, SEVERITY_COLORS["low"])
    risk_labels = {"critical": "Критичный", "high": "Высокий", "medium": "Средний", "low": "Низкий"}
    risk_label = risk_labels.get(risk_level, risk_level)

    col1, col2, col3 = st.columns([6, 2, 2])

    with col1:
        if st.button("← Назад", key="back_to_feed"):
            st.session_state["active_tab"] = "📋 Лента событий"
            st.rerun()
        st.markdown(f"### {plate} — {driver}")

    with col2:
        st.markdown(
            f'<span style="background: {sev["bg"]}; color: {sev["text"]}; '
            f'padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 500;">'
            f'● {risk_label}</span> '
            f'<span style="background: #F0FDF4; color: #16A34A; '
            f'padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 500;">'
            f'{source_label}</span>',
            unsafe_allow_html=True,
        )

    with col3:
        st.metric("Score", score)

    st.divider()
