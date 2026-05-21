from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from app.charts import build_track_speed_chart
from app.data_loader import save_action
from app.metrics import get_alarm_details
from app.risk_table import get_incident_report

_AI_ANALYSIS: dict[str, str] = {
    "Drowsiness": (
        "Водитель не менял положение руля 40+ секунд. Возможен микросон. "
        "Рекомендация: проверить записи с камеры салона, оценить непрерывное время вождения."
    ),
    "Sabotage": (
        "Камера зафиксировала перекрытие объектива или отключение. "
        "Возможна попытка скрыть нарушение. "
        "Рекомендация: запросить видео с других камер, проверить логи системы."
    ),
    "Distraction": (
        "Водитель отвлёкся от дороги более 3 секунд. Риск ДТП повышен. "
        "Рекомендация: провести беседу, проверить историю нарушений."
    ),
    "DangerousDistance": (
        "Несоблюдение безопасной дистанции. Риск попутного столкновения."
    ),
    "SharpAcceleration": (
        "Резкое ускорение. Возможна агрессивная езда или уход от столкновения."
    ),
}

_DEFAULT_ANALYSIS = (
    "Событие зафиксировано системой видеоаналитики. "
    "Требуется ручная проверка диспетчером."
)

_REASON_BUTTONS = [
    ("😴 Засыпание", "Засыпание"),
    ("📱 Отвлечение", "Отвлечение"),
    ("🚗 Подрезали", "Подрезали"),
    ("⚙ Технический сбой", "Технический сбой"),
]

_ACTION_TYPES = ["mark_reviewed", "create_task", "export_report"]
_ACTION_LABELS = {
    "mark_reviewed": "Пометить как проверено",
    "create_task": "Создать заявку",
    "export_report": "Сформировать отчёт",
}


def _resolve_df(datasets: dict[str, pd.DataFrame], key: str) -> pd.DataFrame:
    df = datasets.get(key)
    if df is not None:
        return df
    return datasets.get(f"{key}.csv", pd.DataFrame())


def _get_alarm_row(datasets: dict[str, pd.DataFrame], alarm_id: str) -> pd.Series | None:
    alarms_df = _resolve_df(datasets, "selected_video_alarms")
    if alarms_df is None or alarms_df.empty or "AlarmId" not in alarms_df.columns:
        return None
    mask = alarms_df["AlarmId"] == alarm_id
    if not mask.any():
        return None
    return alarms_df[mask].iloc[0]


def _get_track_points(datasets: dict[str, pd.DataFrame], alarm_id: str) -> pd.DataFrame:
    track_points_df = _resolve_df(datasets, "track_points")
    if track_points_df is None or track_points_df.empty:
        return pd.DataFrame()
    if "alarm_id" not in track_points_df.columns:
        return pd.DataFrame()
    tp = track_points_df[track_points_df["alarm_id"] == alarm_id].copy()
    if not tp.empty and "timestamp_utc" in tp.columns:
        tp = tp.sort_values("timestamp_utc").head(200)
    return tp.reset_index(drop=True)


def _get_videos(datasets: dict[str, pd.DataFrame], alarm_id: str) -> pd.DataFrame:
    video_files_df = _resolve_df(datasets, "video_files")
    if video_files_df is None or video_files_df.empty:
        return pd.DataFrame()
    if "alarm_id" not in video_files_df.columns:
        return pd.DataFrame()
    return video_files_df[video_files_df["alarm_id"] == alarm_id].reset_index(drop=True)


def _get_track_summary(datasets: dict[str, pd.DataFrame], alarm_id: str) -> pd.Series | None:
    track_summary_df = _resolve_df(datasets, "track_summary")
    if track_summary_df is None or track_summary_df.empty:
        return None
    if "alarm_id" not in track_summary_df.columns:
        return None
    mask = track_summary_df["alarm_id"] == alarm_id
    if not mask.any():
        return None
    return track_summary_df[mask].iloc[0]


def _parse_camera_ids(raw: str) -> list[str]:
    if pd.isna(raw) or not raw:
        return []
    raw_str = str(raw)
    try:
        parsed = json.loads(raw_str)
        if isinstance(parsed, list):
            return [str(c) for c in parsed]
    except (json.JSONDecodeError, TypeError):
        pass
    parts = raw_str.replace("'", '"').replace(" ", "").split(",")
    parts = [p.strip('"[] ') for p in parts if p.strip('"[] ')]
    return parts


