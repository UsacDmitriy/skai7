from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from backend.metrics import get_alarm_details
from backend.risk_table import build_risk_table, build_vehicle_summary
from backend.charts import build_track_speed_chart

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_CRITICAL_TYPES = frozenset({"Sabotage", "Drowsiness", "DangerousDistance"})

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
</style>
"""


def _init_report_session() -> None:
    defaults = {
        "report_preset": None,
        "report_driver_id": None,
        "report_selected_alarm_id": None,
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
    is_critical = bool(row.get("IsCritical", False))
    if is_critical:
        return "critical"
    speed = float(row.get("Speed", 0)) if pd.notna(row.get("Speed")) else 0
    if speed > speed_limit * 1.3:
        return "high"
    if speed > speed_limit:
        return "medium"
    return "low"


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
    critical_count = int(driver_alarms["IsCritical"].sum()) if "IsCritical" in driver_alarms.columns else 0

    mileage = 0.0
    alarm_types_str = ""
    video_downloaded = 0
    if vehicle_row is not None:
        mileage = float(vehicle_row.get("total_track_mileage_km", 0) or 0)
        alarm_types_str = str(vehicle_row.get("alarm_types", "") or "")
        video_downloaded = int(vehicle_row.get("downloaded_video_count", 0) or 0)

    period = "—"
    if not driver_alarms.empty and "Begin" in driver_alarms.columns:
        begins = pd.to_datetime(driver_alarms["Begin"], utc=True, errors="coerce").dropna()
        if not begins.empty:
            period = f"{begins.min():%d.%m.%Y} — {begins.max():%d.%m.%Y}"

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
                <span><span class="info-label">Всего алармов</span><br>{total_alarms}</span>
                <span><span class="info-label">Типы алармов</span><br>{alarm_types_str}</span>
                <span><span class="info-label">Видео скачано</span><br>{video_downloaded}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    kpi_items = [
        ("Всего нарушений", total_alarms, "default"),
        ("Видео-детекции", video_detections, "video"),
        ("Телематика", track_detections, "telemetry"),
        ("Критических", critical_count, "critical"),
    ]
    st.markdown('<div class="kpi-row-custom">', unsafe_allow_html=True)
    for label, value, kind in kpi_items:
        css_class = f" {kind}" if kind != "default" else ""
        st.markdown(
            f'<div class="kpi-card-custom{css_class}">'
            f'<div class="kpi-value">{value}</div>'
            f'<div class="kpi-label">{label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)


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


def _render_violations_table(
    driver_alarms: pd.DataFrame,
    alarm_type_labels: dict[str, str],
    speed_limit: int,
    table_key: str,
) -> str | None:
    if driver_alarms.empty:
        st.info("Нет нарушений для отображения.")
        return None

    df = driver_alarms.copy()
    df = df.sort_values("Begin", ascending=False)
    df["Severity"] = df.apply(lambda r: _get_severity(r, speed_limit), axis=1)
    df["TypeLabel"] = df["Type"].map(alarm_type_labels).fillna(df["Type"])

    display = df[["AlarmId", "Begin", "TypeLabel", "Speed", "Severity"]].copy()
    display.columns = ["AlarmId", "Дата·Время", "Нарушение", "Скорость", "Severity"]
    display["Score"] = (display["Скорость"].fillna(0) / speed_limit * 100).round(0).astype(int)
    display["Северити"] = display["Severity"]

    severity_config = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🔵",
        "low": "🟢",
    }
    display["Северити"] = display["Severity"].map(severity_config).fillna("⚪")

    show_cols = ["Дата·Время", "Нарушение", "Скорость", "Score", "Северити"]
    styled = display[show_cols].copy()
    styled = styled.reset_index(drop=True)
    styled.index = range(1, len(styled) + 1)
    styled.index.name = "#"

    event = st.dataframe(
        styled,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        key=table_key,
        column_config={
            "Скорость": st.column_config.NumberColumn(format="%.0f км/ч"),
            "Score": st.column_config.NumberColumn(format="%d%%"),
        },
    )

    selected_rows = event.selection.get("rows", [])
    if selected_rows:
        original_idx = selected_rows[0]
        return str(df.iloc[original_idx]["AlarmId"])
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

    severity_labels = {"critical": "Критическое", "high": "Высокое", "medium": "Среднее", "low": "Низкое"}
    sev_label = severity_labels.get(severity, severity)

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
                st.video(str(local_path), format="video/mp4", start_time="0")
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
    if pd.notna(lat_val) and pd.notna(lon_val):
        st.caption(f"📍 {float(lat_val):.5f}, {float(lon_val):.5f}")

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
            st.toast(f"Инцидент {alarm_id[:8]}… открыт во вкладке «Детали»")


def _render_driver_report(
    datasets: dict[str, pd.DataFrame],
    alarm_type_labels: dict[str, str],
    colors: dict,
    speed_limit: int,
) -> None:
    driver_id = st.session_state["report_driver_id"]
    alarms_df = datasets.get("selected_video_alarms")
    vehicles_df = datasets.get("vehicles")

    if alarms_df is None or alarms_df.empty:
        st.warning("Нет данных об алармах.")
        return

    if st.button("← К выбору водителя", key="_report_back_driver"):
        st.session_state["report_driver_id"] = None
        st.session_state["report_selected_alarm_id"] = None
        st.rerun()

    risk_table = build_risk_table(datasets)
    driver_alarms = (
        risk_table[risk_table["UnitStateNumber"] == driver_id].copy()
        if not risk_table.empty and "UnitStateNumber" in risk_table.columns
        else pd.DataFrame()
    )
    if driver_alarms.empty and "UnitStateNumber" in alarms_df.columns:
        raw_alarms = alarms_df[alarms_df["UnitStateNumber"] == driver_id].copy()
        driver_alarms = raw_alarms

    vehicle_row = None
    if vehicles_df is not None and "unit_state_number" in vehicles_df.columns:
        vmask = vehicles_df["unit_state_number"] == driver_id
        if vmask.any():
            vehicle_row = vehicles_df[vmask].iloc[0]

    left_col, right_col = st.columns([0.55, 0.45])

    with left_col:
        _render_driver_card(driver_id, driver_alarms, vehicle_row, speed_limit)

        critical_count = (
            int(driver_alarms["IsCritical"].sum())
            if not driver_alarms.empty and "IsCritical" in driver_alarms.columns
            else 0
        )
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
            st.markdown("#### Обзор трека")
            if not driver_alarms.empty and "TrackPointCount" in driver_alarms.columns:
                track_alarms = driver_alarms[driver_alarms["TrackPointCount"] > 0]
                if not track_alarms.empty:
                    last_alarm_id = track_alarms.iloc[0]["AlarmId"]
                    details = get_alarm_details(datasets, last_alarm_id)
                    track_points = details.get("track_points", pd.DataFrame())
                    if not track_points.empty and "speed_kmh" in track_points.columns:
                        chart_colors = colors.get("chart_colors", ["#3B82F6"])
                        chart = build_track_speed_chart(track_points, last_alarm_id, chart_colors)
                        st.altair_chart(chart, use_container_width=True)
                    else:
                        st.info("Нет данных трека для визуализации.")
                else:
                    st.info("Нет данных трека для выбранного водителя.")
            else:
                st.info("Выберите нарушение в таблице для просмотра деталей.")


def _render_all_alarms_fleet(
    datasets: dict[str, pd.DataFrame],
    alarm_type_labels: dict[str, str],
    colors: dict,
    speed_limit: int,
) -> None:
    alarms_df = datasets.get("selected_video_alarms")
    if alarms_df is None or alarms_df.empty:
        st.warning("Нет данных об алармах.")
        return

    risk_table = build_risk_table(datasets)
    if risk_table.empty:
        st.warning("Нет данных для отображения.")
        return

    left_col, right_col = st.columns([0.55, 0.45])

    with left_col:
        st.markdown("#### Все алармы")

        display = risk_table.copy()
        display["TypeLabel"] = display["Type"].map(alarm_type_labels).fillna(display["Type"])
        display["BeginStr"] = display["Begin"].astype(str).str[:19]
        severity_icons = {"critical": "🔴", "high": "🟠", "medium": "🔵", "low": "🟢"}

        def _sev_icon(row: pd.Series) -> str:
            sev = _get_severity(row, speed_limit)
            return severity_icons.get(sev, "⚪")

        display["Крит."] = display.apply(_sev_icon, axis=1)

        show = display[["AlarmId", "UnitStateNumber", "TypeLabel", "Speed", "BeginStr", "VideoCount", "Крит."]].copy()
        show.columns = ["AlarmId", "Госномер", "Тип", "Скорость", "Время", "Видео", "Крит."]

        event = st.dataframe(
            show,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
            key="_fleet_alarms",
            column_config={
                "Скорость": st.column_config.NumberColumn(format="%.0f км/ч"),
            },
        )
        selected_rows = event.selection.get("rows", [])
        if selected_rows:
            st.session_state["report_selected_alarm_id"] = str(show.iloc[selected_rows[0]]["AlarmId"])

    with right_col:
        selected_id = st.session_state.get("report_selected_alarm_id")
        if selected_id:
            _render_detail_panel(selected_id, datasets, alarm_type_labels, colors, speed_limit)
        else:
            st.info("Выберите аларм в таблице для просмотра деталей.")


def _render_empty_state(colors: dict) -> None:
    st.markdown("## 📊 Интерактивный отчёт")
    st.caption("Выберите водителя или сформируйте запрос")

    query = st.text_area(
        "NL-запрос",
        placeholder="Например: покажи все нарушения по водителю Т780РН198",
        label_visibility="collapsed",
        height=80,
        key="_report_query",
    )

    _, btn_col, _ = st.columns([1, 1, 1])
    with btn_col:
        submitted = st.button("Сформировать отчёт", type="primary", use_container_width=True)

    st.markdown("---")
    st.caption("Быстрые пресеты")

    preset_cols = st.columns(4)
    presets = [
        ("🚗 Топ-5 нарушителей", "top5"),
        ("⚠ Критические события", "critical"),
        ("📹 Только с видео", "video"),
        ("🌙 Все алармы", "all"),
    ]
    for col, (label, key) in zip(preset_cols, presets):
        if col.button(label, key=f"_preset_{key}", use_container_width=True):
            st.session_state["report_preset"] = key
            st.session_state["report_driver_id"] = None
            st.session_state["report_selected_alarm_id"] = None
            st.rerun()

    if submitted and query.strip():
        alarms_df = st.session_state.get("datasets", {}).get("selected_video_alarms")
        if alarms_df is not None and "UnitStateNumber" in alarms_df.columns:
            q = query.strip()
            matches = alarms_df[alarms_df["UnitStateNumber"].str.contains(q, case=False, na=False)]
            if not matches.empty:
                driver_ids = matches["UnitStateNumber"].unique()
                if len(driver_ids) == 1:
                    st.session_state["report_driver_id"] = driver_ids[0]
                    st.session_state["report_preset"] = None
                    st.session_state["report_selected_alarm_id"] = None
                    st.rerun()
                else:
                    st.info(f"Найдено {len(driver_ids)} совпадений. Выберите водителя:")
                    for did in driver_ids[:10]:
                        if st.button(did, key=f"_nl_driver_{did}"):
                            st.session_state["report_driver_id"] = did
                            st.session_state["report_preset"] = None
                            st.session_state["report_selected_alarm_id"] = None
                            st.rerun()
            else:
                st.warning("Ничего не найдено. Попробуйте изменить запрос.")
        else:
            st.info("Текстовые запросы недоступны: нет данных о госномерах.")


def _resolve_driver_from_preset(
    preset: str,
    datasets: dict[str, pd.DataFrame],
    alarm_type_labels: dict[str, str],
    colors: dict,
    speed_limit: int,
) -> None:
    if st.button("← К пресетам", key="_report_back_preset"):
        st.session_state["report_preset"] = None
        st.session_state["report_driver_id"] = None
        st.session_state["report_selected_alarm_id"] = None
        st.rerun()

    alarms_df = datasets.get("selected_video_alarms")
    vehicles_df = datasets.get("vehicles")

    if preset == "all":
        _render_all_alarms_fleet(datasets, alarm_type_labels, colors, speed_limit)
        return

    if alarms_df is None or alarms_df.empty:
        st.warning("Нет данных об алармах.")
        return

    risk_table = build_risk_table(datasets)

    if preset == "top5":
        st.subheader("Топ-5 водителей по количеству нарушений")
        if vehicles_df is not None and "unit_state_number" in vehicles_df.columns:
            top_drivers = (
                vehicles_df.sort_values("alarm_count", ascending=False)
                .head(5)[["unit_state_number", "alarm_count", "alarm_types", "total_track_mileage_km"]]
            )
            top_drivers.columns = ["Госномер", "Нарушений", "Типы", "Пробег (км)"]
        else:
            if risk_table.empty or "UnitStateNumber" not in risk_table.columns:
                st.info("Недостаточно данных.")
                return
            top_drivers = (
                risk_table.groupby("UnitStateNumber")
                .size()
                .reset_index(name="Нарушений")
                .sort_values("Нарушений", ascending=False)
                .head(5)
            )

        for _, row in top_drivers.iterrows():
            driver_id = str(row.iloc[0])
            alarm_count = row.iloc[1] if len(row) > 1 else 0
            if st.button(f"{driver_id} — {alarm_count} нарушений", key=f"_top5_{driver_id}"):
                st.session_state["report_driver_id"] = driver_id
                st.rerun()

    elif preset == "critical":
        st.subheader("Критические события")
        if not risk_table.empty and "IsCritical" in risk_table.columns:
            critical = risk_table[risk_table["IsCritical"]]
        else:
            critical = alarms_df[alarms_df["Speed"] > speed_limit].copy()
        if critical.empty:
            st.info("Нет критических событий.")
            return
        critical["TypeLabel"] = critical["Type"].map(alarm_type_labels).fillna(critical["Type"])
        display = critical[["AlarmId", "UnitStateNumber", "TypeLabel", "Speed", "Begin"]].copy()
        display.columns = ["AlarmId", "Госномер", "Тип", "Скорость", "Время"]
        event = st.dataframe(display, use_container_width=True, on_select="rerun",
                             selection_mode="single-row", key="_critical_preset")
        selected = event.selection.get("rows", [])
        if selected:
            alarm_id = str(display.iloc[selected[0]]["AlarmId"])
            driver_id = str(display.iloc[selected[0]]["Госномер"])
            st.session_state["report_driver_id"] = driver_id
            st.session_state["report_selected_alarm_id"] = alarm_id
            st.rerun()

    elif preset == "video":
        st.subheader("Алармы с видео")
        with_video = alarms_df[alarms_df["VideoCount"] > 0].copy() if "VideoCount" in alarms_df.columns else pd.DataFrame()
        if with_video.empty:
            st.info("Нет алармов с видеозаписями.")
            return
        with_video["TypeLabel"] = with_video["Type"].map(alarm_type_labels).fillna(with_video["Type"])
        display = with_video[["AlarmId", "UnitStateNumber", "TypeLabel", "Speed", "Begin", "VideoCount"]].copy()
        display.columns = ["AlarmId", "Госномер", "Тип", "Скорость", "Время", "Видео"]
        event = st.dataframe(display, use_container_width=True, on_select="rerun",
                             selection_mode="single-row", key="_video_preset")
        selected = event.selection.get("rows", [])
        if selected:
            alarm_id = str(display.iloc[selected[0]]["AlarmId"])
            driver_id = str(display.iloc[selected[0]]["Госномер"])
            st.session_state["report_driver_id"] = driver_id
            st.session_state["report_selected_alarm_id"] = alarm_id
            st.rerun()


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

    driver_id = st.session_state.get("report_driver_id")
    preset = st.session_state.get("report_preset")

    if driver_id:
        _render_driver_report(datasets, alarm_type_labels, colors, speed_limit_kmh)
    elif preset:
        _resolve_driver_from_preset(preset, datasets, alarm_type_labels, colors, speed_limit_kmh)
    else:
        _render_empty_state(colors)
