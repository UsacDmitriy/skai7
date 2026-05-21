from __future__ import annotations

"""Компонент сводки по ТС для экранов LiveMonitor и IncidentCard."""

import streamlit as st

from app.constants import COLORS


def render_vehicle_summary(vehicle: dict) -> None:
    """Сводка по машине: госномер, модель, driver, alarm_count, пробег, статусы."""
    if not vehicle:
        st.info("Нет данных о ТС")
        return

    cols = st.columns(4)
    cols[0].metric("Алармов всего", vehicle.get("alarm_count", "—"))
    cols[1].metric("Видео скачано", vehicle.get("downloaded_video_count", "—"))
    cols[2].metric(
        "Пробег треков (км)",
        f"{vehicle.get('total_track_mileage_km', 0):.1f}",
    )
    cols[3].metric(
        "Типы алармов",
        str(vehicle.get("alarm_types", "—")).replace("|", ", "),
    )

    st.divider()

    status_cols = st.columns(3)

    status_icons = {
        "online": ("📡", "Онлайн", COLORS["ok"]),
        "warning": ("⚠", "Предупреждение", COLORS["warning"]),
        "offline": ("❌", "Нет связи", COLORS["critical"]),
        "available": ("💾", "Доступен", COLORS["ok"]),
    }

    for col, (key, label) in zip(status_cols, [
        ("telematics", "Связь"),
        ("connection", "Питание"),
        ("archive", "Архив"),
    ]):
        status = vehicle.get(f"{key}_status", "unknown")
        icon, text, color = status_icons.get(status, ("●", status, COLORS["muted"]))
        with col:
            st.markdown(f"{icon} **{label}:** :{color}[{text}]")

    cameras = vehicle.get("cameras", [])
    if cameras:
        st.caption("**Камеры:**")
        cam_cols = st.columns(len(cameras))
        for col, cam in zip(cam_cols, cameras):
            with col:
                status_icon = "🟢" if cam.get("status") == "online" else "🔴"
                st.caption(f"{status_icon} {cam.get('label', cam.get('id', '—'))}")