def _render_selection_mode(datasets: dict[str, pd.DataFrame]) -> None:
    alarms_df = _resolve_df(datasets, "selected_video_alarms")
    if alarms_df is None or alarms_df.empty:
        st.warning("Нет данных об алармах.")
        return

    alarm_ids = (
        alarms_df["AlarmId"].dropna().astype(str).unique().tolist()
        if "AlarmId" in alarms_df.columns
        else []
    )

    if not alarm_ids:
        st.warning("Нет идентификаторов алармов.")
        return

    st.subheader("Выбор инцидента")

    col1, col2 = st.columns(2)

    with col1:
        manual_id = st.text_input(
            "Введите AlarmId",
            placeholder="Например: alarm_001",
            key="_incident_manual_id",
        )

    with col2:
        first_20 = alarm_ids[:20]
        selected = st.selectbox(
            "Или выберите из списка (первые 20)",
            options=["—"] + first_20,
            key="_incident_select_id",
        )
        if selected != "—":
            manual_id = selected

    if st.button("Показать инцидент", type="primary") and manual_id:
        if manual_id in alarm_ids:
            st.session_state["selected_alarm_id"] = manual_id
            st.rerun()
        else:
            st.error(f"AlarmId '{manual_id}' не найден в данных.")


def _render_back_button() -> None:
    if st.button("← К списку", key="_incident_back"):
        st.session_state["selected_alarm_id"] = None
        st.rerun()


def _render_top_panel(
    alarm_row: pd.Series,
    alarm_type_labels: dict[str, str],
    speed_limit_kmh: int,
    has_video: bool,
    has_track: bool,
) -> None:
    unit_sn = str(alarm_row.get("UnitStateNumber", "—"))
    raw_type = alarm_row.get("Type", "—")
    type_label = alarm_type_labels.get(raw_type, raw_type)
    speed = alarm_row.get("Speed", 0)
    speed_val = float(speed) if pd.notna(speed) else 0.0
    score = round(speed_val / speed_limit_kmh * 100) if speed_limit_kmh > 0 else 0

    begin = alarm_row.get("Begin", "—")
    end = alarm_row.get("End", "—")
    address = alarm_row.get("Address") or "не указан"

    if has_video and has_track:
        badge = '<span style="background:#DBEAFE;color:#1E40AF;padding:2px 8px;border-radius:4px;font-size:12px;">⚡📹 Оба</span>'
    elif has_video:
        badge = '<span style="background:#D1FAE5;color:#065F46;padding:2px 8px;border-radius:4px;font-size:12px;">📹 ВА</span>'
    elif has_track:
        badge = '<span style="background:#FEF3C7;color:#92400E;padding:2px 8px;border-radius:4px;font-size:12px;">⚡ Тел</span>'
    else:
        badge = '<span style="background:#F1F5F9;color:#64748B;padding:2px 8px;border-radius:4px;font-size:12px;">—</span>'

    st.markdown(f"**Госномер:** {unit_sn}  |  **Тип:** {type_label}  |  **Скорость:** {speed_val:.0f} км/ч  |  **Score:** {score}%  |  {badge}")
    st.caption(f"🕐 {begin} — {end}")
    st.caption(f"📍 {address}")


