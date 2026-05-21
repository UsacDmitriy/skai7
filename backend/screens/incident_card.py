from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from backend.constants import ALARM_TYPE_LABELS, COLORS, SPEED_LIMIT_KMH
from backend.data_loader import save_action

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASETS_DIR = PROJECT_ROOT / "datasets"
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

_ANALYSIS: dict[str, str] = {
    "Drowsiness":
    "Водитель не менял положение руля 40+ секунд. Возможен микросон.",
    "Sabotage":
    "Камера зафиксировала перекрытие объектива или отключение.",
    "Distraction":
    "Водитель отвлёкся от дороги более 3 секунд. Риск ДТП повышен.",
    "DangerousDistance":
    "Несоблюдение безопасной дистанции. Риск попутного столкновения.",
    "SharpAcceleration":
    "Резкое ускорение. Возможна агрессивная езда.",
    "Yawning":
    "Система зафиксировала зевание водителя — признак усталости.",
    "Smoking":
    "Водитель курит во время движения. Нарушение правил.",
    "SeatBelt":
    "Ремень не пристёгнут. Повышенный риск при ДТП.",
    "NoDriver":
    "Водитель отсутствует за рулём. Требуется проверка.",
}

_DEFAULT_ANALYSIS = "Событие зафиксировано. Требуется ручная проверка."


def _load_csv_max_50(path: Path) -> pd.DataFrame:
    """Читает CSV, максимум 50 строк."""
    try:
        return pd.read_csv(path, nrows=50)
    except Exception:
        return pd.DataFrame()


def _load_datasets() -> dict[str, pd.DataFrame]:
    result = {}
    for name in [
            "selected_video_alarms", "video_files", "track_summary",
            "track_points", "max_speed_points", "track_periods", "vehicles"
    ]:
        csv_path = DATA_DIR / f"{name}.csv"
        if csv_path.exists():
            result[name] = _load_csv_max_50(csv_path)
    return result


def _parse_camera_ids(raw: str) -> list[str]:
    if pd.isna(raw) or not raw:
        return []
    try:
        parsed = json.loads(str(raw))
        if isinstance(parsed, list):
            return [str(c) for c in parsed]
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    parts = str(raw).replace("'", '"').replace(" ", "").split(",")
    return [p.strip('"[] ') for p in parts if p.strip('"[] ')]


def _get_video_path(row: pd.Series) -> Path | None:
    media = row.get("media_relative_path", "")
    if pd.isna(media) or not media:
        return None
    p = PROJECT_ROOT / str(media)
    return p if p.exists() else None


def _format_duration(seconds: float) -> str:
    if pd.isna(seconds) or seconds <= 0:
        return "—"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def _get_alarm_detail(
    datasets: dict[str, pd.DataFrame],
    alarm_id: str,
) -> dict:
    alarms_df = datasets.get("selected_video_alarms")
    video_files_df = datasets.get("video_files")
    track_summary_df = datasets.get("track_summary")
    track_points_df = datasets.get("track_points")
    vehicles_df = datasets.get("vehicles")

    alarm_row = None
    if alarms_df is not None and "AlarmId" in alarms_df.columns:
        mask = alarms_df["AlarmId"] == alarm_id
        if mask.any():
            alarm_row = alarms_df[mask].iloc[0]

    videos = (video_files_df[video_files_df["alarm_id"] ==
                              alarm_id].reset_index(drop=True)
              if video_files_df is not None and "alarm_id" in
              video_files_df.columns else pd.DataFrame())

    track_summary = None
    if track_summary_df is not None and "alarm_id" in track_summary_df.columns:
        mask = track_summary_df["alarm_id"] == alarm_id
        if mask.any():
            track_summary = track_summary_df[mask].iloc[0]

    track_points = pd.DataFrame()
    if track_points_df is not None and "alarm_id" in track_points_df.columns:
        tp = track_points_df[track_points_df["alarm_id"] == alarm_id]
        if not tp.empty and "timestamp_utc" in tp.columns:
            tp = tp.sort_values("timestamp_utc").head(50)
        track_points = tp.reset_index(drop=True)

    vehicle = None
    if alarm_row is not None and vehicles_df is not None:
        unit_sn = alarm_row.get("UnitStateNumber")
        if pd.notna(unit_sn):
            mask = vehicles_df["unit_state_number"] == unit_sn
            if mask.any():
                vehicle = vehicles_df[mask].iloc[0]

    return {
        "alarm": alarm_row,
        "videos": videos,
        "track_summary": track_summary,
        "track_points": track_points,
        "vehicle": vehicle,
    }


