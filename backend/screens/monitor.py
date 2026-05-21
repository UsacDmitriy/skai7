from __future__ import annotations

import streamlit as st
import pandas as pd


_MONITOR_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
    --bg-app:      #0F1117;
    --bg-canvas:   #181A24;
    --bg-sunken:   #13151D;
    --bg-alt:      #1F2231;
    --border-1:    #252838;
    --border-2:    #2E3244;
    --fg-1:        #E8EAF0;
    --fg-2:        #8B90A0;
    --fg-3:        #5C6070;
    --primary:     #3B82F6;
    --primary-soft:#1E3A5F;
    --danger:      #EF4444;
    --danger-ink:  #FCA5A5;
    --warning:     #F59E0B;
    --high:        #F97316;
    --success:     #22C55E;
}

@keyframes m-pulse {
    0%, 100% { opacity: 1; box-shadow: 0 0 4px var(--danger); }
    50% { opacity: 0.35; box-shadow: 0 0 12px var(--danger); }
}

.m-topbar {
    display: flex; align-items: center; height: 40px;
    padding: 0 14px; gap: 14px;
    background: var(--bg-canvas); border-radius: 8px 8px 0 0;
    border: 1px solid var(--border-1);
}

.m-topbar .logo {
    font-weight: 700; font-size: 13px; color: var(--primary);
    letter-spacing: 1px; display: flex; align-items: center; gap: 7px;
}

.m-topbar .live-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--danger); animation: m-pulse 1.5s ease-in-out infinite;
}

.m-topbar .kpi {
    margin-left: auto; display: flex; gap: 14px;
    font-size: 11px; color: var(--fg-2);
}

.m-topbar .kv { color: var(--fg-1); font-weight: 600; }

.m-section {
    font-size: 10px; text-transform: uppercase; letter-spacing: 1px;
    font-weight: 600; color: var(--fg-2);
    padding: 10px 2px 6px; border-bottom: 2px solid var(--danger);
    display: inline-block; margin-bottom: 8px;
}

.m-card {
    background: var(--bg-sunken); border: 1px solid var(--border-1);
    border-radius: 6px; padding: 8px 10px; margin-bottom: 4px;
    cursor: pointer; transition: all 0.12s;
}

.m-card:hover { background: var(--bg-alt); border-color: var(--border-2); }

.m-section {
    font-size: 10px; text-transform: uppercase; letter-spacing: 1px;
    font-weight: 600; color: var(--fg-2);
    padding: 10px 2px 6px; border-bottom: 2px solid var(--danger);
    display: inline-block; margin-bottom: 8px;
}

.m-item-head {
    display: flex; justify-content: space-between; align-items: flex-start;
    gap: 8px;
}

.m-veh { font-size: 11px; font-weight: 600; color: var(--fg-1); margin-bottom: 2px; }
.m-types { font-size: 10px; color: var(--fg-2); }
.m-meta { font-size: 9px; color: var(--fg-3); }

.m-speed {
    font-size: 14px; font-weight: 700; font-variant-numeric: tabular-nums;
}
.m-speed.critical { color: var(--danger-ink); }
.m-speed.normal { color: var(--fg-1); }

.m-dot {
    width: 7px; height: 7px; border-radius: 50%; display: inline-block;
    margin-right: 6px; vertical-align: middle;
}
.m-dot.critical { background: var(--danger); }
.m-dot.high { background: var(--high); }
.m-dot.warning { background: var(--warning); }
.m-dot.normal { background: var(--primary); }

.m-detail-block {
    background: var(--bg-sunken); border: 1px solid var(--border-1);
    border-radius: 6px; padding: 10px 12px; margin-bottom: 8px;
}

.m-detail-block h5 {
    font-size: 9px; text-transform: uppercase; letter-spacing: 0.7px;
    color: var(--fg-3); margin: 0 0 6px; font-weight: 600;
}

.m-dl {
    font-size: 11px; color: var(--fg-1); margin: 3px 0;
    display: flex; justify-content: space-between;
}
.m-dl .label { color: var(--fg-2); }
.m-dl .value { font-weight: 500; }