def _render_video_section(datasets: dict[str, pd.DataFrame], alarm_id: str, alarm_row: pd.Series) -> None:
    st.markdown("### ВИДЕО СОБЫТИЯ")

    videos = _get_videos(datasets, alarm_id)

    if videos.empty:
        st.markdown(
            '<div style="background:#F1F5F9;border:1px dashed #94A3B8;border-radius:8px;'
            'padding:32px 16px;text-align:center;color:#64748B;">'
            '<span style="font-size:48px;">📷</span><br>'
            '<span>Нет видео для этого аларма</span></div>',
            unsafe_allow_html=True,
        )

        has_any_video = False
    else:
        has_any_video = True
        display_videos = videos.copy()
        column_map = {}
        if "channel" in display_videos.columns:
            column_map["channel"] = "Канал"
        if "media_relative_path" in display_videos.columns:
            column_map["media_relative_path"] = "Путь к медиа"
        if "duration_seconds" in display_videos.columns:
            column_map["duration_seconds"] = "Длит. (сек)"
        if "size_bytes" in display_videos.columns:
            display_videos["size_mb"] = (display_videos["size_bytes"] / (1024 * 1024)).round(2)
            column_map["size_mb"] = "Размер (МБ)"

        if column_map:
            st.dataframe(
                display_videos[list(column_map)].rename(columns=column_map),
                use_container_width=True,
                hide_index=True,
            )

    st.markdown("**Статус камер:**")
    camera_ids_raw = alarm_row.get("CameraIds")
    cameras = _parse_camera_ids(camera_ids_raw)
    if cameras:
        active_count = len(cameras)
        st.markdown(
            f"Активно камер: {active_count} — "
            + ", ".join(f"`{c}`" for c in cameras[:10])
            + ("…" if len(cameras) > 10 else "")
        )
    else:
        st.caption("Нет данных о камерах")

    if not has_any_video:
        st.button(
            "Запросить архивное видео",
            disabled=True,
            help="Демо-режим: запрос архивного видео недоступен.",
            key="_incident_request_archive",
        )


def _render_telemetry_section(
    datasets: dict[str, pd.DataFrame],
    alarm_id: str,
    alarm_row: pd.Series,
    colors: dict,
) -> None:
    track_points = _get_track_points(datasets, alarm_id)
    track_summary = _get_track_summary(datasets, alarm_id)
    speed = float(alarm_row.get("Speed", 0)) if pd.notna(alarm_row.get("Speed")) else 0.0
    raw_type = str(alarm_row.get("Type", ""))
    begin = str(alarm_row.get("Begin", ""))

    st.markdown("### СКОРОСТЬ И АКСЕЛЕРОМЕТР")
    if not track_points.empty and "speed_kmh" in track_points.columns:
        chart_colors = colors.get("chart_colors", ["#3B82F6"])
        speed_chart = build_track_speed_chart(track_points, alarm_id, chart_colors)
        st.altair_chart(speed_chart, use_container_width=True)
    else:
        st.info("Нет данных о скорости трека.")

    st.markdown("### МАРШРУТ")
    has_track_coords = (
        not track_points.empty
        and "latitude" in track_points.columns
        and "longitude" in track_points.columns
        and not track_points[["latitude", "longitude"]].isna().all().all()
    )
    if has_track_coords:
        map_df = track_points[["latitude", "longitude"]].dropna()
        map_df.columns = ["LAT", "LON"]
        st.map(map_df.rename(columns={"LAT": "latitude", "LON": "longitude"}))
    else:
        lat = alarm_row.get("Latitude")
        lon = alarm_row.get("Longitude")
        if pd.notna(lat) and pd.notna(lon):
            map_df = pd.DataFrame({"latitude": [float(lat)], "longitude": [float(lon)]})
            st.map(map_df)
        else:
            st.caption("Координаты не доступны")

    st.markdown("### КОНТЕКСТ")

    total_mileage = 0.0
    if track_summary is not None:
        total_mileage = float(track_summary.get("total_mileage_km", 0) or 0)

    chips_html = ""

    if speed > 90:
        chips_html += (
            '<span style="display:inline-block;background:#FEF3C7;color:#92400E;'
            'padding:2px 8px;border-radius:6px;margin:2px;font-size:13px;">'
            f'🟠 Превышение скорости: {speed:.0f} км/ч</span>'
        )

    if raw_type == "Drowsiness":
        chips_html += (
            '<span style="display:inline-block;background:#DBEAFE;color:#1E40AF;'
            'padding:2px 8px;border-radius:6px;margin:2px;font-size:13px;">'
            '🔵 Засыпание — риск для безопасности</span>'
        )

    if raw_type == "Sabotage":
        chips_html += (
            '<span style="display:inline-block;background:#FEE2E2;color:#991B1B;'
            'padding:2px 8px;border-radius:6px;margin:2px;font-size:13px;">'
            '🔴 Саботаж камеры — требуется проверка</span>'
        )

    try:
        if begin and begin != "—":
            hour = pd.Timestamp(begin).hour
            if 22 <= hour or hour < 6:
                chips_html += (
                    '<span style="display:inline-block;background:#EDE9FE;color:#5B21B6;'
                    'padding:2px 8px;border-radius:6px;margin:2px;font-size:13px;">'
                    '🌙 Ночная поездка</span>'
                )
    except (ValueError, TypeError):
        pass

    if total_mileage > 0:
        chips_html += (
            '<span style="display:inline-block;background:#D1FAE5;color:#065F46;'
            'padding:2px 8px;border-radius:6px;margin:2px;font-size:13px;">'
            f'Пробег трека: {total_mileage:.1f} км</span>'
        )

    if chips_html:
        st.markdown(f"<div>{chips_html}</div>", unsafe_allow_html=True)
    else:
        st.caption("Нет дополнительных контекстных признаков.")