def _render_selection(datasets: dict[str, pd.DataFrame]) -> None:
    alarms_df = datasets.get("selected_video_alarms")
    if alarms_df is None or alarms_df.empty:
        st.warning("Нет данных об алармах в ./data/")
        return

    alarm_ids = (alarms_df["AlarmId"].dropna().astype(str).unique().tolist()
                 if "AlarmId" in alarms_df.columns else [])

    if not alarm_ids:
        st.warning("Нет AlarmId в данных.")
        return

    st.markdown(
        '<div style="background:#0F172A;padding:24px;'
        'border-radius:12px;margin-bottom:16px;">'
        '<h2 style="color:#F1F5F9;font-family:-apple-system,'
        'sans-serif;margin:0 0 8px 0;">Выберите инцидент</h2>'
        '<p style="color:#94A3B8;font-size:14px;margin:0;">'
        f"Доступно: {len(alarm_ids)} событий</p></div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        selected = st.selectbox(
            "AlarmId",
            options=["—"] + alarm_ids,
            label_visibility="collapsed",
        )
    with col2:
        show = st.button(
            "Открыть инцидент",
            type="primary",
            use_container_width=True,
        )

    if show and selected != "—":
        st.session_state["selected_alarm_id"] = selected
        st.rerun()


_CSS = """
<style>
.kilo-incident-card {
    background: #0F172A;
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid #1E293B;
    max-width: 1100px;
}
.kilo-card-header {
    background: #1E293B;
    padding: 16px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid #334155;
}
.kilo-card-header-left {
    display: flex;
    align-items: center;
    gap: 12px;
}
.kilo-header-icon {
    width: 32px; height: 32px;
    background: #3B82F6;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
}
.kilo-header-title {
    font-family: -apple-system, sans-serif;
    font-weight: 700;
    font-size: 18px;
    color: #F1F5F9;
}
.kilo-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border-radius: 20px;
    font-family: -apple-system, sans-serif;
    font-weight: 600;
    font-size: 14px;
}
.kilo-body {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0;
}
.kilo-section {
    padding: 20px 24px;
}
.kilo-section + .kilo-section {
    border-left: 1px solid #1E293B;
}
.kilo-video-area {
    background: #020617;
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 16px;
    min-height: 140px;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
}
.kilo-video-placeholder {
    text-align: center;
    color: #475569;
    font-family: -apple-system, sans-serif;
}
.kilo-video-placeholder-icon {
    font-size: 36px;
    margin-bottom: 8px;
}
.kilo-live-badge {
    position: absolute;
    top: 8px;
    right: 8px;
    background: #DC2626;
    color: #fff;
    font-family: -apple-system, sans-serif;
    font-weight: 700;
    font-size: 11px;
    padding: 4px 10px;
    border-radius: 4px;
    letter-spacing: 0.5px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.kilo-live-dot {
    width: 6px; height: 6px;
    background: #fff;
    border-radius: 50%;
    animation: kilo-pulse 1.5s ease-in-out infinite;
}
@keyframes kilo-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}
.kilo-meta-row {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 12px;
}
.kilo-chip {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: 20px;
    font-family: -apple-system, sans-serif;
    font-size: 13px;
    font-weight: 500;
}
.kilo-chip-red { background: #1C1017; color: #FCA5A5; border: 1px solid #7F1D1D; }
.kilo-chip-blue { background: #0C1A2E; color: #93C5FD; border: 1px solid #1E3A5F; }
.kilo-chip-yellow { background: #1C1A0C; color: #FDE68A; border: 1px solid #78350F; }
.kilo-chip-green { background: #0C1F14; color: #86EFAC; border: 1px solid #14532D; }
.kilo-chip-purple { background: #1A0C2E; color: #D8B4FE; border: 1px solid #581C87; }
.kilo-chip-gray { background: #1E293B; color: #94A3B8; border: 1px solid #334155; }

.kilo-section-title {
    font-family: -apple-system, sans-serif;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #64748B;
    margin: 0 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #1E293B;
}
.kilo-field {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid #1E293B;
}
.kilo-field:last-child { border-bottom: none; }
.kilo-field-label {
    font-family: -apple-system, sans-serif;
    font-size: 13px;
    color: #64748B;
}
.kilo-field-value {
    font-family: -apple-system, sans-serif;
    font-size: 13px;
    color: #E2E8F0;
    font-weight: 500;
    text-align: right;
}
.kilo-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 18px;
    border-radius: 8px;
    font-family: -apple-system, sans-serif;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    border: none;
    width: 100%;
    justify-content: center;
}
.kilo-btn-primary {
    background: #16A34A;
    color: #fff;
}
.kilo-btn-primary:hover {
    background: #15803D;
}
.kilo-btn-secondary {
    background: #0369A1;
    color: #fff;
}
.kilo-btn-secondary:hover {
    background: #075985;
}
.kilo-btn-ghost {
    background: #1E293B;
    color: #94A3B8;
    border: 1px solid #334155;
}
.kilo-btn-ghost:hover {
    background: #334155;
    color: #E2E8F0;
}
.kilo-timeline {
    background: #1E293B;
    border-radius: 8px;
    padding: 12px;
    margin-top: 12px;
}
.kilo-timeline-bar {
    height: 6px;
    background: #334155;
    border-radius: 3px;
    position: relative;
    margin-bottom: 8px;
}
.kilo-timeline-active {
    position: absolute;
    height: 100%;
    background: #3B82F6;
    border-radius: 3px;
}
.kilo-timeline-labels {
    display: flex;
    justify-content: space-between;
    font-family: -apple-system, sans-serif;
    font-size: 10px;
    color: #64748B;
}
.kilo-alert-box {
    background: #1C1017;
    border: 1px solid #7F1D1D;
    border-radius: 8px;
    padding: 12px;
    margin: 12px 0;
}
.kilo-alert-title {
    font-family: -apple-system, sans-serif;
    font-size: 12px;
    font-weight: 600;
    color: #FCA5A5;
    margin-bottom: 4px;
}
.kilo-alert-text {
    font-family: -apple-system, sans-serif;
    font-size: 12px;
    color: #F87171;
    line-height: 1.4;
}
.kilo-video-table {
    width: 100%;
    font-family: -apple-system, sans-serif;
    font-size: 11px;
    color: #94A3B8;
    border-collapse: collapse;
    margin-top: 8px;
}
.kilo-video-table td {
    padding: 6px 8px;
    border-bottom: 1px solid #1E293B;
}
.kilo-video-table td:first-child {
    color: #64748B;
}
.kilo-back-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    background: transparent;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #94A3B8;
    font-family: -apple-system, sans-serif;
    font-size: 13px;
    cursor: pointer;
    margin-bottom: 12px;
}
.kilo-back-btn:hover {
    background: #1E293B;
    color: #E2E8F0;
}
</style>
"""


