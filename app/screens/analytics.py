from __future__ import annotations

import pandas as pd
import streamlit as st


def _init_session() -> None:
    if "analytics_preset" not in st.session_state:
        st.session_state["analytics_preset"] = None
    if "analytics_selected_alarm_id" not in st.session_state:
        st.session_state["analytics_selected_alarm_id"] = None


def _handle_open_card(alarm_id: str) -> None:
    st.session_state["selected_alarm_id"] = alarm_id
    st.toast(f"Карточка инцидента {alarm_id[:8]}… открыта во вкладке «Детали»")


def _render_alarm_details(
    alarm_id: str,
    datasets: dict[str, pd.DataFrame],
    alarm_type_labels: dict[str, str],
) -> None:
    alarms_df = datasets.get("selected_video_alarms")
    video_files_df = datasets.get("video_files")

    if alarms_df is None:
        return

    mask = alarms_df["AlarmId"] == alarm_id
    if not mask.any():
        st.warning("Аларм не найден.")
        return

    row = alarms_df[mask].iloc[0]
    raw_type = row.get("Type", "—")
    type_label = alarm_type_labels.get(raw_type, raw_type)

    st.markdown("---")
    st.subheader("Детали инцидента")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Госномер", str(row.get("UnitStateNumber", "—")))
    c2.metric("Тип", type_label)
    c3.metric("Скорость (км/ч)", f"{row.get('Speed', 0):.0f}" if pd.notna(row.get("Speed")) else "—")
    c4.metric("Видео", str(int(row.get("VideoCount", 0))))

    ic1, ic2 = st.columns(2)
    ic1.caption(f"**Начало:** {row.get('Begin', '—')}")
    ic2.caption(f"**Окончание:** {row.get('End', '—')}")
    st.caption(f"**Адрес:** {row.get('Address') or 'не указан'}")

    st.markdown("#### Связанные видео")
    if video_files_df is not None:
        videos = video_files_df[video_files_df["alarm_id"] == alarm_id]
        if not videos.empty:
            video_cols = ["channel", "media_relative_path", "duration_seconds"]
            available = [c for c in video_cols if c in videos.columns]
            st.dataframe(
                videos[available].rename(
                    columns={
                        "channel": "Канал",
                        "media_relative_path": "Путь",
                        "duration_seconds": "Длит. (сек)",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("Нет видеофайлов для этого аларма.")
    else:
        st.caption("Нет видеофайлов для этого аларма.")

    if st.button("Открыть карточку инцидента", key=f"open_card_{alarm_id}"):
        _handle_open_card(alarm_id)


def _select_alarm_from_table(table_df: pd.DataFrame, table_key: str) -> str | None:
    event = st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=table_key,
    )
    selected_idx = event.selection.get("rows", [])
    if selected_idx:
        return str(table_df.iloc[selected_idx[0]]["AlarmId"])
    return None


def _render_preset_top5_speed(
    datasets: dict[str, pd.DataFrame],
    alarm_type_labels: dict[str, str],
    colors: dict[str, object],
) -> None:
    alarms_df = datasets.get("selected_video_alarms")
    if alarms_df is None or alarms_df.empty:
        st.warning("Нет данных по алармам.")
        return

    st.subheader("Топ-5 нарушителей по скорости")

    top5 = alarms_df.sort_values("Speed", ascending=False).head(5).copy()
    top5["TypeLabel"] = top5["Type"].map(alarm_type_labels).fillna(top5["Type"])

    display = top5[["AlarmId", "UnitStateNumber", "TypeLabel", "Speed", "Begin", "VideoCount"]].copy()
    display.columns = ["AlarmId", "Госномер", "Тип", "Скорость (км/ч)", "Время", "Видео"]

    selected = _select_alarm_from_table(display, "_top5_table")
    if selected:
        _render_alarm_details(selected, datasets, alarm_type_labels)

    st.markdown("---")
    chart_data = top5.set_index("UnitStateNumber")[["Speed"]]
    st.bar_chart(chart_data, y_label="Скорость (км/ч)", x_label="Госномер")


def _render_preset_alarm_types(
    datasets: dict[str, pd.DataFrame],
    alarm_type_labels: dict[str, str],
    colors: dict[str, object],
) -> None:
    alarms_df = datasets.get("selected_video_alarms")
    if alarms_df is None or alarms_df.empty:
        st.warning("Нет данных по алармам.")
        return

    st.subheader("Распределение алармов по типам")

    dist = alarms_df["Type"].value_counts().reset_index()
    dist.columns = ["Type", "Количество"]
    dist["Тип"] = dist["Type"].map(alarm_type_labels).fillna(dist["Type"])

    display = dist[["Тип", "Количество"]]
    st.dataframe(display, use_container_width=True, hide_index=True)

    chart_data = dist.set_index("Type")[["Количество"]]
    chart_data.index = chart_data.index.map(alarm_type_labels).fillna(chart_data.index)
    st.bar_chart(chart_data, x_label="Тип аларма", y_label="Количество")


def _render_preset_no_video(
    datasets: dict[str, pd.DataFrame],
    alarm_type_labels: dict[str, str],
    colors: dict[str, object],
) -> None:
    alarms_df = datasets.get("selected_video_alarms")
    if alarms_df is None or alarms_df.empty:
        st.warning("Нет данных по алармам.")
        return

    st.subheader("Машины без видео")

    no_video = alarms_df[alarms_df["VideoCount"] == 0].copy()
    if no_video.empty:
        st.info("Все алармы имеют видеозаписи.")
        return

    no_video["TypeLabel"] = no_video["Type"].map(alarm_type_labels).fillna(no_video["Type"])

    display = no_video[["AlarmId", "UnitStateNumber", "TypeLabel", "Speed", "Begin"]].copy()
    display.columns = ["AlarmId", "Госномер", "Тип аларма", "Скорость (км/ч)", "Время"]

    selected = _select_alarm_from_table(display, "_no_video_table")
    if selected:
        _render_alarm_details(selected, datasets, alarm_type_labels)


def _render_preset_critical(
    datasets: dict[str, pd.DataFrame],
    alarm_type_labels: dict[str, str],
    colors: dict[str, object],
) -> None:
    alarms_df = datasets.get("selected_video_alarms")
    if alarms_df is None or alarms_df.empty:
        st.warning("Нет данных по алармам.")
        return

    st.subheader("Критические события (скорость > 90)")

    critical = alarms_df[alarms_df["Speed"] > 90].sort_values("Speed", ascending=False).copy()
    if critical.empty:
        st.info("Нет критических событий (скорость > 90 км/ч).")
        return

    critical["TypeLabel"] = critical["Type"].map(alarm_type_labels).fillna(critical["Type"])

    display = critical[["AlarmId", "UnitStateNumber", "TypeLabel", "Speed", "Begin", "Address", "VideoCount"]].copy()
    display.columns = ["AlarmId", "Госномер", "Тип", "Скорость (км/ч)", "Время", "Адрес", "Видео"]

    selected = _select_alarm_from_table(display, "_critical_table")
    if selected:
        _render_alarm_details(selected, datasets, alarm_type_labels)


def _render_preset_vehicle_summary(
    datasets: dict[str, pd.DataFrame],
    alarm_type_labels: dict[str, str],
    colors: dict[str, object],
) -> None:
    vehicles_df = datasets.get("vehicles")
    alarms_df = datasets.get("selected_video_alarms")

    if vehicles_df is None or vehicles_df.empty:
        st.warning("Нет данных по машинам.")
        return

    st.subheader("Сводка по всем машинам")

    total_vehicles = len(vehicles_df)
    avg_alarms = round(vehicles_df["alarm_count"].mean(), 1) if "alarm_count" in vehicles_df.columns else 0
    total_mileage = round(vehicles_df["total_track_mileage_km"].sum(), 1) if "total_track_mileage_km" in vehicles_df.columns else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Всего машин", str(total_vehicles))
    c2.metric("Среднее алармов на машину", str(avg_alarms))
    c3.metric("Общий пробег (км)", str(total_mileage))

    st.markdown("---")

    display = vehicles_df.copy()
    display = display.rename(
        columns={
            "unit_state_number": "Госномер",
            "alarm_count": "Всего алармов",
            "alarm_types": "Типы алармов",
            "downloaded_video_count": "Видео скачано",
            "total_track_mileage_km": "Пробег (км)",
        }
    )
    show_cols = [c for c in ["Госномер", "Всего алармов", "Типы алармов", "Видео скачано", "Пробег (км)"] if c in display.columns]
    st.dataframe(display[show_cols], use_container_width=True, hide_index=True)


def _render_preset_today(
    datasets: dict[str, pd.DataFrame],
    alarm_type_labels: dict[str, str],
    colors: dict[str, object],
) -> None:
    alarms_df = datasets.get("selected_video_alarms")
    if alarms_df is None or alarms_df.empty:
        st.warning("Нет данных по алармам.")
        return

    st.subheader("Алармы за сегодня")
    st.caption(f"Нет фильтра по дате — показаны все {len(alarms_df)} алармов")

    display = alarms_df.sort_values("Speed", ascending=False).copy()
    display["TypeLabel"] = display["Type"].map(alarm_type_labels).fillna(display["Type"])

    show = display[["AlarmId", "UnitStateNumber", "TypeLabel", "Speed", "Begin", "Address", "VideoCount"]].copy()
    show.columns = ["AlarmId", "Госномер", "Тип", "Скорость (км/ч)", "Время", "Адрес", "Видео"]

    selected = _select_alarm_from_table(show, "_today_table")
    if selected:
        _render_alarm_details(selected, datasets, alarm_type_labels)


_PRESETS: dict[str, dict[str, object]] = {
    "top5_speed": {
        "label": "Топ-5 нарушителей по скорости",
        "render": _render_preset_top5_speed,
    },
    "alarm_types": {
        "label": "Все алармы по типу",
        "render": _render_preset_alarm_types,
    },
    "no_video": {
        "label": "Машины без видео",
        "render": _render_preset_no_video,
    },
    "critical": {
        "label": "Критические события (скорость > 90)",
        "render": _render_preset_critical,
    },
    "vehicle_summary": {
        "label": "Сводка по всем машинам",
        "render": _render_preset_vehicle_summary,
    },
    "today": {
        "label": "Алармы за сегодня",
        "render": _render_preset_today,
    },
}


def render_analytics_tab(
    datasets: dict[str, pd.DataFrame],
    alarm_type_labels: dict[str, str],
    colors: dict[str, object],
) -> None:
    _init_session()

    if not datasets:
        st.warning("Нет данных. Загрузите CSV-файлы во вкладке «Данные».")
        return

    preset = st.session_state.get("analytics_preset")

    if preset is None:
        _render_empty_state(colors)
        return

    preset_info = _PRESETS.get(preset)
    if preset_info is None:
        st.error(f"Неизвестный пресет: {preset}")
        _render_empty_state(colors)
        return

    if st.button("← Назад к поиску", key="_back_btn"):
        st.session_state["analytics_preset"] = None
        st.session_state["analytics_selected_alarm_id"] = None
        st.rerun()

    render_fn = preset_info["render"]
    render_fn(datasets, alarm_type_labels, colors)


def _render_empty_state(colors: dict[str, object]) -> None:
    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.markdown("<div style='text-align: center; padding: 40px 0;'>", unsafe_allow_html=True)
        st.markdown("### 📊 Сформируйте отчёт")
        st.caption("Опишите что хотите увидеть")
        st.markdown("</div>", unsafe_allow_html=True)

    query = st.text_area(
        "Запрос",
        placeholder="Например: нарушения Иванова за последние 3 дня",
        label_visibility="collapsed",
        height=100,
        key="_query_input",
    )

    _, btn_col, _ = st.columns([1, 1, 1])
    with btn_col:
        submitted = st.button("Сформировать отчёт", type="primary", use_container_width=True)

    st.markdown("---")
    st.caption("Быстрые запросы")

    preset_keys = list(_PRESETS.keys())
    rows = [preset_keys[i : i + 3] for i in range(0, len(preset_keys), 3)]

    for row_keys in rows:
        cols = st.columns(len(row_keys))
        for col, key in zip(cols, row_keys):
            info = _PRESETS[key]
            if col.button(str(info["label"]), key=f"_preset_{key}", use_container_width=True):
                st.session_state["analytics_preset"] = key
                st.session_state["analytics_selected_alarm_id"] = None
                st.rerun()

    if submitted and query.strip():
        st.info("Текстовые запросы будут обрабатываться AI-ассистентом в следующей версии. Используйте быстрые запросы ниже.")