.m-btn {
    width: 100%; padding: 8px 12px; margin: 4px 0;
    border-radius: 6px; border: 1px solid var(--border-2);
    background: var(--bg-sunken); color: var(--fg-1);
    font-size: 11px; font-weight: 500; cursor: pointer;
    transition: all 0.12s; font-family: 'Inter', sans-serif; text-align: left;
}
.m-btn:hover { border-color: var(--primary); background: var(--primary-soft); }
.m-btn.primary { background: var(--primary); border-color: var(--primary); color: white; }

.m-btm {
    display: flex; align-items: center; height: 24px;
    padding: 0 12px; gap: 10px;
    background: var(--bg-canvas); border-radius: 0 0 8px 8px;
    border: 1px solid var(--border-1); border-top: none;
    font-size: 9px; color: var(--fg-3);
}
.m-ok { color: var(--success); font-weight: 600; }
</style>
"""


def _dot(speed, vc=0):
    if speed > 90:
        return "critical"
    if speed > 70:
        return "high"
    if vc == 0:
        return "warning"
    return "normal"


def _render_monitor_html(datasets, alarm_labels, alarm_type_colors, selected_aid):
    alarms_df = datasets.get("selected_video_alarms")
    vehicles_df = datasets.get("vehicles")

    if alarms_df is None or alarms_df.empty:
        return '<div style="color:var(--fg-3);padding:40px;text-align:center;">Нет данных</div>'

    total_alarms = len(alarms_df)
    unique_vehicles = (
        alarms_df["UnitStateNumber"].nunique()
        if "UnitStateNumber" in alarms_df.columns
        else (len(vehicles_df) if vehicles_df is not None else 0)
    )
    avg_speed = alarms_df["Speed"].mean() if "Speed" in alarms_df.columns else 0.0

    sorted_df = alarms_df.dropna(subset=["Speed"]).sort_values("Speed", ascending=False)

    items_html = ""
    for _, row in sorted_df.iterrows():
        alarm_id = str(row.get("AlarmId", ""))
        speed = float(row.get("Speed", 0))
        vc = int(row.get("VideoCount", 0)) if pd.notna(row.get("VideoCount")) else 0
        severity = _dot(speed, vc)
        vehicle = str(row.get("UnitStateNumber", "—"))
        raw_type = row.get("Type", "—")
        types_str = str(row.get("", ""))
        type_label = alarm_labels.get(raw_type, raw_type)
        begin = str(row.get("Begin", ""))
        address = str(row.get("Address", ""))
        if address == "nan":
            address = ""
        speed_cls = "critical" if severity == "critical" else "normal"

        items_html += f"""
<div class="m-card" onclick="parent.postMessage({{type:'alarm_select',id:'{alarm_id}'}},'*')">
    <div class="m-item-head">
        <div>
            <div class="m-veh"><span class="m-dot {severity}"></span>{vehicle}</div>
            <div class="m-types">{type_label}</div>
            <div class="m-meta">{'📍 ' + address + ' · ' if address else ''}{begin} · {vc} 📹</div>
        </div>
        <div class="m-speed {speed_cls}">{speed:.0f}</div>
    </div>
</div>"""

    selected_row = None
    if selected_aid:
        match = alarms_df[alarms_df["AlarmId"].astype(str) == str(selected_aid)]
        if not match.empty:
            selected_row = match.iloc[0]

    if selected_row is not None:
        r = selected_row
        vehicle = str(r.get("UnitStateNumber", "—"))
        raw_type = str(r.get("Type", "—"))
        type_label = alarm_labels.get(raw_type, raw_type)
        type_color = alarm_type_colors.get(raw_type, "#8B90A0")
        speed = float(r.get("Speed", 0))
        begin = str(r.get("Begin", "—"))
        end = str(r.get("End", "—"))
        address = str(r.get("Address", ""))
        if address == "nan":
            address = ""
        video_count = int(r.get("VideoCount", 0)) if pd.notna(r.get("VideoCount")) else 0
        sev = _dot(speed, video_count)
        sev_names = {"critical": "Критический", "high": "Высокий", "warning": "Средний", "normal": "Нормальный"}
        sev_colors = {"critical": "var(--danger)", "high": "var(--high)", "warning": "var(--warning)", "normal": "var(--success)"}
        right_html = f"""
<div class="m-detail-block">
    <h5>Инцидент</h5>
    <div style="font-size:15px;font-weight:700;margin-bottom:4px;">{vehicle}</div>
    <div style="display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600;background:{type_color}20;color:{type_color};border:1px solid {type_color}40;">{type_label}</div>