def _alarm_badge(type_str: str, speed: float) -> tuple[str, str]:
    label = ALARM_TYPE_LABELS.get(type_str, type_str)
    badge_map = {
        "Drowsiness": ("kilo-chip-red", "😴"),
        "Yawning": ("kilo-chip-red", "😴"),
        "Distraction": ("kilo-chip-yellow", "📱"),
        "Sabotage": ("kilo-chip-red", "📷"),
        "DangerousDistance": ("kilo-chip-yellow", "🚗"),
        "SharpAcceleration": ("kilo-chip-yellow", "⚡"),
        "Smoking": ("kilo-chip-purple", "🚬"),
        "SeatBelt": ("kilo-chip-blue", "🔒"),
        "NoDriver": ("kilo-chip-red", "🚫"),
    }
    chip_class, emoji = badge_map.get(type_str, ("kilo-chip-gray", "⚠"))
    return label, chip_class, emoji


def _render_incident_card(
    alarm_id: str,
    datasets: dict[str, pd.DataFrame],
    type_labels: dict[str, str],
) -> None:
    detail = _get_alarm_detail(datasets, alarm_id)
    alarm = detail["alarm"]

    if alarm is None:
        st.warning(f"Аларм '{alarm_id}' не найден.")
        return

    unit_sn = str(alarm.get("UnitStateNumber", "—"))
    raw_type = str(alarm.get("Type", "—"))
    speed_val = float(
        alarm["Speed"]) if pd.notna(alarm.get("Speed")) else 0.0
    begin = str(alarm.get("Begin", "—"))
    end = str(alarm.get("End", "—"))
    address = str(alarm.get("Address", ""))

    label, badge_class, badge_emoji = _alarm_badge(raw_type, speed_val)

    videos = detail["videos"]
    track_summary = detail["track_summary"]
    track_points = detail["track_points"]
    vehicle = detail["vehicle"]

    has_videos = not videos.empty
    first_video_path = _get_video_path(videos.iloc[0]) if has_videos else None

    total_mileage = (float(track_summary.get("total_mileage_km", 0))
                     if track_summary is not None and
                     pd.notna(track_summary.get("total_mileage_km")) else 0.0)
    total_duration = (
        track_summary.get("total_movement_duration", "—")
        if track_summary is not None else "—")
    parking_duration = (
        track_summary.get("total_parking_duration", "—")
        if track_summary is not None else "—")

    total_video_size = 0
    total_video_duration = 0.0
    if has_videos and "size_bytes" in videos.columns:
        total_video_size = int(videos["size_bytes"].sum())
    if has_videos and "duration_seconds" in videos.columns:
        total_video_duration = float(videos["duration_seconds"].sum())

    score = round(speed_val / SPEED_LIMIT_KMH * 100
                  ) if SPEED_LIMIT_KMH > 0 else 0

    ts = _format_timestamps(begin, end)
    chips_html = _build_chips(raw_type, speed_val, total_mileage, ts)

    analysis = _ALYSIS.get(raw_type, _DEFAULT_ANALYSIS)
    risk_level = "high" if speed_val > SPEED_LIMIT_KMH else ("medium" if
                                                             speed_val > 60 else
                                                             "low")
    risk_colors = {
        "high": "#DC2626",
        "medium": "#EAB308",
        "low": "#16A34A"
    }
    risk_labels = {
        "high": "Высокий риск",
        "medium": "Средний риск",
        "low": "Низкий риск"
    }
    risk_color = risk_colors[risk_level]

    timeline_percent = _calc_timeline(track_points, begin, end)

    html = f"""
<div class="kilo-incident-card">
    <div class="kilo-card-header">
        <div class="kilo-card-header-left">
            <div class="kilo-header-icon">📺</div>
            <span class="kilo-header-title">Карточка инцидента</span>
        </div>
        <div class="kilo-badge {badge_class}">
            <span>{badge_emoji}</span>
            <span>{label}</span>
        </div>
    </div>

    <div class="kilo-body">
        <!-- LEFT: Video -->
        <div class="kilo-section">
            <p class="kilo-section-title">Видео события</p>

            <div class="kilo-video-area">
                <div class="kilo-live-badge">
                    <div class="kilo-live-dot"></div>
                    LIVE
                </div>
    """

    if first_video_path:
        video_data_url = _encode_video_base64(first_video_path)
        html += f"""
                <video controls style="max-width:100%;border-radius:8px;" preload="metadata">
                    <source src="{video_data_url}" type="video/mp4">
                    Видео не поддерживается.
                </video>
        """
    else:
        html += """
                <div class="kilo-video-placeholder">
                    <div class="kilo-video-placeholder-icon">📷</div>
                    <div style="font-size:14px;">Нет видео для предпросмотра</div>
                </div>
        """

    html += """
            </div>
    """

    if has_videos:
        html += """<table class="kilo-video-table">"""
        for _, v in videos.head(5).iterrows():
            ch = int(v.get("channel", 0))
            dur = _format_duration(v.get("duration_seconds", 0))
            sz_bytes = int(v.get("size_bytes", 0))
            sz = (f"{sz_bytes / 1024 / 1024:.1f} МБ") if sz_bytes > 0 else "—"
            html += f"""<tr><td>Канал {ch}</td><td>{dur}</td><td>{sz}</td></tr>"""
        html += """</table>"""
    else:
        html += """<p style="color:#64748B;font-size:13px;margin-top:8px;">Нет связанных видео</p>"""

    video_count = int(alarm.get("VideoCount", 0)) if pd.notna(alarm.get(
        "VideoCount")) else 0
    html += f"""
            <div style="margin-top:12px;display:flex;gap:8px;">
                <span class="kilo-chip kilo-chip-blue">📹 Камер: {video_count}</span>
                <span class="kilo-chip kilo-chip-blue">💾 {total_video_size/1024/1024:.1f} МБ</span>
            </div>
        </div>

        <!-- RIGHT: Telemetry + Actions -->
        <div class="kilo-section">
            <p class="kilo-section-title">Телеметрия и контекст</p>

            <div class="kilo-meta-row">
                {chips_html}
            </div>

            <div class="kilo-field">
                <span class="kilo-field-label">Госномер</span>
                <span class="kilo-field-value">{unit_sn}</span>
            </div>
            <div class="kilo-field">
                <span class="kilo-field-label">Скорость</span>
                <span class="kilo-field-value" style="color:{risk_color};">{speed_val:.0f} км/ч</span>
            </div>
            <div class="kilo-field">
                <span class="kilo-field-label">Время</span>
                <span class="kilo-field-value">{begin} — {end}</span>
            </div>
    """

    if address and address != "nan":
        html += f"""
            <div class="kilo-field">
                <span class="kilo-field-label">Адрес</span>
                <span class="kilo-field-value">{address}</span>
            </div>
        """

    html += f"""
            <div class="kilo-field">
                <span class="kilo-field-label">Пробег трека</span>
                <span class="kilo-field-value">{total_mileage:.1f} км</span>
            </div>
            <div class="kilo-field">
                <span class="kilo-field-label">Движение</span>
                <span class="kilo-field-value">{total_duration}</span>
            </div>
            <div class="kilo-field">
                <span class="kilo-field-label">Стоянка</span>
                <span class="kilo-field-value">{parking_duration}</span>
            </div>
            <div class="kilo-field">
                <span class="kilo-field-label">Скорость / Лимит</span>
                <span class="kilo-field-value">{SPEED_LIMIT_KMH} км/ч</span>
            </div>
    """

    html += f"""
            <div class="kilo-timeline">
                <div class="kilo-timeline-bar">
                    <div class="kilo-timeline-active" style="width:{timeline_percent}%;left:0;"></div>
                </div>
                <div class="kilo-timeline-labels">
                    <span>{begin}</span>
                    <span>{end}</span>
                </div>
            </div>

            <div class="kilo-alert-box" style="border-color:{risk_color}40;background:{risk_color}10;">
                <div class="kilo-alert-title" style="color:{risk_color};">
                    ⚡ Анализ: {risk_labels[risk_level]}
                </div>
                <div class="kilo-alert-text" style="color:{risk_color}">{analysis}</div>
            </div>
        </div>
    </div>
</div>
    """

    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown(html, unsafe_allow_html=True)

    # Action buttons below the card
    _render_action_form(alarm_id, unit_sn)


