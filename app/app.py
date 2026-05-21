from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from constants import (
    ACTION_LABELS,
    ACTION_TYPES,
    ALARM_TYPE_LABELS,
    COLORS,
    LAYOUT,
    PAGE_ICON,
    PAGE_TITLE,
    SPEED_LIMIT_KMH,
)
from data_loader import load_csv_files, save_action
from metrics import build_dashboard_metrics, get_alarm_details, get_alarm_types_distribution
from charts import (
    build_alarm_type_bar_chart,
    build_speed_scatter_chart,
    build_track_speed_chart,
    build_vehicle_mileage_bar_chart,
)
from risk_table import build_risk_table, build_vehicle_summary, get_incident_report


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_DATA_DIR = PROJECT_ROOT / "sample_data"
OUTPUT_DIR = PROJECT_ROOT / "output"


st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT,
)


def _init_session_state() -> None:
    defaults = {
        "datasets": {},
        "selected_dataset": None,
        "selected_alarm_id": None,
        "alarm_type_filter": [],
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def _pick_dataset(datasets: dict[str, pd.DataFrame]) -> tuple[str | None, pd.DataFrame]:
    if not datasets:
        return None, pd.DataFrame()
    names = sorted(datasets)
    idx = 0
    if st.session_state["selected_dataset"] in names:
        idx = names.index(st.session_state["selected_dataset"])
    selected = st.sidebar.selectbox("Датасет", names, index=idx, key="_dataset_picker")
    st.session_state["selected_dataset"] = selected
    return selected, datasets[selected]


def _get_available_alarm_types(datasets: dict[str, pd.DataFrame]) -> list[str]:
    alarms_df = datasets.get("selected_video_alarms")
    if alarms_df is None or "Type" not in alarms_df.columns:
        return []
    return sorted(alarms_df["Type"].dropna().unique())


def _filter_alarms(datasets: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    filtered = dict(datasets)
    filters = st.session_state.get("alarm_type_filter", [])
    alarms_df = datasets.get("selected_video_alarms")
    if not filters or alarms_df is None or "Type" not in alarms_df.columns:
        return filtered
    mask = alarms_df["Type"].isin(filters)
    filtered_alarms = alarms_df[mask].copy()
    filtered_ids = set(filtered_alarms["AlarmId"].unique())
    filtered["selected_video_alarms"] = filtered_alarms
    for key in ("video_files", "track_points", "track_summary", "max_speed_points"):
        df = datasets.get(key)
        if df is not None and "alarm_id" in df.columns:
            filtered[key] = df[df["alarm_id"].isin(filtered_ids)].copy()
    return filtered


def _render_sidebar(datasets: dict[str, pd.DataFrame], data_source: Path) -> None:
    st.sidebar.caption(f"Источник данных: {data_source.relative_to(PROJECT_ROOT)}")

    alarm_types = _get_available_alarm_types(datasets)
    if alarm_types:
        type_labels = {t: ALARM_TYPE_LABELS.get(t, t) for t in alarm_types}
        st.sidebar.multiselect(
            "Фильтр по типу аларма",
            options=alarm_types,
            format_func=lambda t: type_labels.get(t, t),
            key="alarm_type_filter",
        )
    st.sidebar.caption(
        f"Загружено: {len(datasets)} файлов"
        if datasets
        else "Нет данных — добавьте CSV в ./data"
    )


def _render_data_tab(datasets: dict[str, pd.DataFrame]) -> None:
    st.subheader("Загруженные CSV-файлы")
    if not datasets:
        st.warning("CSV-файлы не найдены. Поместите файлы в ./data или скопируйте примеры из ./sample_data.")
        return

    overview = pd.DataFrame(
        [
            {"Файл": name, "Строк": len(df), "Колонок": len(df.columns)}
            for name, df in sorted(datasets.items())
        ]
    )
    st.dataframe(overview, use_container_width=True, hide_index=True)

    selected, df = _pick_dataset(datasets)
    if selected:
        st.caption(f"Превью: {selected}")
        st.dataframe(df.head(100), use_container_width=True)


def _render_dashboard_tab(datasets: dict[str, pd.DataFrame]) -> None:
    st.subheader("Дашборд")

    if not datasets:
        st.warning("Нет данных для построения дашборда.")
        return

    filtered = _filter_alarms(datasets)

    metrics_items = build_dashboard_metrics(filtered)
    if metrics_items:
        metric_cols = st.columns(len(metrics_items))
        for col, item in zip(metric_cols, metrics_items):
            col.metric(item["label"], item["value"], item.get("delta"))

    st.markdown("---")
    left, right = st.columns(2)

    with left:
        st.subheader("Распределение типов алармов")
        alarm_dist = get_alarm_types_distribution(filtered)
        alarm_bar = build_alarm_type_bar_chart(alarm_dist, ALARM_TYPE_LABELS, COLORS["chart_colors"])
        st.altair_chart(alarm_bar, use_container_width=True)

    with right:
        st.subheader("Пробег машин")
        vehicles_df = filtered.get("vehicles")
        if vehicles_df is not None and not vehicles_df.empty:
            mileage_chart = build_vehicle_mileage_bar_chart(vehicles_df, COLORS["chart_colors"])
            st.altair_chart(mileage_chart, use_container_width=True)
        else:
            st.info("Нет данных о пробеге машин.")

    st.markdown("---")
    st.subheader("Кастомный scatter-график")

    selected, df = _pick_dataset(filtered)
    if not selected or df.empty:
        st.info("Выберите датасет для построения графика.")
        return

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(exclude="number").columns.tolist()
    if len(numeric_cols) < 2:
        st.info("Нужно минимум две числовые колонки для scatter-графика.")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        x_col = st.selectbox("Ось X", numeric_cols, index=0, key="scatter_x")
    with c2:
        y_col = st.selectbox("Ось Y", numeric_cols, index=min(1, len(numeric_cols) - 1), key="scatter_y")
    with c3:
        color_options = ["— нет —"] + cat_cols
        color_col = st.selectbox("Цвет по", color_options, index=0, key="scatter_color")

    actual_color = color_col if color_col != "— нет —" else None
    scatter = build_speed_scatter_chart(
        df, x_col, y_col, color_col=actual_color, chart_colors=COLORS["chart_colors"]
    )
    st.altair_chart(scatter, use_container_width=True)


def _render_details_tab(datasets: dict[str, pd.DataFrame]) -> None:
    st.subheader("Детали инцидентов")

    if not datasets:
        st.warning("Нет данных для анализа.")
        return

    filtered = _filter_alarms(datasets)

    risk_table = build_risk_table(filtered)
    if risk_table.empty:
        st.info("Нет данных для построения риск-таблицы. Реализуйте build_risk_table() в app/risk_table.py.")
        return

    st.subheader("Риск-таблица")
    event = st.dataframe(
        risk_table,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="_risk_table",
        column_config={
            "AlarmId": st.column_config.TextColumn("ID аларма", width="small"),
            "UnitStateNumber": st.column_config.TextColumn("Госномер", width="small"),
            "Type": st.column_config.TextColumn("Тип", width="small"),
            "Speed": st.column_config.NumberColumn("Скорость (км/ч)", width="small"),
            "Begin": st.column_config.TextColumn("Начало", width="medium"),
            "Address": st.column_config.TextColumn("Адрес", width="medium"),
            "VideoCount": st.column_config.NumberColumn("Видео", width="small"),
        },
    )

    selected_idx = event.selection.get("rows", [])
    if selected_idx:
        row = risk_table.iloc[selected_idx[0]]
        alarm_id = str(row["AlarmId"])
        st.session_state["selected_alarm_id"] = alarm_id
    else:
        alarm_id = st.session_state.get("selected_alarm_id")

    if not alarm_id:
        st.info("Выберите строку в риск-таблице для просмотра деталей инцидента.")
        _render_action_form("", "")
        return

    st.markdown("---")
    st.subheader(f"Детали инцидента: {alarm_id[:8]}…")

    alarm_details = get_alarm_details(filtered, alarm_id)
    alarm_row = alarm_details.get("alarm_row")
    videos = alarm_details.get("videos", pd.DataFrame())
    track_points = alarm_details.get("track_points", pd.DataFrame())

    if alarm_row is None:
        st.warning("Аларм не найден в данных.")
        _render_action_form(alarm_id, "")
        return

    summary_cols = st.columns(3)
    with summary_cols[0]:
        st.metric("Госномер", str(alarm_row.get("UnitStateNumber", "—")))
    with summary_cols[1]:
        raw_type = alarm_row.get("Type", "—")
        type_label = ALARM_TYPE_LABELS.get(raw_type, raw_type)
        st.metric("Тип аларма", type_label)
    with summary_cols[2]:
        speed = alarm_row.get("Speed", 0)
        st.metric(
            "Скорость (км/ч)",
            f"{speed:.0f}" if pd.notna(speed) else "—",
            delta=f"Лимит: {SPEED_LIMIT_KMH}",
            delta_color="inverse",
        )

    info_cols = st.columns(2)
    with info_cols[0]:
        st.caption(f"**Начало:** {alarm_row.get('Begin', '—')}")
        st.caption(f"**Окончание:** {alarm_row.get('End', '—')}")
    with info_cols[1]:
        st.caption(f"**Адрес:** {alarm_row.get('Address') or 'не указан'}")
        if "CameraIds" in alarm_row.index:
            st.caption(f"**Камеры:** {alarm_row.get('CameraIds', '—')}")

    st.markdown("### Связанные видео")
    if videos.empty:
        st.caption("Нет видеофайлов для этого аларма.")
    else:
        st.dataframe(
            videos.rename(
                columns={
                    "channel": "Канал",
                    "media_relative_path": "Путь к медиа",
                    "duration_seconds": "Длит. (сек)",
                    "size_bytes": "Размер (байт)",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### График скорости трека")
    if not track_points.empty and "speed_kmh" in track_points.columns:
        track_chart = build_track_speed_chart(track_points, alarm_id, COLORS["chart_colors"])
        st.altair_chart(track_chart, use_container_width=True)
    else:
        st.info("Нет данных о треке для этого аларма.")

    st.markdown("---")
    st.subheader("Сводка по машине")
    vehicles_df = filtered.get("vehicles")
    if vehicles_df is not None:
        unit_sn = str(alarm_row.get("UnitStateNumber", ""))
        if unit_sn:
            vmask = vehicles_df["unit_state_number"] == unit_sn
            if vmask.any():
                vrow = vehicles_df[vmask].iloc[0]
                vcols = st.columns(4)
                vcols[0].metric("Алармов всего", vrow.get("alarm_count", "—"))
                vcols[1].metric("Видео скачано", vrow.get("downloaded_video_count", "—"))
                vcols[2].metric(
                    "Пробег треков (км)",
                    f"{vrow.get('total_track_mileage_km', 0):.1f}",
                )
                vcols[3].metric(
                    "Типы алармов",
                    str(vrow.get("alarm_types", "—")).replace("|", ", "),
                )

    _render_action_form(alarm_id, str(alarm_row.get("UnitStateNumber", "")))


def _render_action_form(alarm_id: str, unit_sn: str) -> None:
    with st.form("action_form", clear_on_submit=True):
        st.markdown("### Действие")
        prefix = f"{alarm_id[:8]}_{unit_sn}" if alarm_id else ""
        row_id = st.text_input("ID записи", value=prefix, key="form_row_id")
        action_type = st.selectbox(
            "Тип действия",
            options=ACTION_TYPES,
            format_func=lambda t: ACTION_LABELS.get(t, t),
            key="form_action_type",
        )
        comment = st.text_area("Комментарий", height=80, key="form_comment")
        submitted = st.form_submit_button("Сохранить действие")

    if submitted:
        save_action(OUTPUT_DIR, row_id=row_id, action=action_type, comment=comment)
        st.success("Действие сохранено в ./output/actions.csv")
        st.rerun()


def main() -> None:
    _init_session_state()

    st.title(PAGE_TITLE)
    st.caption("Телематика + Видео → Контекст → Действие. MVP единого окна инцидентов.")

    data_source = DATA_DIR if any(DATA_DIR.glob("*.csv")) else SAMPLE_DATA_DIR
    st.session_state["datasets"] = load_csv_files(data_source)
    datasets = st.session_state["datasets"]

    _render_sidebar(datasets, data_source)

    data_tab, dashboard_tab, details_tab = st.tabs(
        ["📋 Данные", "📊 Дашборд", "🔍 Детали"]
    )
    with data_tab:
        _render_data_tab(datasets)
    with dashboard_tab:
        _render_dashboard_tab(datasets)
    with details_tab:
        _render_details_tab(datasets)


if __name__ == "__main__":
    main()