</div>
<div class="m-detail-block">
    <h5>Телеметрия</h5>
    <div class="m-dl"><span class="label">Скорость</span><span class="value" style="color:{'var(--danger)' if speed>90 else 'var(--fg-1)'};">{speed:.0f} км/ч</span></div>
    <div class="m-dl"><span class="label">Риск</span><span class="value" style="color:{sev_colors[sev]};">{sev_names[sev]}</span></div>
    <div class="m-dl"><span class="label">Начало</span><span class="value">{begin}</span></div>
    <div class="m-dl"><span class="label">Окончание</span><span class="value">{end}</span></div>
    {'<div class="m-dl"><span class="label">Адрес</span><span class="value">'+address+'</span></div>' if address else ''}
</div>
<div class="m-detail-block">
    <h5>Видео</h5>
    <div class="m-dl"><span class="label">Камеры</span><span class="value">{video_count}</span></div>
    {'<div class="m-dl"><span class="label">Статус</span><span class="value" style="color:var(--warning);">Нет видео</span></div>' if not video_count else ''}
</div>
<div class="m-detail-block">
    <h5>Действия</h5>
    <button class="m-btn primary" onclick="parent.postMessage({{type:'alarm_action',action:'report'}},'*')">📋 Создать отчёт</button>
    <button class="m-btn" onclick="parent.postMessage({{type:'alarm_action',action:'verify'}},'*')">✅ Отметить проверкой</button>
    <button class="m-btn" onclick="parent.postMessage({{type:'alarm_action',action:'request_video'}},'*')">🎬 Запросить видео</button>
</div>"""
    else:
        right_html = '<div style="padding:30px;text-align:center;color:var(--fg-3);font-size:12px;">Выберите событие из ленты</div>'

    sel_veh = selected_row.get("UnitStateNumber", "—") if selected_row is not None else "—"
    sel_type_raw = selected_row.get("Type", "") if selected_row is not None else ""
    sel_type_label = alarm_labels.get(sel_type_raw, sel_type_raw) if selected_row is not None else ""
    sel_speed = selected_row.get("Speed", "—") if selected_row is not None else ""

    return f"""
<div style="font-family:'Inter',sans-serif;background:var(--bg-app);color:var(--fg-1);padding:12px;border-radius:8px;">
    <div class="m-topbar">
        <div class="logo"><span class="live-dot"></span>РИСКОВАННЫЕ ПОЕЗДКИ ОНЛАЙН</div>
        <div class="kpi">
            <span>Алармы: <span class="kv">{total_alarms}</span></span>
            <span>Машины: <span class="kv">{unique_vehicles}</span></span>
            <span>Средняя: <span class="kv">{avg_speed:.0f} км/ч</span></span>
        </div>
    </div>

    <div style="display:flex;gap:10px;margin-top:10px;">
        <div style="width:280px;min-width:280px;max-height:450px;overflow-y:auto;">
            <div class="m-section">ТОП СОБЫТИЙ</div>
            {items_html}
        </div>

        <div style="flex:1;min-width:0;">
            <div class="m-section">ВИДЕО</div>
            <div class="m-detail-block" style="min-height:120px;display:flex;align-items:center;justify-content:center;flex-direction:column;">
                <h4 style="font-size:13px;margin:0 0 4px;">📹 {sel_veh}</h4>
                <div style="font-size:10px;color:var(--fg-3);">{sel_type_label} · {sel_speed} км/ч</div>
                <div style="font-size:24px;margin-top:10px;">▶</div>
                <div style="font-size:10px;color:var(--fg-3);margin-top:4px;">Видео не загружено</div>
            </div>
            <div class="m-section" style="margin-top:4px;">КАРТА</div>
            <div class="m-detail-block" style="height:160px;display:flex;align-items:center;justify-content:center;">
                <div style="font-size:10px;color:var(--fg-3);">См. карту в expander ниже</div>
            </div>
        </div>

        <div style="width:340px;max-height:450px;overflow-y:auto;">
            <div class="m-section">ДЕТАЛИ ИНЦИДЕНТА</div>
            {right_html}
        </div>
    </div>

    <div class="m-btm" style="margin-top:8px;">
        <span class="m-ok">● Онлайн</span>
        <span>SKAI — Единое окно видео и телематики</span>
        <span style="margin-left:auto;">{total_alarms} событий · {unique_vehicles} машин</span>
    </div>