def _render_action_form(alarm_id: str, unit_sn: str) -> None:
    st.markdown("### Действия")

    action_types = [
        "mark_reviewed",
        "create_task",
        "export_report",
    ]
    action_labels = {
        "mark_reviewed": "✅ Пометить как проверено",
        "create_task": "📋 Создать заявку",
        "export_report": "📄 Сформировать отчёт",
    }

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

    with col1:
        if st.button(
                action_labels["mark_reviewed"],
                use_container_width=True,
        ):
            save_action(OUTPUT_DIR,
                        row_id=f"{alarm_id[:8]}_{unit_sn}",
                        action="mark_reviewed")
            st.toast("Помечено как проверено")

    with col2:
        if st.button(
                action_labels["create_task"],
                use_container_width=True,
        ):
            save_action(OUTPUT_DIR,
                        row_id=f"{alarm_id[:8]}_{unit_sn}",
                        action="create_task")
            st.toast("Заявка создана")

    with col3:
        if st.button(
                action_labels["export_report"],
                use_container_width=True,
        ):
            save_action(OUTPUT_DIR,
                        row_id=f"{alarm_id[:8]}_{unit_sn}",
                        action="export_report")
            _export_report(alarm_id)
            st.toast("Отчёт сохранён")

    with col4:
        if st.button(
                "← К списку",
                use_container_width=True,
        ):
            st.session_state["selected_alarm_id"] = None
            st.rerun()