def _render_analysis_section(alarm_row: pd.Series) -> None:
    raw_type = str(alarm_row.get("Type", ""))
    analysis_text = _AI_ANALYSIS.get(raw_type, _DEFAULT_ANALYSIS)

    st.markdown("### АНАЛИЗ СОБЫТИЯ")

    st.markdown(
        f"""
        <div style="border:1px solid #E2E8F0;border-radius:10px;padding:16px;background:#F8FAFC;margin-bottom:12px;">
            <p style="font-weight:600;margin-bottom:6px;">🤖 Вероятная причина</p>
            <p style="font-size:14px;color:#334155;line-height:1.5;">{analysis_text}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_a, col_b, col_c, col_d = st.columns(4)
    for col, (btn_label, reason) in zip(
        [col_a, col_b, col_c, col_d], _REASON_BUTTONS
    ):
        if col.button(btn_label, key=f"_reason_{reason}"):
            st.toast(f"Причина '{reason}' зафиксирована")


def _render_action_form(alarm_id: str, unit_sn: str) -> None:
    st.markdown("### ДЕЙСТВИЯ")

    output_dir = Path(__file__).resolve().parents[2] / "output"

    with st.form("_incident_action_form", clear_on_submit=True):
        prefix = f"{alarm_id[:8]}_{unit_sn}" if alarm_id else ""
        row_id = st.text_input("ID записи", value=prefix, key="_incident_form_row_id")
        action_type = st.selectbox(
            "Тип действия",
            options=_ACTION_TYPES,
            format_func=lambda t: _ACTION_LABELS.get(t, t),
            key="_incident_form_action_type",
        )
        comment = st.text_area("Комментарий", height=80, key="_incident_form_comment")
        submitted = st.form_submit_button("Сохранить")

    if submitted:
        save_action(output_dir, row_id=row_id, action=action_type, comment=comment)
        st.session_state["_incident_action_submitted"] = True
        st.success("Действие сохранено в ./output/actions.csv")
        st.rerun()


def render_incident_tab(
    datasets: dict[str, pd.DataFrame],
    alarm_type_labels: dict[str, str],
    colors: dict,
    speed_limit_kmh: int,
) -> tuple[str, str] | None:
    selected_id = st.session_state.get("selected_alarm_id")

    if not selected_id:
        _render_selection_mode(datasets)
        return None

    alarm_row = _get_alarm_row(datasets, selected_id)
    if alarm_row is None:
        st.warning(f"Аларм '{selected_id}' не найден в данных.")
        if st.button("← К списку", key="_incident_back_notfound"):
            st.session_state["selected_alarm_id"] = None
            st.rerun()
        return None

    _render_back_button()

    videos = _get_videos(datasets, selected_id)
    track_points = _get_track_points(datasets, selected_id)
    has_video = not videos.empty
    has_track = not track_points.empty

    unit_sn = str(alarm_row.get("UnitStateNumber", ""))

    _render_top_panel(alarm_row, alarm_type_labels, speed_limit_kmh, has_video, has_track)

    st.markdown("---")

    left_col, right_col = st.columns([0.4, 0.6])

    with left_col:
        _render_video_section(datasets, selected_id, alarm_row)

    with right_col:
        _render_telemetry_section(datasets, selected_id, alarm_row, colors)

    st.markdown("---")

    _render_analysis_section(alarm_row)

    st.markdown("---")

    _render_action_form(selected_id, unit_sn)

    if st.session_state.get("_incident_action_submitted"):
        st.session_state["_incident_action_submitted"] = False
        return (selected_id, unit_sn)

    return None
