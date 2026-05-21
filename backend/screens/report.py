from __future__ import annotations

import random
from pathlib import Path

import pandas as pd
import streamlit as st

from backend.metrics import get_alarm_details
from backend.risk_table import build_risk_table, build_vehicle_summary
from backend.charts import build_track_speed_chart

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_CRITICAL_TYPES = frozenset({"Sabotage", "Drowsiness", "DangerousDistance"})
_HIGH_TYPES = frozenset({"SharpBraking", "SharpAcceleration", "SharpLeftTurn", "SpeedLimitViolation"})

_PRESETS = [
    ("📊", "Нарушения Иванова за последние 3 дня", "driver_3d"),
    ("⚡", "Топ-5 нарушителей за май", "top5_month"),
    ("🔴", "Грубые нарушения за квартал", "critical_quarter"),
    ("📷", "Водители с видео-детекциями", "fleet_video"),
    ("🌙", "Ночные поездки этой недели", "fleet_night"),
    ("📋", "Сравнить двух водителей", "compare"),
]

_CSS = """
<style>
    .report-driver-card {
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        border-radius: 12px;
        padding: 20px 24px;
        color: #FFFFFF;
        margin-bottom: 12px;
    }
    .report-driver-card .initials-circle {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: rgba(255,255,255,0.2);
        font-weight: 700;
        font-size: 20px;
        margin-right: 12px;
        vertical-align: middle;
    }
    .report-driver-card .driver-name-row {
        display: flex;
        align-items: center;
        margin-bottom: 10px;
    }
    .report-driver-card .driver-name {
        font-size: 20px;
        font-weight: 700;
    }
    .report-driver-card .driver-plate {
        font-size: 14px;
        opacity: 0.85;
    }
    .report-safety-bar {
        height: 6px;
        border-radius: 3px;
        background: rgba(255,255,255,0.25);
        margin: 8px 0 12px 0;
        overflow: hidden;
    }
    .report-safety-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.4s;
    }
    .report-info-grid {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 8px 16px;
        font-size: 12px;
        opacity: 0.9;
    }
    .report-info-grid span {
        display: block;
    }
    .report-info-grid .info-label {
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        opacity: 0.7;
    }
    .kpi-row-custom {
        display: flex;
        gap: 10px;
        margin: 12px 0;
    }
    .kpi-card-custom {
        flex: 1;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 14px 16px;
        text-align: center;
    }
    .kpi-card-custom .kpi-value {
        font-size: 26px;
        font-weight: 700;
        color: #0F172A;
    }
    .kpi-card-custom .kpi-label {
        font-size: 11px;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        margin-top: 2px;
    }
    .kpi-card-custom.critical {
        border-color: #DC2626;
        background: #FEF2F2;
    }
    .kpi-card-custom.video {
        border-color: #3B82F6;
        background: #EFF6FF;
    }
    .kpi-card-custom.telemetry {
        border-color: #F59E0B;
        background: #FFFBEB;
    }
    .severe-banner {
        background: #FEF3C7;
        border: 1px solid #F59E0B;
        border-radius: 8px;
        padding: 10px 14px;
        margin: 10px 0;
        font-size: 13px;
        color: #92400E;
    }
    .severity-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
    }
    .severity-badge.critical {
        background: #FEE2E2;
        color: #991B1B;
    }
    .severity-badge.high {
        background: #FEF3C7;
        color: #B45309;
    }
    .severity-badge.medium {
        background: #DBEAFE;
        color: #1E40AF;
    }
    .severity-badge.low {
        background: #DCFCE7;
        color: #166534;
    }
    .detail-header {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 10px;
    }
    .context-chip {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 12px;
        margin: 2px 4px 2px 0;
    }
    .preset-pill-row {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin: 10px 0;
    }
    .modal-box {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 24px;
        max-width: 560px;
        margin: 40px auto 0 auto;
        box-shadow: 0 10px 40px rgba(0,0,0,0.12);
    }
    .fleet-list-row {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .fleet-list-row:hover {
        border-color: #3B82F6;
    }
    .fleet-initials {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: #E2E8F0;
        font-weight: 700;
        font-size: 14px;
        color: #0F172A;
        margin-right: 10px;
    }
    .risk-bar-bg {
        height: 4px;
        border-radius: 2px;
        background: #E2E8F0;
        overflow: hidden;
        width: 100px;
        display: inline-block;
        vertical-align: middle;
    }
    .risk-bar-fill {
        height: 100%;
        border-radius: 2px;
    }
    .mic-btn-active {
        background-color: #FEE2E2 !important;
        color: #DC2626 !important;
        border-color: #DC2626 !important;
    }
    /* navy primary buttons to match reference */
    div[data-testid="stButton"] button[kind="primary"],
    div[data-testid="stButton"] button[kind="primaryFormSubmit"] {
        background: #1E3A8A !important;
        border-color: #1E3A8A !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
    }
    div[data-testid="stButton"] button[kind="primary"]:hover,
    div[data-testid="stButton"] button[kind="primaryFormSubmit"]:hover {
        background: #1E40AF !important;
        border-color: #1E40AF !important;
    }
    .report-empty {
        text-align: center;
        margin: 24px 0 4px 0;
    }
    .report-empty .empty-icon {
        font-size: 40px;
        color: #94A3B8;
    }
    .report-empty .empty-title {
        font-size: 26px;
        font-weight: 700;
        color: #0F172A;
        margin-top: 6px;
    }
    .report-empty .empty-sub {
        font-size: 14px;
        color: #64748B;
        margin-top: 4px;
    }
    .mic-hint {
        font-size: 9px;
        color: #94A3B8;
        text-align: center;
        line-height: 1.2;
        margin-top: 2px;
    }
    .preset-divider {
        text-align: center;
        font-size: 11px;
        letter-spacing: 1px;
        color: #94A3B8;
        text-transform: uppercase;
        margin: 18px 0 6px 0;
    }
    .confirm-row {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 10px;
    }
    .confirm-row .row-icon {
        font-size: 18px;
        line-height: 1.4;
    }
    .confirm-row .row-label {
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #64748B;
    }
    .confirm-row .row-value {
        font-size: 15px;
        font-weight: 600;
        color: #0F172A;
    }
    .confirm-tag {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
        margin-left: 6px;
    }
</style>
"""