def _format_timestamps(begin: str, end: str) -> dict:
    result = {"begin_hour": "", "end_hour": "", "duration": "—"}
    try:
        b = pd.Timestamp(begin)
        e = pd.Timestamp(end)
        result["begin_hour"] = b.strftime("%H:%M")
        result["end_hour"] = e.strftime("%H:%M")
        result["duration"] = str(e - b).split(":")[0:2]
    except Exception:
        pass
    return result


def _build_chips(
    raw_type: str,
    speed: float,
    mileage: float,
    ts: dict,
) -> str:
    chips = ""
    if speed > SPEED_LIMIT_KMH:
        chips += (
            f'<span class="kilo-chip kilo-chip-red">'
            f'⚠ Превышение: {speed:.0f} км/ч</span>')
    elif speed > 60:
        chips += (
            f'<span class="kilo-chip kilo-chip-yellow">'
            f'🟡 Скорость: {speed:.0f} км/ч</span>')

    if raw_type in ("Drowsiness", "Yawning"):
        chips += (
            '<span class="kilo-chip kilo-chip-red">'
            '😴 Усталость водителя</span>')

    if raw_type == "Sabotage":
        chips += (
            '<span class="kilo-chip kilo-chip-red">'
            '🚫 Саботаж камеры</span>')

    if mileage > 0:
        chips += (
            f'<span class="kilo-chip kilo-chip-green">'
            f'🛣 {mileage:.1f} км</span>')

    chips += (
        f'<span class="kilo-chip kilo-chip-blue">'
        f'🕐 {ts.get("begin_hour", "—")}</span>')

    return chips