</div>
"""


def render_monitor_tab(datasets: dict[str, pd.DataFrame], alarm_type_labels: dict[str, str]) -> None:
    if not datasets:
        st.warning("Нет данных")
        return

    alarms_df = datasets.get("selected_video_alarms")
    if alarms_df is None or alarms_df.empty:
        st.warning("Нет данных об алармах.")
        return

    st.markdown(_MONITOR_CSS, unsafe_allow_html=True)

    from backend.constants import ALARM_TYPE_COLORS

    selected_aid = st.session_state.get("selected_alarm_id")

    monitor_html = _render_monitor_html(datasets, alarm_type_labels, ALARM_TYPE_COLORS, selected_aid)

    st.components.v1.html(monitor_html, height=700, scrolling=True)

    # --- Functional controls below HTML (HTML onclick/postMessage does not work in Streamlit) ---
    alarms_sorted = alarms_df.dropna(subset=["Speed"]).sort_values("Speed", ascending=False)

    event_options = ["— Выберите событие —"]
    event_map = {}
    for _, row in alarms_sorted.iterrows():
        aid = str(row.get("AlarmId", ""))
        veh = str(row.get("UnitStateNumber", "—"))
        typ = alarm_type_labels.get(row.get("Type", ""), row.get("Type", ""))
        spd = float(row.get("Speed", 0))
        lbl = f"{veh} · {typ} · {spd:.0f} км/ч"
        event_options.append(lbl)
        event_map[lbl] = aid

    # Pre-select current event if any
    current_lbl = None
    if selected_aid:
        for lbl, aid in event_map.items():
            if aid == selected_aid:
                current_lbl = lbl
                break

    sel_lbl = st.selectbox(
        "Событие в ленте",
        options=event_options,
        index=event_options.index(current_lbl) if current_lbl else 0,
        key="monitor_event_select",
        label_visibility="collapsed",
    )

    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
    with c1:
        if st.button("📋 Открыть карточку", use_container_width=True):
            if sel_lbl != event_options[0]:
                st.session_state["selected_alarm_id"] = event_map[sel_lbl]
                st.toast("Перейдите во вкладку 🔍 Карточка инцидента")
                st.rerun()
            else:
                st.warning("Сначала выберите событие")
    with c2:
        if st.button("✅ Отметить проверкой", use_container_width=True):
            if sel_lbl != event_options[0]:
                from backend.data_loader import save_action
                aid = event_map[sel_lbl]
                save_action(Path("output"), row_id=aid[:8], action="mark_reviewed")
                st.success("Помечено как проверено")
            else:
                st.warning("Сначала выберите событие")
    with c3:
        if st.button("🎬 Запросить видео", use_container_width=True):
            st.info("Демо-режим: запрос видео недоступен")
    with c4:
        if st.button("📊 Создать отчёт", use_container_width=True):
            if sel_lbl != event_options[0]:
                from backend.data_loader import save_action
                aid = event_map[sel_lbl]
                save_action(Path("output"), row_id=aid[:8], action="export_report")
                st.success("Отчёт сохранён в output/")
            else:
                st.warning("Сначала выберите событие")

    with st.expander("Карта (интерактивная)", expanded=False):
        lat_col = None
        lon_col = None
        for col in alarms_df.columns:
            cl = col.lower()
            if cl in ("latitude", "lat"):
                lat_col = col
            elif cl in ("longitude", "lon"):
                lon_col = col

        if lat_col and lon_col:
            map_df = alarms_df.dropna(subset=[lat_col, lon_col]).copy()
            if len(map_df) > 0:

                def _pick_color(row):
                    speed = row.get("Speed", 0)
                    if pd.notna(speed) and speed > 90:
                        return "#EF4444"
                    if pd.notna(speed) and speed > 70:
                        return "#F97316"
                    if row.get("VideoCount", 0) == 0:
                        return "#F59E0B"
                    return "#3B82F6"

                map_df["color"] = map_df.apply(_pick_color, axis=1)
                map_df = map_df.rename(columns={lat_col: "latitude", lon_col: "longitude"})
                st.map(map_df, latitude="latitude", longitude="longitude", color="color")
            else:
                st.info("Нет координат для карты.")
        else:
            st.info("Координаты не найдены.")