def _init_report_session() -> None:
    defaults = {
        "report_preset": None,
        "report_driver_id": None,
        "report_selected_alarm_id": None,
        "report_query_text": "",
        "report_confirmed": False,
        "report_show_confirm": False,
        "report_mic_active": False,
        "report_fleet_view_mode": "Водители",
        "report_fleet_selected_driver": None,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def _inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def _get_initials(name: str) -> str:
    if not name or pd.isna(name):
        return "??"
    parts = str(name).split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return str(name)[:2].upper()


def _get_safety_score(driver_alarms: pd.DataFrame, speed_limit: int) -> tuple[int, str]:
    if driver_alarms.empty:
        return 100, "#16A34A"
    total = len(driver_alarms)
    speeding = int((driver_alarms["Speed"] > speed_limit).sum())
    pct = int(speeding / total * 100) if total > 0 else 0
    score = max(0, 100 - pct)
    if score >= 80:
        color = "#16A34A"
    elif score >= 50:
        color = "#F59E0B"
    else:
        color = "#DC2626"
    return score, color


def _get_severity(row: pd.Series, speed_limit: int) -> str:
    atype = str(row.get("Type", ""))
    if atype in _CRITICAL_TYPES:
        return "critical"
    speed = float(row.get("Speed", 0)) if pd.notna(row.get("Speed")) else 0
    if speed > speed_limit * 1.3:
        return "critical"
    if atype in _HIGH_TYPES:
        return "high"
    if speed > speed_limit:
        return "medium"
    if atype == "":
        return "low"
    return "medium"


def _get_source(row: pd.Series) -> str:
    video_count = int(row.get("VideoCount", 0)) if pd.notna(row.get("VideoCount")) else 0
    track_count = int(row.get("TrackPointCount", 0)) if pd.notna(row.get("TrackPointCount")) else 0
    if video_count > 0:
        return "📹 Видео (ВА)"
    if track_count > 0:
        return "📡 Телематика"
    return "📹 Видео"


def _format_period(driver_alarms: pd.DataFrame) -> str:
    if driver_alarms.empty or "Begin" not in driver_alarms.columns:
        return "—"
    begins = pd.to_datetime(driver_alarms["Begin"], utc=True, errors="coerce").dropna()
    if begins.empty:
        return "—"
    return f"{begins.min():%d.%m.%Y} — {begins.max():%d.%m.%Y}"


def _get_driver_alarms(
    datasets: dict[str, pd.DataFrame],
    driver_id: str,
) -> pd.DataFrame:
    risk_table = build_risk_table(datasets)
    if not risk_table.empty and "UnitStateNumber" in risk_table.columns:
        df = risk_table[risk_table["UnitStateNumber"] == driver_id].copy()
        if not df.empty:
            return df
    alarms_df = datasets.get("selected_video_alarms")
    if alarms_df is not None and "UnitStateNumber" in alarms_df.columns:
        return alarms_df[alarms_df["UnitStateNumber"] == driver_id].copy()
    return pd.DataFrame()


def _get_vehicle_row(datasets: dict[str, pd.DataFrame], driver_id: str) -> pd.Series | None:
    vehicles_df = datasets.get("vehicles")
    if vehicles_df is not None and "unit_state_number" in vehicles_df.columns:
        vmask = vehicles_df["unit_state_number"] == driver_id
        if vmask.any():
            return vehicles_df[vmask].iloc[0]
    return None


def _reset_report(to_confirm: bool = False) -> None:
    st.session_state["report_preset"] = None
    st.session_state["report_driver_id"] = None
    st.session_state["report_selected_alarm_id"] = None
    st.session_state["report_confirmed"] = False
    st.session_state["report_show_confirm"] = to_confirm
    st.session_state["report_fleet_selected_driver"] = None


def _kpi_card(label: str, value: int, kind: str = "default") -> str:
    css_class = f" {kind}" if kind != "default" else ""
    return (
        f'<div class="kpi-card-custom{css_class}">'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-label">{label}</div>'
        f'</div>'
    )


def _render_driver_card(
    driver_id: str,
    driver_alarms: pd.DataFrame,
    vehicle_row: pd.Series | None,
    speed_limit: int,
) -> None:
    if driver_alarms.empty and vehicle_row is None:
        return

    unit_name = str(vehicle_row.get("unit_name", driver_id)) if vehicle_row is not None else driver_id
    if pd.isna(unit_name) or unit_name == "nan":
        unit_name = driver_id

    initials = _get_initials(unit_name)
    safety_score, score_color = _get_safety_score(driver_alarms, speed_limit)

    total_alarms = len(driver_alarms)
    video_detections = int((driver_alarms["VideoCount"] > 0).sum()) if "VideoCount" in driver_alarms.columns else 0
    track_detections = int((driver_alarms["TrackPointCount"] > 0).sum()) if "TrackPointCount" in driver_alarms.columns else 0
    critical_count = (
        int((driver_alarms.apply(lambda r: _get_severity(r, speed_limit), axis=1) == "critical").sum())
        if not driver_alarms.empty
        else 0
    )

    mileage = 0.0
    trips = 0
    if vehicle_row is not None:
        mileage = float(vehicle_row.get("total_track_mileage_km", 0) or 0)
        trips = int(vehicle_row.get("track_window_count", 0) or 0)

    period = _format_period(driver_alarms)

    st.markdown(
        f"""
        <div class="report-driver-card">
            <div class="driver-name-row">
                <span class="initials-circle">{initials}</span>
                <div>
                    <div class="driver-name">{unit_name}</div>
                    <div class="driver-plate">{driver_id}</div>
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                <span style="font-size:13px;">Рейтинг безопасности</span>
                <span style="font-weight:700;font-size:18px;color:{score_color};">{safety_score}%</span>
            </div>
            <div class="report-safety-bar">
                <div class="report-safety-fill" style="width:{safety_score}%;background:{score_color};"></div>
            </div>
            <div class="report-info-grid">
                <span><span class="info-label">ТС</span><br>{unit_name}</span>
                <span><span class="info-label">Период</span><br>{period}</span>
                <span><span class="info-label">Пробег</span><br>{mileage:.1f} км</span>
                <span><span class="info-label">Время в рейсах</span><br>{trips}</span>
                <span><span class="info-label">Рейсов</span><br>{trips}</span>
                <span><span class="info-label">Всего алармов</span><br>{total_alarms}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    kpi_items = [
        ("Всего нарушений", total_alarms, "default"),
        ("Видео-детекции", video_detections, "video"),
        ("Телематика", track_detections, "telemetry"),
        ("Грубых", critical_count, "critical"),
    ]
    cards_html = "".join(_kpi_card(label, value, kind) for label, value, kind in kpi_items)
    st.markdown(f'<div class="kpi-row-custom">{cards_html}</div>', unsafe_allow_html=True)


def _render_severe_banner(critical_count: int) -> None:
    if critical_count == 0:
        return
    st.markdown(
        f"""
        <div class="severe-banner">
            ⚠️ <strong>Внимание:</strong> у водителя зафиксировано {critical_count} критических нарушений.
            Рекомендуется провести беседу по безопасности.
        </div>
        """,
        unsafe_allow_html=True,
    )


def _build_violations_table_df(
    driver_alarms: pd.DataFrame,
    alarm_type_labels: dict[str, str],
    speed_limit: int,
) -> pd.DataFrame:
    if driver_alarms.empty:
        return pd.DataFrame()

    df = driver_alarms.copy()
    df = df.sort_values("Begin", ascending=False)
    df["Severity"] = df.apply(lambda r: _get_severity(r, speed_limit), axis=1)
    df["TypeLabel"] = df["Type"].map(alarm_type_labels).fillna(df["Type"])
    df["Source"] = df.apply(_get_source, axis=1)

    def _reason(row: pd.Series) -> str:
        atype = str(row.get("Type", ""))
        speed = float(row.get("Speed", 0)) if pd.notna(row.get("Speed")) else 0
        if atype == "SpeedLimitViolation" or atype == "Overspeeding":
            over = speed - speed_limit
            if over > 0:
                return f"+{over:.0f} км/ч"
        addr = str(row.get("Address", ""))
        if addr and addr != "nan":
            return addr
        return ""

    df["Reason"] = df.apply(_reason, axis=1)

    # Hide low severity
    df = df[df["Severity"] != "low"].copy()

    display = df[["AlarmId", "Begin", "TypeLabel", "Source", "Severity", "Reason"]].copy()
    display.columns = ["AlarmId", "Дата·Время", "Нарушение", "Источник", "Severity", "Причина"]

    sev_map = {
        "critical": "🔴 Грубое",
        "high": "🟠 Высокое",
        "medium": "🟢 Среднее",
    }
    display["SeverityLabel"] = display["Severity"].map(sev_map).fillna("⚪")

    # keep only needed cols for display
    out = display[["Дата·Время", "Нарушение", "Источник", "SeverityLabel", "Причина"]].copy()
    out = out.reset_index(drop=True)
    out.index = range(1, len(out) + 1)
    out.index.name = "#"
    return out


def _render_violations_table(
    driver_alarms: pd.DataFrame,
    alarm_type_labels: dict[str, str],
    speed_limit: int,
    table_key: str,
) -> str | None:
    styled = _build_violations_table_df(driver_alarms, alarm_type_labels, speed_limit)
    if styled.empty:
        st.info("Нет нарушений для отображения.")
        return None

    event = st.dataframe(
        styled,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        key=table_key,
    )

    selected_rows = event.selection.get("rows", [])
    if selected_rows:
        # recover AlarmId from original ordered frame
        df = driver_alarms.copy()
        df = df.sort_values("Begin", ascending=False)
        df = df[df.apply(lambda r: _get_severity(r, speed_limit), axis=1) != "low"]
        df = df.reset_index(drop=True)
        if selected_rows[0] < len(df):
            return str(df.iloc[selected_rows[0]]["AlarmId"])
    return None


def _render_detail_panel(
    alarm_id: str,
    datasets: dict[str, pd.DataFrame],
    alarm_type_labels: dict[str, str],
    colors: dict,
    speed_limit: int,
) -> None:
    details = get_alarm_details(datasets, alarm_id)
    alarm_row = details.get("alarm_row")
    if alarm_row is None:
        st.warning("Данные аларма не найдены.")
        return

    raw_type = str(alarm_row.get("Type", "—"))
    type_label = alarm_type_labels.get(raw_type, raw_type)
    speed = float(alarm_row.get("Speed", 0)) if pd.notna(alarm_row.get("Speed")) else 0
    begin_str = str(alarm_row.get("Begin", "—"))
    severity = _get_severity(alarm_row, speed_limit)

    sev_labels = {"critical": "Грубое", "high": "Высокое", "medium": "Среднее", "low": "Низкое"}
    sev_label = sev_labels.get(severity, severity)

    st.markdown(
        f"""
        <div class="detail-header">
            <strong style="font-size:16px;">{type_label}</strong>
            <span class="severity-badge {severity}" style="margin-left:8px;">{sev_label}</span>
            <div style="font-size:12px;color:#64748B;margin-top:4px;">{begin_str}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    track_points = details.get("track_points", pd.DataFrame())
    has_coords = (
        not track_points.empty
        and "latitude" in track_points.columns
        and "longitude" in track_points.columns
    )
    if has_coords:
        map_df = track_points[["latitude", "longitude"]].dropna()
        if not map_df.empty:
            st.map(map_df, use_container_width=True)
    else:
        lat = alarm_row.get("Latitude")
        lon = alarm_row.get("Longitude")
        if pd.notna(lat) and pd.notna(lon):
            st.map(pd.DataFrame({"latitude": [float(lat)], "longitude": [float(lon)]}), use_container_width=True)
        else:
            st.caption("Координаты недоступны")

    videos = details.get("videos", pd.DataFrame())
    st.markdown("**📹 Видео**")
    if not videos.empty and "media_relative_path" in videos.columns:
        for _, vrow in videos.iterrows():
            rel_path = str(vrow.get("media_relative_path", ""))
            channel = str(vrow.get("channel", "?"))
            duration = float(vrow.get("duration_seconds", 0)) if pd.notna(vrow.get("duration_seconds")) else 0
            local_path = PROJECT_ROOT / rel_path
            st.caption(f"Канал {channel} — {duration:.1f} сек")
            if local_path.exists():
                st.video(str(local_path), format="video/mp4", start_time=0)
            else:
                st.caption(f"(файл не найден: {rel_path})")
    else:
        st.caption("Нет видеофайлов для этого аларма.")

    st.markdown("**📊 Данные**")
    c1, c2, c3 = st.columns(3)
    c1.metric("Скорость (км/ч)", f"{speed:.0f}")
    c2.metric("Лимит (км/ч)", str(speed_limit))
    exceeded = max(0, speed - speed_limit)
    c3.metric("Превышение", f"+{exceeded:.0f}" if exceeded > 0 else "—")
    lat_val = alarm_row.get("Latitude")
    lon_val = alarm_row.get("Longitude")
    camera = str(alarm_row.get("CameraIds", "—"))
    if pd.notna(lat_val) and pd.notna(lon_val):
        st.caption(f"📍 {float(lat_val):.5f}, {float(lon_val):.5f} | Камера: {camera}")
    else:
        st.caption(f"Камера: {camera}")

    st.markdown("**Контекст**")
    chips: list[str] = []
    try:
        if begin_str and begin_str != "—":
            hour = pd.Timestamp(begin_str).hour
            if 22 <= hour or hour < 6:
                chips.append(
                    '<span class="context-chip" style="background:#EDE9FE;color:#5B21B6;">🌙 Ночное время</span>'
                )
            else:
                chips.append(
                    '<span class="context-chip" style="background:#DBEAFE;color:#1E40AF;">☀️ Дневное время</span>'
                )
    except (ValueError, TypeError):
        pass

    if exceeded > 0:
        chips.append(
            f'<span class="context-chip" style="background:#FEE2E2;color:#991B1B;">⚠ Превышение +{exceeded:.0f} км/ч</span>'
        )
    chips.append(
        f'<span class="context-chip" style="background:#F1F5F9;color:#475569;">🏷 {type_label}</span>'
    )
    # route / continuous time chips (demo)
    chips.append(
        '<span class="context-chip" style="background:#E0F2FE;color:#0C4A6E;">🛣️ Городская трасса</span>'
    )
    if chips:
        st.markdown('<div style="line-height:2;">' + "".join(chips) + "</div>", unsafe_allow_html=True)

    st.markdown("**Действия**")
    ac1, ac2 = st.columns(2)
    with ac1:
        st.button("📥 Скачать видео", disabled=True, key=f"dl_video_{alarm_id}",
                  help="Демо-режим: скачивание недоступно.", use_container_width=True)
    with ac2:
        if st.button("📋 Открыть карточку", key=f"open_card_{alarm_id}", use_container_width=True):
            st.session_state["selected_alarm_id"] = alarm_id
            st.session_state["active_tab"] = "🔍 Карточка инцидента"
            st.rerun()


def _render_track_overview(
    datasets: dict[str, pd.DataFrame],
    driver_alarms: pd.DataFrame,
    colors: dict,
) -> None:
    st.markdown("#### Обзор трека")
    if driver_alarms.empty or "TrackPointCount" not in driver_alarms.columns:
        st.info("Выберите нарушение в таблице для просмотра деталей.")
        return

    track_alarms = driver_alarms[driver_alarms["TrackPointCount"] > 0]
    if track_alarms.empty:
        st.info("Нет данных трека для выбранного водителя.")
        return

    last_alarm_id = track_alarms.iloc[0]["AlarmId"]
    details = get_alarm_details(datasets, last_alarm_id)
    track_points = details.get("track_points", pd.DataFrame())
    if not track_points.empty and "speed_kmh" in track_points.columns:
        chart_colors = colors.get("chart_colors", ["#3B82F6"])
        chart = build_track_speed_chart(track_points, last_alarm_id, chart_colors)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Нет данных трека для визуализации.")


def _state_a(datasets: dict[str, pd.DataFrame]) -> None:
    mic_active = st.session_state.get("report_mic_active", False)

    st.markdown(
        """
        <div class="report-empty">
            <div class="empty-icon">📄</div>
            <div class="empty-title">Сформируйте отчёт</div>
            <div class="empty-sub">Опишите что хотите увидеть — система построит отчёт автоматически</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, mid, _ = st.columns([1, 3, 1])
    with mid:
        if mic_active:
            st.markdown(
                '<div style="text-align:right;color:#DC2626;font-size:12px;">● Слушаю…</div>',
                unsafe_allow_html=True,
            )
            placeholder = "Говорите — речь появится здесь..."
        else:
            placeholder = "Покажи нарушения по ВА и телематике у Иванова за последние три дня"

        query = st.text_area(
            "NL-запрос",
            value=st.session_state.get("report_query_text", ""),
            placeholder=placeholder,
            label_visibility="collapsed",
            height=80,
            key="_report_query_input",
        )

        col_mic, col_submit = st.columns([1, 5])
        with col_mic:
            mic_cls = "mic-btn-active" if mic_active else ""
            st.markdown(f'<div class="{mic_cls}">', unsafe_allow_html=True)
            if st.button("🎤", key="_report_mic", help="Голосовой ввод (демо)", use_container_width=True):
                st.session_state["report_mic_active"] = not mic_active
                if st.session_state["report_mic_active"]:
                    st.toast("🎤 Запись голосового запроса началась (демо)")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown('<div class="mic-hint">faster-whisper<br>RU · KK · EN</div>', unsafe_allow_html=True)
        with col_submit:
            submitted = st.button(
                "✈ Сформировать отчёт", type="primary", use_container_width=True, key="_report_submit"
            )

        st.markdown('<div class="preset-divider">или выберите готовый:</div>', unsafe_allow_html=True)

        preset_cols = st.columns(2)
        for idx, (emoji, label, key) in enumerate(_PRESETS):
            col = preset_cols[idx % 2]
            if col.button(f"{emoji} {label}", key=f"_preset_{key}", use_container_width=True):
                st.session_state["report_preset"] = key
                st.session_state["report_query_text"] = label
                st.session_state["report_show_confirm"] = True
                st.session_state["report_confirmed"] = False
                alarms_df = datasets.get("selected_video_alarms")
                if key == "driver_3d":
                    if alarms_df is not None and "UnitStateNumber" in alarms_df.columns:
                        first = alarms_df["UnitStateNumber"].iloc[0]
                        st.session_state["report_driver_id"] = first
                else:
                    st.session_state["report_driver_id"] = "__fleet__"
                st.rerun()

    if submitted and query.strip():
        alarms_df = datasets.get("selected_video_alarms")
        if alarms_df is not None and "UnitStateNumber" in alarms_df.columns:
            q = query.strip()
            st.session_state["report_query_text"] = q
            # try exact match on plate
            matches = alarms_df[alarms_df["UnitStateNumber"].str.contains(q, case=False, na=False)]
            if matches.empty and "UnitName" in alarms_df.columns:
                matches = alarms_df[alarms_df["UnitName"].str.contains(q, case=False, na=False)]
            if not matches.empty:
                driver_ids = matches["UnitStateNumber"].unique()
                if len(driver_ids) == 1:
                    st.session_state["report_driver_id"] = driver_ids[0]
                    st.session_state["report_show_confirm"] = True
                    st.session_state["report_confirmed"] = False
                    st.rerun()
                else:
                    st.info(f"Найдено {len(driver_ids)} совпадений. Выберите водителя:")
                    for did in driver_ids[:10]:
                        if st.button(did, key=f"_nl_driver_{did}"):
                            st.session_state["report_driver_id"] = did
                            st.session_state["report_show_confirm"] = True
                            st.session_state["report_confirmed"] = False
                            st.rerun()
            else:
                # fallback: fleet report
                st.session_state["report_driver_id"] = "__fleet__"
                st.session_state["report_show_confirm"] = True
                st.session_state["report_confirmed"] = False
                st.rerun()
        else:
            st.info("Текстовые запросы недоступны: нет данных о госномерах.")


def _state_b(datasets: dict[str, pd.DataFrame]) -> None:
    driver_id = st.session_state.get("report_driver_id")
    preset = st.session_state.get("report_preset")
    query_text = st.session_state.get("report_query_text", "")

    # Resolve driver name / period for display
    unit_name = "—"
    period = "—"
    data_type = "Видео + телематика"

    if driver_id and driver_id != "__fleet__":
        vehicle_row = _get_vehicle_row(datasets, driver_id)
        if vehicle_row is not None:
            unit_name = str(vehicle_row.get("unit_name", driver_id))
        else:
            unit_name = driver_id
        driver_alarms = _get_driver_alarms(datasets, driver_id)
        period = _format_period(driver_alarms)
    else:
        unit_name = "Все водители / Весь парк"
        alarms_df = datasets.get("selected_video_alarms")
        if alarms_df is not None and "Begin" in alarms_df.columns:
            begins = pd.to_datetime(alarms_df["Begin"], utc=True, errors="coerce").dropna()
            if not begins.empty:
                period = f"{begins.min():%d.%m.%Y} — {begins.max():%d.%m.%Y}"
        data_type = "Сводка по парку"

    confidence = random.randint(90, 98)
    driver_display = (
        f"{unit_name} · {driver_id}" if driver_id and driver_id != "__fleet__" else unit_name
    )

    _, mid, _ = st.columns([1, 3, 1])
    with mid:
        st.markdown(
            f"""
            <div class="modal-box">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:2px;">
                    <span style="font-size:22px;">🤖</span>
                    <h4 style="margin:0;">Вот как я понял ваш запрос</h4>
                </div>
                <div style="font-size:13px;color:#64748B;margin-bottom:16px;">
                    Проверьте параметры перед построением отчёта
                </div>
                <div class="confirm-row">
                    <span class="row-icon">👤</span>
                    <div>
                        <div class="row-label">Водитель</div>
                        <div class="row-value">{driver_display}</div>
                    </div>
                </div>
                <div class="confirm-row">
                    <span class="row-icon">📅</span>
                    <div>
                        <div class="row-label">Период</div>
                        <div class="row-value">{period}</div>
                    </div>
                </div>
                <div class="confirm-row">
                    <span class="row-icon">📊</span>
                    <div>
                        <div class="row-label">Тип данных</div>
                        <div class="row-value">{data_type}
                            <span class="confirm-tag" style="background:#EFF6FF;color:#1E40AF;">📷 ВА</span>
                            <span class="confirm-tag" style="background:#FFFBEB;color:#B45309;">📡 Телематика</span>
                        </div>
                    </div>
                </div>
                <div style="font-size:12px;color:#64748B;margin-top:14px;">
                    ● Уверенность распознавания: <strong>{confidence}%</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("✏️ Уточнить запрос", key="_report_refine", use_container_width=True):
                st.session_state["report_show_confirm"] = False
                st.session_state["report_confirmed"] = False
                st.rerun()
        with c2:
            if st.button("✅ Всё верно — показать отчёт", type="primary", key="_report_confirm", use_container_width=True):
                st.session_state["report_confirmed"] = True
                st.session_state["report_show_confirm"] = False
                st.rerun()


def _state_c(
    datasets: dict[str, pd.DataFrame],
    alarm_type_labels: dict[str, str],
    colors: dict,
    speed_limit: int,
) -> None:
    driver_id = st.session_state["report_driver_id"]
    query_text = st.session_state.get("report_query_text", "")

    driver_alarms = _get_driver_alarms(datasets, driver_id)
    vehicle_row = _get_vehicle_row(datasets, driver_id)

    total_alarms = len(driver_alarms)
    critical_count = int(driver_alarms["IsCritical"].sum()) if "IsCritical" in driver_alarms.columns else 0
    mileage = float(vehicle_row.get("total_track_mileage_km", 0) or 0) if vehicle_row is not None else 0.0
    period = _format_period(driver_alarms)

    st.markdown(f"**{query_text}**")
    st.caption(f"Период: {period} | Нарушений: {total_alarms} | Пробег: {mileage:.1f} км")

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("✏️ Изменить запрос", key="_report_edit_query"):
            _reset_report()
            st.rerun()
    with c2:
        st.button("📄 Скачать PDF", disabled=True, key="_report_pdf", help="Демо-режим: экспорт недоступен.")

    left_col, right_col = st.columns([0.55, 0.45])

    with left_col:
        _render_driver_card(driver_id, driver_alarms, vehicle_row, speed_limit)
        _render_severe_banner(critical_count)

        st.markdown("#### Нарушения")
        selected_alarm = _render_violations_table(
            driver_alarms, alarm_type_labels, speed_limit, "_driver_violations"
        )
        if selected_alarm:
            st.session_state["report_selected_alarm_id"] = selected_alarm

    with right_col:
        selected_id = st.session_state.get("report_selected_alarm_id")
        if selected_id:
            _render_detail_panel(selected_id, datasets, alarm_type_labels, colors, speed_limit)
        else:
            _render_track_overview(datasets, driver_alarms, colors)


def _state_c2(
    datasets: dict[str, pd.DataFrame],
    alarm_type_labels: dict[str, str],
    colors: dict,
    speed_limit: int,
) -> None:
    query_text = st.session_state.get("report_query_text", "")

    alarms_df = datasets.get("selected_video_alarms")
    risk_table = build_risk_table(datasets)
    vehicles_df = datasets.get("vehicles")

    if alarms_df is None or alarms_df.empty:
        st.warning("Нет данных об алармах.")
        return

    # Determine view mode
    view_mode = st.session_state.get("report_fleet_view_mode", "Водители")
    st.markdown(f"**{query_text}**")

    # Summary stats
    total_alarms = len(risk_table) if not risk_table.empty else len(alarms_df)
    video_count = int((risk_table["VideoCount"] > 0).sum()) if not risk_table.empty and "VideoCount" in risk_table.columns else 0
    telemetry_count = int((risk_table["TrackPointCount"] > 0).sum()) if not risk_table.empty and "TrackPointCount" in risk_table.columns else 0
    critical_count = int(risk_table["IsCritical"].sum()) if not risk_table.empty and "IsCritical" in risk_table.columns else 0

    # Period
    period = "—"
    if "Begin" in alarms_df.columns:
        begins = pd.to_datetime(alarms_df["Begin"], utc=True, errors="coerce").dropna()
        if not begins.empty:
            period = f"{begins.min():%d.%m.%Y} — {begins.max():%d.%m.%Y}"

    drivers_or_vehicles = (
        risk_table["UnitStateNumber"].nunique()
        if not risk_table.empty and "UnitStateNumber" in risk_table.columns
        else alarms_df["UnitStateNumber"].nunique()
    )

    st.caption(f"Период: {period} | Водителей/ТС: {drivers_or_vehicles} | Нарушений: {total_alarms}")

    toggle_val = st.toggle("Показать по ТС", value=(view_mode == "ТС"), key="_fleet_toggle")
    st.session_state["report_fleet_view_mode"] = "ТС" if toggle_val else "Водители"

    # KPI row
    kpi_items = [
        ("Всего нарушений", total_alarms, "default"),
        ("Видео-детекции", video_count, "video"),
        ("Телематика", telemetry_count, "telemetry"),
        ("Грубых", critical_count, "critical"),
        ("Водителей" if not toggle_val else "ТС", drivers_or_vehicles, "default"),
    ]
    cards_html = "".join(_kpi_card(label, value, kind) for label, value, kind in kpi_items)
    st.markdown(f'<div class="kpi-row-custom">{cards_html}</div>', unsafe_allow_html=True)

    # Build fleet list
    if not risk_table.empty and "UnitStateNumber" in risk_table.columns:
        risk_table["Severity"] = risk_table.apply(lambda r: _get_severity(r, speed_limit), axis=1)
        grouped = risk_table.groupby("UnitStateNumber").agg(
            AlarmCount=("AlarmId", "count"),
            VideoCount=("VideoCount", lambda x: int((x > 0).sum())),
            TrackCount=("TrackPointCount", lambda x: int((x > 0).sum())),
            CriticalCount=("Severity", lambda x: int((x == "critical").sum())),
            MaxSpeed=("Speed", "max"),
        ).reset_index()
    else:
        grouped = (
            alarms_df.groupby("UnitStateNumber")
            .size()
            .reset_index(name="AlarmCount")
        )
        grouped["VideoCount"] = 0
        grouped["TrackCount"] = 0
        grouped["CriticalCount"] = 0
        grouped["MaxSpeed"] = 0.0

    # Merge vehicle names
    if vehicles_df is not None and "unit_state_number" in vehicles_df.columns and "unit_name" in vehicles_df.columns:
        vmap = vehicles_df[["unit_state_number", "unit_name"]].copy()
        vmap.columns = ["UnitStateNumber", "UnitName"]
        grouped = grouped.merge(vmap, on="UnitStateNumber", how="left")
    else:
        grouped["UnitName"] = grouped["UnitStateNumber"]

    grouped = grouped.sort_values("AlarmCount", ascending=False).head(30)

    left_col, right_col = st.columns([0.55, 0.45])

    with left_col:
        st.markdown("#### Список")
        for _, row in grouped.iterrows():
            unit_sn = str(row["UnitStateNumber"])
            unit_name = str(row.get("UnitName", unit_sn))
            initials = _get_initials(unit_name)
            alarms = int(row["AlarmCount"])
            video = int(row["VideoCount"])
            telem = int(row["TrackCount"])
            crit = int(row["CriticalCount"])
            # risk bar color
            if crit > 0:
                risk_color = "#DC2626"
                risk_width = min(100, 30 + crit * 10)
            elif alarms > 5:
                risk_color = "#F59E0B"
                risk_width = min(100, 20 + alarms * 5)
            else:
                risk_color = "#16A34A"
                risk_width = max(10, alarms * 5)

            crit_badges = ""
            if crit > 0:
                crit_badges += f'<span class="severity-badge critical" style="margin-left:6px;">Грубых {crit}</span>'

            sources_html = ""
            if video > 0:
                sources_html += f'<span style="font-size:12px;margin-right:8px;">📹 {video}</span>'
            if telem > 0:
                sources_html += f'<span style="font-size:12px;margin-right:8px;">📡 {telem}</span>'

            selected = st.session_state.get("report_fleet_selected_driver") == unit_sn
            border_color = "#3B82F6" if selected else "#E2E8F0"

            st.markdown(
                f"""
                <div style="background:#FFFFFF;border:1px solid {border_color};border-radius:10px;padding:10px 12px;margin-bottom:8px;cursor:pointer;"
                     onclick="">
                    <div style="display:flex;align-items:center;justify-content:space-between;">
                        <div style="display:flex;align-items:center;">
                            <span class="fleet-initials">{initials}</span>
                            <div>
                                <div style="font-weight:600;font-size:14px;">{unit_name} <span style="font-size:12px;color:#64748B;">{unit_sn}</span>{crit_badges}</div>
                                <div style="font-size:12px;color:#64748B;margin-top:2px;">
                                    {sources_html}
                                    <span class="risk-bar-bg"><span class="risk-bar-fill" style="width:{risk_width}%;background:{risk_color};"></span></span>
                                </div>
                            </div>
                        </div>
                        <div style="font-weight:700;font-size:16px;color:#0F172A;">{alarms}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Use a tiny button below each card for selection (HTML onclick unreliable in Streamlit)
            if st.button("Выбрать", key=f"_fleet_sel_{unit_sn}", use_container_width=True):
                st.session_state["report_fleet_selected_driver"] = unit_sn
                st.rerun()

    with right_col:
        selected_driver = st.session_state.get("report_fleet_selected_driver")
        if selected_driver:
            sel_alarms = _get_driver_alarms(datasets, selected_driver)
            sel_vehicle = _get_vehicle_row(datasets, selected_driver)
            _render_driver_card(selected_driver, sel_alarms, sel_vehicle, speed_limit)
            # mini violations (last 5)
            st.markdown("**Последние нарушения**")
            mini = _build_violations_table_df(sel_alarms, alarm_type_labels, speed_limit).head(5)
            if not mini.empty:
                st.dataframe(mini, use_container_width=True)
            else:
                st.caption("Нет нарушений")
        else:
            st.info("Выберите водителя или ТС из списка слева для просмотра мини-дашборда.")


def render_interactive_report(
    datasets: dict[str, pd.DataFrame],
    alarm_type_labels: dict[str, str],
    colors: dict,
    speed_limit_kmh: int,
) -> None:
    _init_report_session()
    _inject_css()

    alarms_df = datasets.get("selected_video_alarms")
    if alarms_df is None or alarms_df.empty:
        st.warning("Нет данных об алармах. Загрузите CSV-файлы в ./data.")
        return

    show_confirm = st.session_state.get("report_show_confirm", False)
    confirmed = st.session_state.get("report_confirmed", False)
    driver_id = st.session_state.get("report_driver_id")

    if show_confirm:
        _state_b(datasets)
        return

    if confirmed and driver_id and driver_id != "__fleet__":
        _state_c(datasets, alarm_type_labels, colors, speed_limit_kmh)
        return

    if confirmed and driver_id == "__fleet__":
        _state_c2(datasets, alarm_type_labels, colors, speed_limit_kmh)
        return

    # default empty state
    _state_a(datasets)