def _calc_timeline(
    track_points: pd.DataFrame,
    begin: str,
    end: str,
) -> float:
    if track_points.empty or "timestamp_utc" not in track_points.columns:
        return 10.0
    try:
        b = pd.Timestamp(begin)
        e = pd.Timestamp(end)
        total = (e - b).total_seconds()
        if total <= 0:
            return 10.0
        first = pd.Timestamp(track_points["timestamp_utc"].iloc[0])
        last = pd.Timestamp(track_points["timestamp_utc"].iloc[-1])
        coverage = (last - first).total_seconds()
        return min(max(round(coverage / total * 100, 1), 5.0), 100.0)
    except Exception:
        return 10.0


def _encode_video_base64(path: Path) -> str:
    """Encode small videos as data: URI for inline playback."""
    import base64
    max_size = 5 * 1024 * 1024
    if path.stat().st_size > max_size:
        return ""
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:video/mp4;base64,{data}"


def _export_report(alarm_id: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT_DIR / f"incident_{alarm_id[:8]}.md"
    datasets = _load_datasets()
    detail = _get_alarm_detail(datasets, alarm_id)
    alarm = detail["alarm"]

    if alarm is None:
        return

    line = f"# Инцидент {alarm_id[:8]}\n\n"
    line += f"- Госномер: {alarm.get('UnitStateNumber', '—')}\n"
    line += f"- Тип: {ALARM_TYPE_LABELS.get(str(alarm.get('Type', '')), str(alarm.get('Type', '')))}\n"
    line += f"- Скорость: {alarm.get('Speed', '?')} км/ч\n"
    line += f"- Время: {alarm.get('Begin', '—')} — {alarm.get('End', '—')}\n"
    line += f"- Адрес: {alarm.get('Address', '—')}\n"

    if not detail["videos"].empty:
        line += f"\n## Видео ({len(detail['videos'])})\n"
        for _, v in detail["videos"].head(5).iterrows():
            path = _get_video_path(v)
            line += f"- Канал {v.get('channel', '?')}: {path or 'нет файла'}\n"

    line += f"\n## Телеметрия\n"
    ts = _get_track_summary_str(detail["track_summary"])
    line += ts

    line += f"\n---\nОтчёт: {datetime.now().isoformat()}\n"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(line)


def _get_track_summary_str(
        track_summary: pd.Series | None) -> str:
    if track_summary is None:
        return "Нет данных\n"
    lines = []
    for col in track_summary.index:
        val = track_summary[col]
        if pd.notna(val):
            lines.append(f"- {col}: {val}")
    return "\n".join(lines) + "\n"


def render_incident_card_screen() -> None:
    """Main entry point for the incident card tab."""
    datasets = _load_datasets()

    selected_id = st.session_state.get("selected_alarm_id")

    if not selected_id:
        _render_selection(datasets)
    else:
        _render_incident_card(selected_id, datasets, ALARM_TYPE_LABELS)
