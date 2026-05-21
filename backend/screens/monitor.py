from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import altair as alt

from backend.constants import ALARM_TYPE_LABELS, SPEED_LIMIT_KMH
from backend.data_loader import save_action

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
MEDIA_ROOT = PROJECT_ROOT / "datasets" / "media" / "video_events"

_RISK_TONES = {
    "crit": {
        "dot": "#EF4444",
        "bg": "rgba(239,68,68,0.12)",
        "fg": "#FCA5A5",
        "label": "Критический",
    },
    "high": {
        "dot": "#F97316",
        "bg": "rgba(249,115,22,0.12)",
        "fg": "#FDBA74",
        "label": "Высокий",
    },
    "med": {
        "dot": "#F59E0B",
        "bg": "rgba(245,158,11,0.12)",
        "fg": "#FDE68A",
        "label": "Средний",
    },
    "normal": {
        "dot": "#3B82F6",
        "bg": "rgba(59,130,246,0.12)",
        "fg": "#93C5FD",
        "label": "Нормальный",
    },
}

_CSS_RAW = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root {
  --bg-app: #0F1117;
  --bg-canvas: #181A24;
  --bg-sunken: #13151D;
  --bg-alt: #1F2231;
  --border-1: #252838;
  --border-2: #2E3244;
  --fg-1: #E8EAF0;
  --fg-2: #8B90A0;
  --fg-3: #5C6070;
  --primary: #3B82F6;
  --primary-soft: #1E3A5F;
  --danger: #EF4444;
  --danger-ink: #FCA5A5;
  --danger-soft: rgba(239,68,68,0.12);
  --warning: #F59E0B;
  --warning-ink: #FDE68A;
  --warning-soft: rgba(245,158,11,0.12);
  --high: #F97316;
  --high-ink: #FDBA74;
  --high-soft: rgba(249,115,22,0.12);
  --success: #22C55E;
  --success-ink: #86EFAC;
  --success-soft: rgba(34,197,94,0.12);
  --plate-bg: #0C1A2E;
  --plate-fg: #93C5FD;
}
.m-wrap { font-family: 'Inter', -apple-system, sans-serif; background: var(--bg-app); color: var(--fg-1); border-radius: 8px; overflow: hidden; }
.m-topbar { display:flex; align-items:center; height:56px; padding:0 16px; gap:14px; background:var(--bg-canvas); border-bottom:1px solid var(--border-1); }
.m-logo { display:flex; align-items:center; gap:8px; font-weight:700; font-size:13px; color:var(--primary); letter-spacing:1px; }
.m-logo-s { width:28px; height:28px; border-radius:8px; display:flex; align-items:center; justify-content:center; background:var(--primary); color:#fff; font-weight:700; font-size:14px; }
.m-live-dot { width:8px; height:8px; border-radius:50%; background:var(--danger); animation: m-pulse 1.5s ease-in-out infinite; }
@keyframes m-pulse { 0%,100%{opacity:1;box-shadow:0 0 4px var(--danger);} 50%{opacity:0.35;box-shadow:0 0 12px var(--danger);} }
.m-kpi { margin-left:auto; display:flex; gap:16px; font-size:11px; color:var(--fg-2); }
.m-kpi .kv { color:var(--fg-1); font-weight:600; }
.m-search { background:var(--bg-sunken); border:1px solid var(--border-1); border-radius:6px; padding:6px 10px; font-size:12px; color:var(--fg-1); outline:none; width:160px; }
.m-shift-time { font-size:11px; color:var(--fg-3); font-variant-numeric: tabular-nums; }

.m-timeline-wrap { background:var(--bg-canvas); border-right:1px solid var(--border-1); height:100%; min-height:520px; display:flex; flex-direction:column; }
.m-timeline-header { padding:12px 14px 8px; }
.m-timeline-title { font-size:10px; text-transform:uppercase; letter-spacing:1px; font-weight:600; color:var(--fg-2); margin-bottom:8px; }
.m-timeline-filters { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:6px; }
.m-timeline-filter { display:inline-flex; align-items:center; gap:4px; padding:4px 10px; border-radius:999px; font-size:11px; font-weight:500; border:1px solid var(--border-1); cursor:pointer; }
.m-timeline-body { flex:1; overflow-y:auto; padding:0 14px 14px; position:relative; }
.m-timeline-spine { position:absolute; left:19px; top:8px; bottom:14px; width:1px; background:var(--border-2); }
.m-timeline-item { position:relative; padding-left:28px; padding-bottom:14px; cursor:pointer; }
.m-timeline-tick { position:absolute; left:14px; top:3px; width:10px; height:10px; border-radius:50%; border:2px solid var(--bg-canvas); }
.m-timeline-tick.live { width:12px; height:12px; left:13px; top:2px; }
.m-timeline-time { font-size:10px; color:var(--fg-3); font-variant-numeric:tabular-nums; margin-bottom:2px; }
.m-timeline-veh { font-size:12px; font-weight:600; color:var(--fg-1); }
.m-timeline-type { font-size:11px; color:var(--fg-2); line-height:1.3; }
.m-timeline-meta { font-size:10px; color:var(--fg-3); margin-top:2px; }
.m-timeline-badge { display:inline-block; font-size:9px; font-weight:600; padding:1px 5px; border-radius:4px; margin-top:4px; }

.m-center { padding:12px; display:flex; flex-direction:column; gap:10px; }
.m-bigvideo { position:relative; width:100%; border-radius:12px; overflow:hidden; background:#000; border:1px solid var(--border-2); aspect-ratio:16/9; }
.m-bigvideo-overlay { position:absolute; top:10px; left:10px; display:flex; gap:6px; }
.m-bigvideo-chip { font-size:11px; padding:3px 8px; border-radius:6px; background:rgba(15,23,42,0.85); color:#E2E8F0; backdrop-filter:blur(6px); font-weight:500; }
.m-bigvideo-rec { display:inline-flex; align-items:center; gap:3px; font-size:10px; font-weight:700; letter-spacing:0.5px; padding:3px 8px; border-radius:6px; background:var(--danger); color:#fff; }
.m-bigvideo-time { position:absolute; top:10px; right:10px; font-size:11px; padding:3px 8px; border-radius:6px; background:rgba(15,23,42,0.85); color:#E2E8F0; backdrop-filter:blur(6px); font-variant-numeric:tabular-nums; }
.m-bigvideo-play { position:absolute; bottom:10px; left:10px; width:32px; height:32px; border-radius:50%; background:rgba(15,23,42,0.85); color:#fff; display:flex; align-items:center; justify-content:center; font-size:14px; cursor:pointer; border:1px solid var(--border-2); }

.m-map-wrap { border-radius:10px; overflow:hidden; border:1px solid var(--border-2); background:var(--bg-sunken); height:260px; }
.m-minicams { display:flex; flex-direction:column; gap:6px; }
.m-minicam { position:relative; border-radius:8px; overflow:hidden; background:#0B1220; border:1px solid var(--border-2); aspect-ratio:16/9; }
.m-minicam-label { position:absolute; left:4px; top:4px; font-size:9px; padding:1px 5px; border-radius:4px; background:rgba(0,0,0,0.7); color:#fff; font-weight:600; }
.m-minicam-rec { position:absolute; right:4px; top:4px; font-size:8px; padding:1px 4px; border-radius:4px; background:rgba(242,44,44,0.95); color:#fff; font-weight:700; }
.m-minicam-time { position:absolute; right:4px; bottom:4px; font-size:9px; padding:1px 5px; border-radius:4px; background:rgba(0,0,0,0.6); color:#CBD5E1; font-variant-numeric:tabular-nums; }

.m-right { background:var(--bg-canvas); border-left:1px solid var(--border-1); height:100%; min-height:520px; display:flex; flex-direction:column; padding:12px 14px; gap:10px; overflow-y:auto; }
.m-right-block { background:var(--bg-sunken); border:1px solid var(--border-1); border-radius:8px; padding:10px 12px; }
.m-right-block h5 { font-size:9px; text-transform:uppercase; letter-spacing:0.7px; color:var(--fg-3); margin:0 0 8px; font-weight:600; }
.m-plate { font-family:ui-monospace, monospace; font-size:15px; font-weight:700; padding:3px 10px; border-radius:6px; background:var(--plate-bg); color:var(--plate-fg); display:inline-block; }
.m-score-pill { display:inline-flex; align-items:center; gap:4px; padding:4px 10px; border-radius:999px; font-size:11px; font-weight:600; }
.m-dl { font-size:11px; color:var(--fg-1); margin:4px 0; display:flex; justify-content:space-between; }
.m-dl .label { color:var(--fg-2); }
.m-dl .value { font-weight:500; }
.m-desc-box { padding:8px 10px; border-radius:8px; font-size:12px; line-height:1.4; }
.m-desc-box .title { font-weight:600; margin-bottom:2px; }
.m-btn { width:100%; padding:8px 12px; margin:3px 0; border-radius:6px; border:1px solid var(--border-2); background:var(--bg-sunken); color:var(--fg-1); font-size:12px; font-weight:500; cursor:pointer; transition:all .12s; text-align:left; }
.m-btn:hover { border-color:var(--primary); background:var(--primary-soft); }
.m-btn.primary { background:var(--success); border-color:var(--success); color:#fff; }
.m-btn.danger { background:var(--danger); border-color:var(--danger); color:#fff; }

.m-btm { display:flex; align-items:center; height:32px; padding:0 14px; gap:12px; background:var(--bg-canvas); border-top:1px solid var(--border-1); font-size:10px; color:var(--fg-2); }
.m-btm .sep { width:1px; height:12px; background:var(--border-1); }
.m-btm .ok { color:var(--success); font-weight:600; }
.m-btm .bad { color:var(--danger-ink); }
.m-btm .val { color:var(--fg-1); font-weight:600; font-variant-numeric:tabular-nums; }
"""

_CSS = f"<style>{_CSS_RAW}</style>"


def _embed_css(fragment: str) -> str:
    return f"<style>{_CSS_RAW}</style>\n{fragment}"


def _severity(speed: float, video_count: int) -> str:
    if speed > 90:
        return "crit"
    if speed > 70:
        return "high"
    if video_count == 0:
        return "med"
    return "normal"


def _get_video_path(row: pd.Series) -> Path | None:
    media = row.get("media_relative_path", "")
    if pd.isna(media) or not media:
        return None
    p = PROJECT_ROOT / str(media)
    return p if p.exists() else None


def _encode_video_base64(path: Path) -> str:
    if path.stat().st_size > 8 * 1024 * 1024:
        return ""
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:video/mp4;base64,{data}"


def _fmt_time(iso: str) -> str:
    try:
        return pd.Timestamp(iso).strftime("%H:%M:%S")
    except Exception:
        return str(iso)[-8:] if len(str(iso)) >= 8 else str(iso)


def _build_top_bar(total_alarms: int, unique_vehicles: int, avg_speed: float, shift_time: str) -> str:
    return f"""
<div class="m-topbar">
  <div class="m-logo"><div class="m-logo-s">S</div><span>РИСКОВАННЫЕ ПОЕЗДКИ ОНЛАЙН</span></div>
  <div class="m-live-dot"></div>
  <div class="m-kpi">
    <span>Алармы: <span class="kv">{total_alarms}</span></span>
    <span>Машины: <span class="kv">{unique_vehicles}</span></span>
    <span>Средняя скорость: <span class="kv">{avg_speed:.0f} км/ч</span></span>
  </div>
  <div style="margin-left:auto;" class="m-shift-time">{shift_time}</div>
</div>
"""


def _build_left_timeline(
    alarms_df: pd.DataFrame,
    alarm_labels: dict[str, str],
    selected_id: str | None,
    filter_level: str,
) -> str:
    if alarms_df is None or alarms_df.empty:
        return '<div style="padding:20px;color:var(--fg-3);font-size:12px;">Нет событий</div>'

    # Counts
    counts = {"all": len(alarms_df), "crit": 0, "high": 0, "med": 0}
    for _, r in alarms_df.iterrows():
        s = _severity(float(r.get("Speed", 0)), int(r.get("VideoCount", 0)) if pd.notna(r.get("VideoCount")) else 0)
        if s in counts:
            counts[s] += 1

    filters_html = ""
    for k, label, n in [("all", "Все", counts["all"]), ("crit", "Крит.", counts["crit"]), ("high", "Высок.", counts["high"]), ("med", "Сред.", counts["med"])]:
        active = "background:var(--primary);color:#fff;border-color:transparent;" if filter_level == k else ""
        filters_html += f'<span class="m-timeline-filter" style="{active}">{label}<span style="opacity:.8;margin-left:3px;">{n}</span></span>'

    # Filter rows
    rows = []
    sorted_df = alarms_df.dropna(subset=["Speed"]).sort_values("Speed", ascending=False)
    for _, r in sorted_df.iterrows():
        aid = str(r.get("AlarmId", ""))
        speed = float(r.get("Speed", 0))
        vc = int(r.get("VideoCount", 0)) if pd.notna(r.get("VideoCount")) else 0
        sev = _severity(speed, vc)
        if filter_level != "all" and sev != filter_level:
            continue
        rows.append((aid, r, speed, vc, sev))

    items_html = ""
    for aid, r, speed, vc, sev in rows:
        tone = _RISK_TONES.get(sev, _RISK_TONES["normal"])
        veh = str(r.get("UnitStateNumber", "—"))
        raw_type = str(r.get("Type", "—"))
        label = alarm_labels.get(raw_type, raw_type)
        begin = str(r.get("Begin", ""))
        t_str = _fmt_time(begin)
        selected_class = " style='background:var(--bg-alt);border-radius:6px;padding:4px;margin:0 -4px;'" if aid == selected_id else ""
        live_badge = '<span class="m-timeline-badge" style="background:var(--danger-soft);color:var(--danger-ink);">● LIVE</span>' if vc > 0 else ""
        items_html += f"""
<div class="m-timeline-item"{selected_class}>
  <div class="m-timeline-tick" style="background:{tone['dot']};box-shadow:0 0 0 2px var(--bg-canvas);"></div>
  <div class="m-timeline-time">{t_str}</div>
  <div class="m-timeline-veh">{veh}</div>
  <div class="m-timeline-type">{label}</div>
  <div class="m-timeline-meta">{speed:.0f} км/ч · {vc} 📹</div>
  {live_badge}
</div>"""

    return f"""
<div class="m-timeline-wrap">
  <div class="m-timeline-header">
    <div class="m-timeline-title">Лента смены</div>
    <div class="m-timeline-filters">{filters_html}</div>
  </div>
  <div class="m-timeline-body">
    <div class="m-timeline-spine"></div>
    {items_html}
  </div>
</div>
"""


def _build_big_video(alarm_row: pd.Series | None, video_path: Path | None, videos_df: pd.DataFrame) -> str:
    if alarm_row is None:
        return '<div class="m-bigvideo" style="display:flex;align-items:center;justify-content:center;color:var(--fg-3);font-size:12px;">Выберите событие</div>'

    veh = str(alarm_row.get("UnitStateNumber", "—"))
    raw_type = str(alarm_row.get("Type", "—"))
    begin = str(alarm_row.get("Begin", ""))
    t_str = _fmt_time(begin)

    # Try real video first
    video_tag = ""
    if video_path is not None:
        data_url = _encode_video_base64(video_path)
        if data_url:
            video_tag = f'<video controls style="width:100%;height:100%;object-fit:cover;" preload="metadata"><source src="{data_url}" type="video/mp4"></video>'

    if not video_tag:
        # SVG pseudo-scene (reference style)
        video_tag = """
<svg viewBox="0 0 800 450" preserveAspectRatio="none" style="width:100%;height:100%;display:block;">
  <defs>
    <linearGradient id="bvRoad" x1="0" y1="1" x2="0" y2="0">
      <stop offset="0" stop-color="#0F172A"/>
      <stop offset="1" stop-color="#1E293B" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="800" height="450" fill="#050810"/>
  <path d="M0 450 L320 220 L480 220 L800 450 Z" fill="url(#bvRoad)"/>
  <path d="M400 450 L420 250 L432 190" stroke="#FCD34D" stroke-width="2" stroke-dasharray="4 8" fill="none" opacity=".6"/>
  <path d="M400 450 L380 250 L368 190" stroke="#FCD34D" stroke-width="2" stroke-dasharray="4 8" fill="none" opacity=".6"/>
  <path d="M0 450 L0 360 Q400 320 800 360 L800 450 Z" fill="#020409"/>
  <ellipse cx="320" cy="380" rx="70" ry="20" fill="#0B1220"/>
  <ellipse cx="320" cy="378" rx="55" ry="14" fill="none" stroke="#1E293B" stroke-width="2"/>
  <g transform="translate(360,340)">
    <ellipse cx="0" cy="60" rx="110" ry="35" fill="#0B1220"/>
    <circle cx="-40" cy="40" r="22" fill="#1F2937"/>
    <path d="M-62 42 Q-40 60 -18 42" stroke="#0F172A" stroke-width="3" fill="none"/>
  </g>
  <circle cx="60" cy="40" r="0.8" fill="#fff" opacity=".5"/>
  <circle cx="120" cy="30" r="0.8" fill="#fff" opacity=".5"/>
  <circle cx="200" cy="55" r="0.8" fill="#fff" opacity=".5"/>
  <circle cx="280" cy="30" r="0.8" fill="#fff" opacity=".5"/>
  <circle cx="520" cy="40" r="0.8" fill="#fff" opacity=".5"/>
  <circle cx="640" cy="30" r="0.8" fill="#fff" opacity=".5"/>
  <circle cx="710" cy="55" r="0.8" fill="#fff" opacity=".5"/>
  <circle cx="740" cy="30" r="0.8" fill="#fff" opacity=".5"/>
</svg>"""

    # Mini cam count
    cam_count = len(videos_df) if not videos_df.empty else int(alarm_row.get("VideoCount", 0))

    return f"""
<div class="m-bigvideo">
  {video_tag}
  <div class="m-bigvideo-overlay">
    <span class="m-bigvideo-chip">Cam 1 · фронт</span>
    <span class="m-bigvideo-rec">● REC</span>
  </div>
  <div class="m-bigvideo-time">{t_str}</div>
  <div style="position:absolute;bottom:10px;left:10px;font-size:10px;color:#fff;background:rgba(15,23,42,0.7);padding:3px 8px;border-radius:6px;">{veh} · {raw_type}</div>
  <div style="position:absolute;bottom:10px;right:10px;font-size:10px;color:var(--fg-3);background:rgba(15,23,42,0.7);padding:3px 8px;border-radius:6px;">{cam_count} камер</div>
</div>
"""


def _build_map_leaflet(
    alarms_df: pd.DataFrame,
    alarm_coords: dict[str, tuple[float, float]],
    selected_id: str | None,
    center_lat: float,
    center_lon: float,
    track_line: list[tuple[float, float]] | None = None,
) -> str:
    if alarms_df is None or alarms_df.empty or not alarm_coords:
        return '<div style="height:260px;display:flex;align-items:center;justify-content:center;color:var(--fg-3);font-size:12px;">Нет координат</div>'

    markers_js = ""
    for _, r in alarms_df.iterrows():
        aid = str(r.get("AlarmId", ""))
        coords = alarm_coords.get(aid)
        if coords is None:
            continue
        lat, lon = coords
        speed = float(r.get("Speed", 0))
        vc = int(r.get("VideoCount", 0)) if pd.notna(r.get("VideoCount")) else 0
        sev = _severity(speed, vc)
        tone = _RISK_TONES.get(sev, _RISK_TONES["normal"])
        is_sel = aid == selected_id
        size = 18 if is_sel else 12
        pulse = "true" if is_sel and sev == "crit" else "false"
        markers_js += f"""
(function(){{
  var color = '{tone['dot']}';
  var html = '<div style=\"color:'+color+';position:relative;width:36px;height:36px;\">'+
    '<div class=\"ring\" style=\"display:{('block' if is_sel else 'none')};position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:28px;height:28px;border-radius:50%;border:2px solid '+color+';animation:m-pulse 1.5s ease-in-out infinite;\"></div>'+
    '<div style=\"background:'+color+';position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:{size}px;height:{size}px;border-radius:50%;border:2px solid #181A24;\"></div></div>';
  var icon = L.divIcon({{className:'',html:html,iconSize:[36,36],iconAnchor:[18,18]}});
  var m = L.marker([{lat},{lon}],{{icon:icon}}).addTo(map);
}})();
"""

    track_js = ""
    if track_line and len(track_line) > 1:
        pts = ",".join([f"[{lat},{lon}]" for lat, lon in track_line])
        track_js = f"L.polyline([{pts}],{{color:'#3B82F6',weight:3,opacity:0.7}}).addTo(map);"

    return f"""
<div class="m-map-wrap" id="live-map"></div>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
(function(){{
  var map = L.map('live-map', {{center:[{center_lat},{center_lon}],zoom:11,zoomControl:false}});
  L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{{z}}/{{x}}/{{y}}{{r}}.png', {{
    maxZoom:19, subdomains:'abcd', attribution:'© OSM · CARTO'
  }}).addTo(map);
  L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{{z}}/{{x}}/{{y}}{{r}}.png', {{
    maxZoom:19, subdomains:'abcd', opacity:0.85
  }}).addTo(map);
  {markers_js}
  {track_js}
}})();
</script>
"""



def _build_minicams(videos_df: pd.DataFrame, begin: str) -> str:
    t_str = _fmt_time(begin)
    cams = []
    if not videos_df.empty and "channel" in videos_df.columns:
        for _, v in videos_df.iterrows():
            ch = int(v.get("channel", 0))
            label = f"Cam {ch}"
            cams.append(label)
    else:
        cams = ["Cam 2 · салон", "Cam 3 · правая", "Cam 4 · задняя"]

    items = ""
    for i, lbl in enumerate(cams[:3]):
        items += f"""
<div class="m-minicam">
  <div style="position:absolute;inset:0;background:radial-gradient(ellipse at 50% 60%, #1E1B2E 0%, #050810 70%);"></div>
  <div class="m-minicam-label">{lbl}</div>
  <div class="m-minicam-rec">● REC</div>
  <div class="m-minicam-time">{t_str}</div>
</div>"""

    return f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
  <span style="font-size:10px;text-transform:uppercase;letter-spacing:1px;font-weight:600;color:var(--fg-2);">Другие камеры</span>
  <span style="font-size:10px;color:var(--fg-3);">{len(cams)}/4 онлайн</span>
</div>
<div class="m-minicams">{items}</div>
"""


def _build_right_panel(
    alarm_row: pd.Series | None,
    track_summary: pd.Series | None,
    videos_df: pd.DataFrame,
    alarm_labels: dict[str, str],
) -> str:
    if alarm_row is None:
        return '<div style="padding:30px;text-align:center;color:var(--fg-3);font-size:12px;">Выберите событие из ленты</div>'

    veh = str(alarm_row.get("UnitStateNumber", "—"))
    raw_type = str(alarm_row.get("Type", "—"))
    label = alarm_labels.get(raw_type, raw_type)
    speed = float(alarm_row.get("Speed", 0))
    begin = str(alarm_row.get("Begin", "—"))
    end = str(alarm_row.get("End", "—"))
    address = str(alarm_row.get("Address", ""))
    if address == "nan":
        address = ""
    vc = int(alarm_row.get("VideoCount", 0)) if pd.notna(alarm_row.get("VideoCount")) else 0
    sev = _severity(speed, vc)
    tone = _RISK_TONES.get(sev, _RISK_TONES["normal"])
    # Score heuristic
    score = min(100, max(0, int(speed * 1.1))) if speed > 0 else 30
    if sev == "crit":
        score = max(score, 85)
    elif sev == "high":
        score = max(score, 65)

    total_mileage = (
        float(track_summary.get("total_mileage_km", 0))
        if track_summary is not None and pd.notna(track_summary.get("total_mileage_km"))
        else 0.0
    )
    total_duration = (
        str(track_summary.get("total_movement_duration", "—"))
        if track_summary is not None
        else "—"
    )

    desc = {
        "Drowsiness": "Водитель не менял положение руля 40+ секунд. Возможен микросон.",
        "Sabotage": "Камера зафиксировала перекрытие объектива или отключение.",
        "Distraction": "Водитель отвлёкся от дороги более 3 секунд. Риск ДТП повышен.",
        "DangerousDistance": "Несоблюдение безопасной дистанции. Риск попутного столкновения.",
        "SharpAcceleration": "Резкое ускорение. Возможна агрессивная езда.",
        "Yawning": "Система зафиксировала зевание водителя — признак усталости.",
        "Smoking": "Водитель курит во время движения. Нарушение правил.",
        "SeatBelt": "Ремень не пристёгнут. Повышенный риск при ДТП.",
    }.get(raw_type, "Событие зафиксировано. Требуется ручная проверка.")

    video_size = int(videos_df["size_bytes"].sum()) if not videos_df.empty and "size_bytes" in videos_df.columns else 0
    video_dur = float(videos_df["duration_seconds"].sum()) if not videos_df.empty and "duration_seconds" in videos_df.columns else 0.0
    video_info = f"{vc} файлов · {video_size/1024/1024:.1f} МБ · {int(video_dur)} с" if vc else "Нет видео"

    return f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;gap:8px;">
  <span style="font-size:10px;text-transform:uppercase;letter-spacing:1px;font-weight:600;color:var(--fg-2);">Инцидент</span>
  <span style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;padding:2px 8px;border-radius:999px;background:{tone['bg']};color:{tone['fg']};display:inline-flex;align-items:center;gap:4px;">
    <span style="width:6px;height:6px;border-radius:50%;background:{tone['dot']}"></span>{tone['label']}
  </span>
</div>

<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:10px;">
  <span class="m-plate">{veh}</span>
  <div class="m-score-pill" style="background:{tone['bg']};color:{tone['fg']};">
    <span style="font-size:9px;text-transform:uppercase;letter-spacing:.1em;">Score</span>
    <span style="font-size:18px;font-weight:700;line-height:1;">{score}</span>
  </div>
</div>

<div style="margin-bottom:10px;">
  <div style="font-size:14px;font-weight:600;color:var(--fg-1);line-height:1.2;">{label}</div>
  <div style="font-size:11px;color:var(--fg-2);margin-top:2px;">{raw_type}</div>
</div>

<div class="m-desc-box" style="background:{tone['bg']};color:{tone['fg']};margin-bottom:10px;">
  <div class="title">⚡ Анализ</div>
  <div style="opacity:.9;">{desc}</div>
</div>

<div class="m-right-block">
  <h5>Телеметрия</h5>
  <div class="m-dl"><span class="label">Скорость</span><span class="value" style="color:{'var(--danger-ink)' if speed>90 else 'var(--fg-1)'}">{speed:.0f} км/ч</span></div>
  <div class="m-dl"><span class="label">Лимит</span><span class="value">{SPEED_LIMIT_KMH} км/ч</span></div>
  <div class="m-dl"><span class="label">Начало</span><span class="value">{begin}</span></div>
  <div class="m-dl"><span class="label">Окончание</span><span class="value">{end}</span></div>
  {'<div class="m-dl"><span class="label">Адрес</span><span class="value">'+address+'</span></div>' if address else ''}
  <div class="m-dl"><span class="label">Пробег трека</span><span class="value">{total_mileage:.1f} км</span></div>
  <div class="m-dl"><span class="label">Движение</span><span class="value">{total_duration}</span></div>
</div>

<div class="m-right-block">
  <h5>Видео</h5>
  <div class="m-dl"><span class="label">Камеры</span><span class="value">{vc}</span></div>
  <div class="m-dl"><span class="label">Инфо</span><span class="value">{video_info}</span></div>
</div>
"""


def _build_bottom_bar(total_alarms: int, unique_vehicles: int) -> str:
    return f"""
<div class="m-btm">
  <span class="ok">● Онлайн</span>
  <span class="sep"></span>
  <span>Алармы: <span class="val">{total_alarms}</span></span>
  <span>Машины: <span class="val">{unique_vehicles}</span></span>
  <span class="sep"></span>
  <span style="margin-left:auto;color:var(--fg-3);">SKAI — Единое окно видео и телематики</span>
</div>
"""


def _build_speed_chart(track_points: pd.DataFrame) -> alt.Chart | None:
    if track_points.empty or "speed_kmh" not in track_points.columns:
        return None
    tp = track_points.copy()
    tp["t"] = pd.to_datetime(tp["timestamp_utc"], errors="coerce")
    tp = tp.dropna(subset=["t", "speed_kmh"]).sort_values("t").head(200)
    if tp.empty:
        return None
    tp["time_label"] = tp["t"].dt.strftime("%H:%M:%S")

    chart = (
        alt.Chart(tp)
        .mark_area(opacity=0.25, color="#3B82F6")
        .encode(
            x=alt.X("t:T", title=None, axis=alt.Axis(format="%H:%M", labelColor="#8B90A0", tickColor="#252838", domainColor="#252838")),
            y=alt.Y("speed_kmh:Q", title="км/ч", axis=alt.Axis(labelColor="#8B90A0", tickColor="#252838", domainColor="#252838", gridColor="#1E293B")),
        )
        + alt.Chart(tp)
        .mark_line(color="#3B82F6", strokeWidth=2)
        .encode(x="t:T", y="speed_kmh:Q")
        + alt.Chart(pd.DataFrame({"y": [SPEED_LIMIT_KMH]}))
        .mark_rule(color="#EF4444", strokeDash=[4, 4])
        .encode(y="y:Q")
    )
    chart = chart.configure_view(strokeWidth=0).configure_axis(grid=True).properties(height=140)
    return chart


def _get_alarm_detail(datasets: dict[str, pd.DataFrame], alarm_id: str) -> dict:
    alarms_df = datasets.get("selected_video_alarms")
    video_files_df = datasets.get("video_files")
    track_summary_df = datasets.get("track_summary")
    track_points_df = datasets.get("track_points")

    alarm_row = None
    if alarms_df is not None and "AlarmId" in alarms_df.columns:
        mask = alarms_df["AlarmId"] == alarm_id
        if mask.any():
            alarm_row = alarms_df[mask].iloc[0]

    videos = pd.DataFrame()
    if video_files_df is not None and "alarm_id" in video_files_df.columns:
        videos = video_files_df[video_files_df["alarm_id"] == alarm_id].reset_index(drop=True)

    track_summary = None
    if track_summary_df is not None and "alarm_id" in track_summary_df.columns:
        mask = track_summary_df["alarm_id"] == alarm_id
        if mask.any():
            track_summary = track_summary_df[mask].iloc[0]

    track_points = pd.DataFrame()
    if track_points_df is not None and "alarm_id" in track_points_df.columns:
        tp = track_points_df[track_points_df["alarm_id"] == alarm_id]
        if not tp.empty and "timestamp_utc" in tp.columns:
            tp = tp.sort_values("timestamp_utc").head(200)
        track_points = tp.reset_index(drop=True)

    return {
        "alarm": alarm_row,
        "videos": videos,
        "track_summary": track_summary,
        "track_points": track_points,
    }


def render_monitor_tab(datasets: dict[str, pd.DataFrame], alarm_type_labels: dict[str, str]) -> None:
    alarms_df = datasets.get("selected_video_alarms")
    if alarms_df is None or alarms_df.empty:
        st.warning("Нет данных об алармах.")
        return

    total_alarms = len(alarms_df)
    unique_vehicles = alarms_df["UnitStateNumber"].nunique() if "UnitStateNumber" in alarms_df.columns else 0
    avg_speed = alarms_df["Speed"].mean() if "Speed" in alarms_df.columns else 0.0
    shift_time = datetime.now().strftime("%H:%M:%S")

    # Session state for selection and filter
    selected_aid = st.session_state.get("selected_alarm_id")
    filter_level = st.session_state.get("monitor_filter", "all")

    # Top bar
    st.components.v1.html(
        _embed_css(_build_top_bar(total_alarms, unique_vehicles, avg_speed, shift_time)),
        height=60,
    )

    # Main columns
    left_col, center_col, right_col = st.columns([1.0, 2.2, 1.2])

    with left_col:
        # Filter buttons (streamlit)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("Все", key="mf_all", use_container_width=True):
                st.session_state["monitor_filter"] = "all"
                st.rerun()
        with c2:
            if st.button("Крит.", key="mf_crit", use_container_width=True):
                st.session_state["monitor_filter"] = "crit"
                st.rerun()
        with c3:
            if st.button("Высок.", key="mf_high", use_container_width=True):
                st.session_state["monitor_filter"] = "high"
                st.rerun()
        with c4:
            if st.button("Сред.", key="mf_med", use_container_width=True):
                st.session_state["monitor_filter"] = "med"
                st.rerun()

        # Timeline HTML
        timeline_html = _build_left_timeline(alarms_df, alarm_type_labels, selected_aid, filter_level)
        st.components.v1.html(_embed_css(timeline_html), height=520, scrolling=True)

        # Event selector
        sorted_df = alarms_df.dropna(subset=["Speed"]).sort_values("Speed", ascending=False)
        event_options = ["— Выберите событие —"]
        event_map = {}
        for _, row in sorted_df.iterrows():
            aid = str(row.get("AlarmId", ""))
            veh = str(row.get("UnitStateNumber", "—"))
            typ = alarm_type_labels.get(row.get("Type", ""), row.get("Type", ""))
            spd = float(row.get("Speed", 0))
            lbl = f"{veh} · {typ} · {spd:.0f} км/ч"
            event_options.append(lbl)
            event_map[lbl] = aid

        current_lbl = None
        if selected_aid:
            for lbl, aid in event_map.items():
                if aid == selected_aid:
                    current_lbl = lbl
                    break

        sel_lbl = st.selectbox(
            "Событие",
            options=event_options,
            index=event_options.index(current_lbl) if current_lbl else 0,
            key="monitor_event_select",
            label_visibility="collapsed",
        )
        if sel_lbl != event_options[0] and event_map.get(sel_lbl) != selected_aid:
            st.session_state["selected_alarm_id"] = event_map[sel_lbl]
            st.rerun()

    with center_col:
        detail = _get_alarm_detail(datasets, selected_aid) if selected_aid else {"alarm": None, "videos": pd.DataFrame(), "track_summary": None, "track_points": pd.DataFrame()}
        alarm = detail["alarm"]
        videos = detail["videos"]
        track_points = detail["track_points"]

        # Determine primary video path
        video_path = None
        if not videos.empty:
            first = videos.iloc[0]
            video_path = _get_video_path(first)

        # Big video
        big_video_html = _build_big_video(alarm, video_path, videos)
        st.components.v1.html(_embed_css(big_video_html), height=260)

        # Map + minicams row
        map_col, cam_col = st.columns([3, 1])
        with map_col:
            # Leaflet map HTML
            center_lat, center_lon = 55.7558, 37.6173
            if alarm is not None:
                lat = alarm.get("Latitude")
                lon = alarm.get("Longitude")
                if pd.notna(lat) and pd.notna(lon):
                    center_lat, center_lon = float(lat), float(lon)
            map_html = _build_map_leaflet(alarms_df, selected_aid, center_lat, center_lon)
            st.components.v1.html(_embed_css(map_html), height=260)

        with cam_col:
            begin = str(alarm.get("Begin", "")) if alarm is not None else ""
            minicams_html = _build_minicams(videos, begin)
            st.components.v1.html(_embed_css(minicams_html), height=260)

        # Speed chart
        chart = _build_speed_chart(track_points)
        if chart is not None:
            st.markdown("<div style='font-size:10px;text-transform:uppercase;letter-spacing:1px;font-weight:600;color:#8B90A0;margin:8px 0 4px;'>График скорости</div>", unsafe_allow_html=True)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.caption("Нет данных трека для графика")

    with right_col:
        detail = _get_alarm_detail(datasets, selected_aid) if selected_aid else {"alarm": None, "videos": pd.DataFrame(), "track_summary": None, "track_points": pd.DataFrame()}
        right_html = _build_right_panel(detail["alarm"], detail["track_summary"], detail["videos"], alarm_type_labels)
        st.components.v1.html(_embed_css(right_html), height=520, scrolling=True)

        if selected_aid and detail["alarm"] is not None:
            unit_sn = str(detail["alarm"].get("UnitStateNumber", ""))
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("📋 Отчёт", use_container_width=True, key="mon_report"):
                    save_action(OUTPUT_DIR, row_id=f"{selected_aid[:8]}_{unit_sn}", action="export_report")
                    st.toast("Отчёт сохранён")
            with c2:
                if st.button("✅ Проверено", use_container_width=True, key="mon_verify"):
                    save_action(OUTPUT_DIR, row_id=f"{selected_aid[:8]}_{unit_sn}", action="mark_reviewed")
                    st.toast("Помечено как проверено")
            with c3:
                if st.button("🔍 Карточка", use_container_width=True, key="mon_card"):
                    st.session_state["active_tab"] = "🔍 Карточка инцидента"
                    st.rerun()
        else:
            st.button("📋 Отчёт", use_container_width=True, disabled=True, key="mon_report_d")
            st.button("✅ Проверено", use_container_width=True, disabled=True, key="mon_verify_d")
            st.button("🔍 Карточка", use_container_width=True, disabled=True, key="mon_card_d")

    # Bottom bar
    st.components.v1.html(_embed_css(_build_bottom_bar(total_alarms, unique_vehicles)), height=40)
