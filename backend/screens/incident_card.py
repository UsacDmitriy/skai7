from __future__ import annotations

import json
import base64
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from backend.constants import ALARM_TYPE_LABELS, SPEED_LIMIT_KMH
from backend.data_loader import save_action
from backend.charts import build_track_speed_chart

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

_ANALYSIS: dict[str, str] = {
    "Drowsiness": "Водитель не менял положение руля 40+ секунд. Возможен микросон.",
    "Sabotage": "Камера зафиксировала перекрытие объектива или отключение.",
    "Distraction": "Водитель отвлёкся от дороги более 3 секунд. Риск ДТП повышен.",
    "DangerousDistance": "Несоблюдение безопасной дистанции. Риск попутного столкновения.",
    "SharpAcceleration": "Резкое ускорение. Возможна агрессивная езда.",
    "Yawning": "Система зафиксировала зевание водителя - признак усталости.",
    "Smoking": "Водитель курит во время движения. Нарушение правил.",
    "SeatBelt": "Ремень не пристёгнут. Повышенный риск при ДТП.",
    "NoDriver": "Водитель отсутствует за рулём. Требуется проверка.",
}
_DEFAULT_ANALYSIS = "Событие зафиксировано. Требуется ручная проверка."

_VOICE_JS = """<script>
(function(){
  if(window.__kilo_voice__)return;
  window.__kilo_voice__=true;
  var SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  var recognition=SR?new SR():null;
  var listening=false;var timerInt=null,timerStart=null,timerEl=null;
  var curId=null;
  if(recognition){recognition.lang='ru-RU';recognition.interimResults=true;recognition.continuous=true;}
  function el(id){return document.getElementById(id);}
  window._kiloVoiceStart=function(tid){
    if(!recognition)return;curId=tid;
    if(listening){_kiloVoiceStop();return;}
    try{recognition.start();}catch(e){}
  };
  window._kiloVoiceStop=function(){
    listening=false;
    if(recognition)try{recognition.stop();}catch(e){}
    if(timerInt){clearInterval(timerInt);timerInt=null;}
    var b=el(curId+'-btn'),st=el(curId+'-st'),ta=el(curId);
    var r1=el(curId+'-ring1'),r2=el(curId+'-ring2'),mi=el(curId+'-mic');
    if(b){b.style.borderColor='#E2E8F0';b.style.backgroundColor='#fff';}
    if(mi)mi.setAttribute('stroke','#94A3B8');
    if(r1)r1.style.opacity='0';if(r2)r2.style.opacity='0';
    if(ta){ta.style.backgroundColor='#0F172A';ta.style.opacity='1';}
    if(st){st.style.color='#64748B';st.childNodes[0].textContent='🎤 Нажмите для голосового ввода';}
    if(timerEl){timerEl.remove();timerEl=null;}
  };
  if(recognition){
    recognition.onstart=function(){
      listening=true;
      var b=el(curId+'-btn'),st=el(curId+'-st'),ta=el(curId);
      var r1=el(curId+'-ring1'),r2=el(curId+'-ring2'),mi=el(curId+'-mic');
      if(b){b.style.borderColor='#DC2626';b.style.backgroundColor='#FEF2F2';}
      if(mi)mi.setAttribute('stroke','#DC2626');
      if(r1)r1.style.opacity='1';if(r2)r2.style.opacity='1';
      if(ta){ta.style.backgroundColor='#F8FAFC';ta.style.opacity='0.55';}
      st.style.color='#DC2626';timerStart=Date.now();
      if(!timerEl){timerEl=document.createElement('span');timerEl.style.marginLeft='8px';st.appendChild(timerEl);}
      timerInt=setInterval(function(){var e=Math.floor((Date.now()-timerStart)/1000);timerEl.textContent=String(Math.floor(e/60)).padStart(2,'0')+':'+String(e%60).padStart(2,'0');},500);
      var t=0;(function pa(){if(!listening)return;t+=0.05;
        var s=1+0.15*Math.sin(t);var o=0.3+0.4*Math.sin(t);
        if(r1){r1.style.transform='translate(-50%,-50%) scale('+s+')';r1.style.opacity=o;}
        var s2=1+0.25*Math.sin(t+0.7);var o2=0.15+0.35*Math.sin(t+0.7);
        if(r2){r2.style.transform='translate(-50%,-50%) scale('+s2+')';r2.style.opacity=o2;}
        requestAnimationFrame(pa);
      })();
    };
    recognition.onresult=function(e){
      var f='';for(var i=0;i<e.results.length;i++)if(e.results[i].isFinal)f+=e.results[i][0].transcript;
      if(f){var ta=el(curId);if(ta)ta.value+=f;}
      var st=el(curId+'-st');if(st&&st.childNodes[0])st.childNodes[0].textContent='⏺ Запись… ';
    };
    recognition.onerror=function(e){
      _kiloVoiceStop();var st=el(curId+'-st');
      if(st&&st.childNodes[0]){
        if(e.error==='not-allowed')st.childNodes[0].textContent='❌ Микрофон блокирован';
        else st.childNodes[0].textContent='⚠ Ошибка распознавания';
      }
    };
    recognition.onend=function(){
      if(listening){try{recognition.start();}catch(e){_kiloVoiceStop();}}else _kiloVoiceStop();
    };
  }
})();
</script>"""

_VOICE_CSS = """<style>
.kv-wrap{display:flex;flex-direction:column;gap:8px;max-width:100%}
.kv-row{display:flex;align-items:center;gap:10px}
.kv-ta{flex:1;resize:vertical;border:1px solid #E2E8F0;border-radius:10px;padding:12px 16px;font-size:14px;font-family:-apple-system,sans-serif;min-height:52px;outline:none;line-height:1.5;background:#0F172A;color:#E2E8F0}
.kv-mic{width:52px;height:52px;border-radius:50%;border:2px solid #E2E8F0;background:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:border-color .2s,background-color .2s;position:relative;flex-shrink:0;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.kv-mic:hover{border-color='#94A3B8'}
.kv-ring1,.kv-ring2{position:absolute;width:52px;height:52px;border-radius:50%;border:2px solid #DC2626;opacity:0;pointer-events:none;transform:translate(-50%,-50%);left:50%;top:50%}
.kv-ring2{width:72px;height:72px}
.kv-st{font-size:12px;color:#64748B;font-family:-apple-system,sans-serif}
</style>"""


def _voice_recording_card(widget_id: str, placeholder: str = "Нажмите микрофон и скажите...") -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
<style>
#{widget_id}_wrap{{display:flex;flex-direction:column;align-items:center;gap:12px;padding:24px;background:#1E293B;border-radius:16px;border:1px solid #334155;margin:12px 0;max-width:400px;}}
#{widget_id}_timer{{font-family:-apple-system,sans-serif;font-size:24px;font-weight:700;color:#F1F5F9;letter-spacing:2px;min-height:32px;}}
#{widget_id}_mic_btn{{width:80px;height:80px;border-radius:50%;background:#DC2626;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;position:relative;transition:transform .15s;flex-shrink:0;}}
#{widget_id}_mic_btn:hover{{transform:scale(1.05);}}
#{widget_id}_mic_btn:active{{transform:scale(0.95);}}
#{widget_id}_pulse1,#{widget_id}_pulse2{{position:absolute;width:80px;height:80px;border-radius:50%;border:2px solid #DC2626;opacity:0;pointer-events:none;top:50%;left:50%;transform:translate(-50%,-50%);}}
#{widget_id}_pulse2{{width:110px;height:110px;}}
#{widget_id}_waveform{{display:flex;align-items:center;gap:3px;height:40px;justify-content:center;}}
#{widget_id}_wave_bar{{width:3px;background:#fff;border-radius:2px;transition:height .1s;}}
#{widget_id}_status{{font-family:-apple-system,sans-serif;font-size:13px;color:#94A3B8;}}
#{widget_id}_result{{width:100%;min-height:60px;background:#0F172A;border:1px solid #334155;border-radius:12px;padding:12px 16px;font-size:14px;font-family:-apple-system,sans-serif;color:#E2E8F0;resize:vertical;outline:none;line-height:1.5;}}
#{widget_id}_result::placeholder{{color:#64748B;}}
</style>
</head>
<body>
<div id="{widget_id}_wrap" class="vrc-wrap">
  <div id="{widget_id}_timer" class="vrc-timer"></div>
  <button id="{widget_id}_mic_btn" onclick="window._vrcToggle('{widget_id}')" aria-label="Voice record">
    <svg id="{widget_id}_mic_icon" width="36" height="36" viewBox="0 0 24 24" fill="none"
      stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <rect x="9" y="1" width="6" height="12" rx="3"/>
      <path d="M5 10a7 7 0 0 0 14 0"/>
      <line x1="12" y1="17" x2="12" y2="21"/>
      <line x1="8" y1="21" x2="16" y2="21"/>
    </svg>
    <div id="{widget_id}_pulse1" class="vrc-pulse1"></div>
    <div id="{widget_id}_pulse2" class="vrc-pulse2"></div>
  </button>
  <div id="{widget_id}_waveform" class="vrc-waveform"></div>
  <div id="{widget_id}_status" class="vrc-status">Нажмите для записи</div>
  <textarea id="{widget_id}_result" class="vrc-result" placeholder="{placeholder}" rows="3"></textarea>
</div>
<script>
(function(){{
  if(!window.__VRC_INSTANCES)window.__VRC_INSTANCES={{}};
  if(!window.__VRC_SR){{
    window.__VRC_SR=window.SpeechRecognition||window.webkitSpeechRecognition;
    window.__VRC_GLOBAL_REC=null;
    window.__VRC_ACTIVE_ID=null;
    if(window.__VRC_SR){{
      var rec=new window.__VRC_SR();
      rec.lang='ru-RU';rec.interimResults=true;rec.continuous=true;
      window.__VRC_GLOBAL_REC=rec;
      rec.onresult=function(e){{
        if(!window.__VRC_ACTIVE_ID)return;
        var id=window.__VRC_ACTIVE_ID;
        var inst=window.__VRC_INSTANCES[id];if(!inst)return;
        var f='';for(var i=0;i<e.results.length;i++)f+=e.results[i][0].transcript;
        inst.transcript=f;
        var ra=document.getElementById(id+'_result');if(ra)ra.value=f;
      }};
      rec.onerror=function(ev){{
        var id=window.__VRC_ACTIVE_ID;
        var st2=document.getElementById(id+'_status');
        if(st2){{if(ev.error==='not-allowed')st2.textContent='Микрофон не доступен';
          else st2.textContent='Ошибка распознавания';}}
        var inst=window.__VRC_INSTANCES[id];if(inst){{inst.listening=false;}}
        stopAnim(id);
        var btn3=document.getElementById(id+'_mic_btn');if(btn3)btn3.style.background='#DC2626';
        var p7=document.getElementById(id+'_pulse1');if(p7)p7.style.animation='none';
        var p8=document.getElementById(id+'_pulse2');if(p8)p8.style.animation='none';
        window.__VRC_ACTIVE_ID=null;
      }};
    }}
    if(!document.getElementById('__vrc_pulse_style')){{
      var style=document.createElement('style');style.id='__vrc_pulse_style';
      style.textContent='@keyframes vrcPulse{{0%{{transform:translate(-50%,-50%) scale(1);opacity:.6;}}100%{{transform:translate(-50%,-50%) scale(1.8);opacity:0;}}}}';
      document.head.appendChild(style);
    }}
  }}
  function stopAnim(id){{
    var inst=window.__VRC_INSTANCES[id];if(!inst)return;
    if(inst.timerInt){{clearTimeout(inst.timerInt);inst.timerInt=null;}}
    if(inst.animId){{cancelAnimationFrame(inst.animId);inst.animId=null;}}
  }}
  function startUI(id){{
    var inst=window.__VRC_INSTANCES[id];if(!inst)return;
    inst.listening=true;inst.timerStart=Date.now();inst.transcript='';
    var ra2=document.getElementById(id+'_result');if(ra2)ra2.value='';
    var btn=document.getElementById(id+'_mic_btn');if(btn)btn.style.background='#991B1B';
    var st=document.getElementById(id+'_status');if(st)st.textContent='Нажмите чтобы остановить запись';
    var pulse1=document.getElementById(id+'_pulse1');if(pulse1)pulse1.style.animation='vrcPulse 1s ease-out infinite';
    var pulse2=document.getElementById(id+'_pulse2');if(pulse2)pulse2.style.animation='vrcPulse 1s ease-out infinite .5s';
    function tick(){{if(!inst.listening)return;
      var elapsed=Math.floor((Date.now()-inst.timerStart)/1000);
      var m=String(Math.floor(elapsed/60)).padStart(2,'0');
      var s=String(elapsed%60).padStart(2,'0');
      var te=document.getElementById(id+'_timer');if(te)te.textContent=m+':'+s;
      inst.timerInt=setTimeout(tick,500);}}tick();
    var t=0;function anim(){{if(!inst.listening)return;t+=0.06;
      for(var i=0;i<inst.waveformBars.length;i++){{
        var h=6+Math.abs(Math.sin(t+i*0.5))*24+Math.random()*6;
        if(inst.waveformBars[i])inst.waveformBars[i].style.height=h+'px';}}
      inst.animId=requestAnimationFrame(anim);}}anim();
  }}
  function stopUI(id){{
    var inst=window.__VRC_INSTANCES[id];if(!inst)return;
    inst.listening=false;
    stopAnim(id);
    var btn2=document.getElementById(id+'_mic_btn');if(btn2)btn2.style.background='#DC2626';
    var st3=document.getElementById(id+'_status');if(st3){{
      st3.textContent=inst.transcript?'Распознано: ✓ Нажмите для новой записи':'Нажмите для записи';}}
    var p3=document.getElementById(id+'_pulse1');if(p3)p3.style.animation='none';
    var p4=document.getElementById(id+'_pulse2');if(p4)p4.style.animation='none';
    for(var i=0;i<inst.waveformBars.length;i++){{
      if(inst.waveformBars[i])inst.waveformBars[i].style.height='6px';}}
  }}
  window._vrcToggle=function(id){{
    var inst=window.__VRC_INSTANCES[id];if(!inst)return;
    if(!window.__VRC_GLOBAL_REC){{
      var st4=document.getElementById(id+'_status');
      if(st4)st4.textContent='Распознавание речи не поддерживается браузером';return;}}
    if(inst.listening){{
      stopUI(id);
      try{{window.__VRC_GLOBAL_REC.stop();}}catch(e){{}}
      window.__VRC_ACTIVE_ID=null;
    }}else{{
      window.__VRC_ACTIVE_ID=id;
      try{{window.__VRC_GLOBAL_REC.start();}}catch(e){{}}
      startUI(id);
    }}
  }};
  window._vrcRegister=function(id){{
    if(window.__VRC_INSTANCES[id])return;
    var d={{id:id,listening:false,timerInt:null,timerStart:null,animId:null,
      waveformBars:[],transcript:''}};
    var wrap=document.getElementById(id+'_waveform');
    if(wrap){{for(var i=0;i<20;i++){{var bar=document.createElement('div');
      bar.style.cssText='width:3px;background:#fff;border-radius:2px;transition:height .1s;height:6px;';
      wrap.appendChild(bar);d.waveformBars.push(bar);}}}}
    window.__VRC_INSTANCES[id]=d;
  }};
}})();
(function(){{_vrcRegister('{widget_id}');}})();
</script>
"""


def _load_csv_max_50(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, nrows=50)
    except Exception:
        return pd.DataFrame()


def _load_datasets() -> dict[str, pd.DataFrame]:
    result = {}
    for name in ["selected_video_alarms","video_files","track_summary","track_points","max_speed_points","track_periods","vehicles"]:
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
    m = int(seconds // 60); s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def _get_alarm_detail(datasets, alarm_id: str) -> dict:
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
            tp = tp.sort_values("timestamp_utc").head(50)
        track_points = tp.reset_index(drop=True)

    vehicle = None
    if alarm_row is not None and vehicles_df is not None:
        usn = alarm_row.get("UnitStateNumber")
        if pd.notna(usn):
            mask = vehicles_df["unit_state_number"] == usn
            if mask.any():
                vehicle = vehicles_df[mask].iloc[0]

    return {"alarm": alarm_row, "videos": videos, "track_summary": track_summary,
            "track_points": track_points, "vehicle": vehicle}


def _find_alarm_by_voice(alarm_ids, alarms_df, query: str) -> str | None:
    q = query.lower().replace(" ", "")
    for _, row in alarms_df.iterrows():
        plate = str(row.get("UnitStateNumber", "")).lower().replace(" ", "")
        if q in plate or plate in q:
            return str(row["AlarmId"])
        name = str(row.get("UnitName", "")).lower().replace(" ", "")
        if q in name or name in q:
            return str(row["AlarmId"])
    for raw_type, label in ALARM_TYPE_LABELS.items():
        if label.lower() in query.lower() or raw_type.lower() in query.lower():
            mask = alarms_df["Type"] == raw_type
            if mask.any():
                return str(alarms_df[mask].iloc[0]["AlarmId"])
    return None


def _render_selection(datasets) -> None:
    alarms_df = datasets.get("selected_video_alarms")
    if alarms_df is None or alarms_df.empty:
        st.warning("Нет данных об алармах в ./data/")
        return

    alarm_ids = alarms_df["AlarmId"].dropna().astype(str).unique().tolist() if "AlarmId" in alarms_df.columns else []
    if not alarm_ids:
        st.warning("Нет AlarmId в данных.")
        return

    count = len(alarm_ids)
    st.markdown(
        '<div style="background:#0F172A;padding:24px;border-radius:12px;margin-bottom:16px;">'
        '<h2 style="color:#F1F5F9;font-family:-apple-system,sans-serif;margin:0 0 8px 0;">Выберите инцидент</h2>'
        '<p style="color:#94A3B8;font-size:14px;margin:0;">Доступно: ' + str(count) + ' событий</p></div>',
        unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])
    with col1:
        selected = st.selectbox("AlarmId", options=alarm_ids, label_visibility="collapsed")
    with col2:
        show = st.button("Открыть инцидент", type="primary", use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🎤 Найти голосом", use_container_width=True):
        st.session_state["voice_search"] = not st.session_state.get("voice_search", False)

    if st.session_state.get("voice_search"):
        st.markdown(
            '<p style="color:#94A3B8;font-size:13px;font-family:-apple-system,sans-serif;'
            'margin:-8px 0 8px;">Скажите госномер или тип, например: "М477" или "Зевание"</p>',
            unsafe_allow_html=True)
        st.markdown(_voice_recording_card("voice_search_card", "Нажмите микрофон и скажите госномер или тип..."), unsafe_allow_html=True)
        voice_q = st.text_input("Или введите запрос текстом:", key="voice_manual_q",
                                placeholder='Например: М477, Дросс, Курение')
        if voice_q.strip():
            matched = _find_alarm_by_voice(alarm_ids, alarms_df, voice_q)
            if matched:
                st.success(f"Найден: {matched}")
                if st.button("Открыть найденный", type="primary"):
                    st.session_state["selected_alarm_id"] = matched
                    st.session_state["voice_search"] = False
                    st.rerun()
            else:
                st.info(f'По запросу "{voice_q}" совпадений не найдено')

    if show:
        st.session_state["selected_alarm_id"] = selected
        st.session_state["voice_search"] = False
        st.rerun()


def _render_voice_comment_box() -> None:
    st.markdown("### 🎤 Голосовой комментарий")
    st.markdown(
        '<p style="color:#94A3B8;font-size:12px;font-family:-apple-system,sans-serif;'
        'margin:-8px 0 10px;">Запишите голосом комментарий к инциденту</p>',
        unsafe_allow_html=True)
    st.markdown(_voice_recording_card("voice_comment", "Комментарий к инциденту..."), unsafe_allow_html=True)
    st.text_input("Voice comment store", key="_voice_comment_store", label_visibility="collapsed")


_CSS = """
<style>
.kilo-incident-card{background:#0F172A;border-radius:16px;overflow:hidden;border:1px solid #1E293B;max-width:1100px}
.kilo-card-header{background:#1E293B;padding:16px 24px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #334155}
.kilo-card-header-left{display:flex;align-items:center;gap:12px}
.kilo-header-icon{width:32px;height:32px;background:#3B82F6;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px}
.kilo-header-title{font-family:-apple-system,sans-serif;font-weight:700;font-size:18px;color:#F1F5F9}
.kilo-badge{display:flex;align-items:center;gap:6px;padding:6px 14px;border-radius:20px;font-family:-apple-system,sans-serif;font-weight:600;font-size:14px}
.kilo-body{display:grid;grid-template-columns:1fr 1fr;gap:0}
.kilo-section{padding:20px 24px}
.kilo-section+.kilo-section{border-left:1px solid #1E293B}
.kilo-video-area{background:#020617;border-radius:10px;padding:16px;margin-bottom:16px;min-height:140px;display:flex;align-items:center;justify-content:center;position:relative}
.kilo-video-placeholder{text-align:center;color:#475569;font-family:-apple-system,sans-serif}
.kilo-video-placeholder-icon{font-size:36px;margin-bottom:8px}
.kilo-live-badge{position:absolute;top:8px;right:8px;background:#DC2626;color:#fff;font-family:-apple-system,sans-serif;font-weight:700;font-size:11px;padding:4px 10px;border-radius:4px;letter-spacing:.5px;display:flex;align-items:center;gap:6px}
.kilo-live-dot{width:6px;height:6px;background:#fff;border-radius:50%;animation:kilo-pulse 1.5s ease-in-out infinite}
@keyframes kilo-pulse{0%,100%{opacity:1}50%{opacity:.3}}
.kilo-meta-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.kilo-chip{display:flex;align-items:center;gap:6px;padding:6px 12px;border-radius:20px;font-family:-apple-system,sans-serif;font-size:13px;font-weight:500}
.kilo-chip-red{background:#1C1017;color:#FCA5A5;border:1px solid #7F1D1D}
.kilo-chip-blue{background:#0C1A2E;color:#93C5FD;border:1px solid #1E3A5F}
.kilo-chip-yellow{background:#1C1A0C;color:#FDE68A;border:1px solid #78350F}
.kilo-chip-green{background:#0C1F14;color:#86EFAC;border:1px solid #14532D}
.kilo-chip-purple{background:#1A0C2E;color:#D8B4FE;border:1px solid #581C87}
.kilo-chip-gray{background:#1E293B;color:#94A3B8;border:1px solid #334155}
.kilo-section-title{font-family:-apple-system,sans-serif;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#64748B;margin:0 0 12px;padding-bottom:8px;border-bottom:1px solid #1E293B}
.kilo-field{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #1E293B}
.kilo-field:last-child{border-bottom:none}
.kilo-field-label{font-family:-apple-system,sans-serif;font-size:13px;color:#64748B}
.kilo-field-value{font-family:-apple-system,sans-serif;font-size:13px;color:#E2E8F0;font-weight:500;text-align:right}
.kilo-timeline{background:#1E293B;border-radius:8px;padding:12px;margin-top:12px}
.kilo-timeline-bar{height:6px;background:#334155;border-radius:3px;position:relative;margin-bottom:8px}
.kilo-timeline-active{position:absolute;height:100%;background:#3B82F6;border-radius:3px}
.kilo-timeline-labels{display:flex;justify-content:space-between;font-family:-apple-system,sans-serif;font-size:10px;color:#64748B}
.kilo-alert-box{background:#1C1017;border:1px solid #7F1D1D;border-radius:8px;padding:12px;margin:12px 0}
.kilo-alert-title{font-family:-apple-system,sans-serif;font-size:12px;font-weight:600;color:#FCA5A5;margin-bottom:4px}
.kilo-alert-text{font-family:-apple-system,sans-serif;font-size:12px;color:#F87171;line-height:1.4}
.kilo-video-table{width:100%;font-family:-apple-system,sans-serif;font-size:11px;color:#94A3B8;border-collapse:collapse;margin-top:8px}
.kilo-video-table td{padding:6px 8px;border-bottom:1px solid #1E293B}
.kilo-video-table td:first-child{color:#64748B}
</style>"""


def _alarm_badge(type_str: str, speed: float) -> tuple[str, str]:
    label = ALARM_TYPE_LABELS.get(type_str, type_str)
    badge_map = {
        "Drowsiness":("kilo-chip-red","😴"), "Yawning":("kilo-chip-red","😴"),
        "Distraction":("kilo-chip-yellow","📱"), "Sabotage":("kilo-chip-red","📷"),
        "DangerousDistance":("kilo-chip-yellow","🚗"), "SharpAcceleration":("kilo-chip-yellow","⚡"),
        "Smoking":("kilo-chip-purple","🚬"), "SeatBelt":("kilo-chip-blue","🔒"),
        "NoDriver":("kilo-chip-red","🚫"),
    }
    chip_class, emoji = badge_map.get(type_str, ("kilo-chip-gray","⚠"))
    return label, chip_class, emoji


def _render_incident_card(alarm_id: str, datasets, type_labels) -> None:
    detail = _get_alarm_detail(datasets, alarm_id)
    alarm = detail["alarm"]
    if alarm is None:
        st.warning(f"Аларм '{alarm_id}' не найден.")
        return

    # --- Left sidebar: event list + navigation ---
    alarms_df = datasets.get("selected_video_alarms")
    left_col, right_col = st.columns([1, 3])

    with left_col:
        st.markdown("#### Лента событий")
        if alarms_df is not None and not alarms_df.empty and "AlarmId" in alarms_df.columns:
            sorted_alarms = alarms_df.dropna(subset=["Speed"]).sort_values("Speed", ascending=False)
            event_options = []
            event_map = {}
            for _, row in sorted_alarms.iterrows():
                aid = str(row.get("AlarmId", ""))
                veh = str(row.get("UnitStateNumber", "—"))
                typ = type_labels.get(row.get("Type", ""), row.get("Type", ""))
                spd = float(row.get("Speed", 0))
                lbl = f"{veh} · {typ} · {spd:.0f} км/ч"
                event_options.append(lbl)
                event_map[lbl] = aid

            current_lbl = None
            for lbl, aid in event_map.items():
                if aid == alarm_id:
                    current_lbl = lbl
                    break

            sel_lbl = st.selectbox(
                "Событие",
                options=event_options,
                index=event_options.index(current_lbl) if current_lbl else 0,
                key="incident_card_event_select",
                label_visibility="collapsed",
            )
            if sel_lbl and event_map.get(sel_lbl) != alarm_id:
                st.session_state["selected_alarm_id"] = event_map[sel_lbl]
                st.rerun()

            # Navigation buttons
            alarm_ids = list(event_map.values())
            current_idx = alarm_ids.index(alarm_id) if alarm_id in alarm_ids else -1
            nav1, nav2 = st.columns(2)
            with nav1:
                if st.button("← Предыдущий", disabled=(current_idx <= 0), use_container_width=True):
                    st.session_state["selected_alarm_id"] = alarm_ids[current_idx - 1]
                    st.rerun()
            with nav2:
                if st.button("Следующий →", disabled=(current_idx < 0 or current_idx >= len(alarm_ids) - 1), use_container_width=True):
                    st.session_state["selected_alarm_id"] = alarm_ids[current_idx + 1]
                    st.rerun()
        else:
            st.caption("Нет данных для ленты")

        if st.button("← Назад к списку", use_container_width=True):
            st.session_state["selected_alarm_id"] = None
            st.rerun()

    # --- Right side: incident card (HTML) ---
    with right_col:
        unit_sn = str(alarm.get("UnitStateNumber","—"))
        raw_type = str(alarm.get("Type","—"))
        speed_val = float(alarm["Speed"]) if pd.notna(alarm.get("Speed")) else 0.0
        begin = str(alarm.get("Begin","—"))
        end = str(alarm.get("End","—"))
        address = str(alarm.get("Address",""))

        label, badge_class, badge_emoji = _alarm_badge(raw_type, speed_val)
        videos = detail["videos"]
        track_summary = detail["track_summary"]
        track_points = detail["track_points"]
        has_videos = not videos.empty
        first_video_path = _get_video_path(videos.iloc[0]) if has_videos else None

        total_mileage = float(track_summary.get("total_mileage_km",0)) if track_summary is not None and pd.notna(track_summary.get("total_mileage_km")) else 0.0
        total_duration = track_summary.get("total_movement_duration","—") if track_summary is not None else "—"
        parking_duration = track_summary.get("total_parking_duration","—") if track_summary is not None else "—"

        total_video_size = int(videos["size_bytes"].sum()) if has_videos and "size_bytes" in videos.columns else 0
        total_video_duration = float(videos["duration_seconds"].sum()) if has_videos and "duration_seconds" in videos.columns else 0.0
        video_count = int(alarm.get("VideoCount",0)) if pd.notna(alarm.get("VideoCount")) else 0

        risk_level = "high" if speed_val > SPEED_LIMIT_KMH else ("medium" if speed_val > 60 else "low")
        risk_color = {"high":"#DC2626","medium":"#EAB308","low":"#16A34A"}[risk_level]
        risk_label = {"high":"Высокий риск","medium":"Средний риск","low":"Низкий риск"}[risk_level]

        analysis = _ANALYSIS.get(raw_type, _DEFAULT_ANALYSIS)
        chips_html = _build_chips(raw_type, speed_val, total_mileage, begin)
        timeline_pct = _calc_timeline(track_points, begin, end)

        html = f"""<div class="kilo-incident-card">
  <div class="kilo-card-header">
    <div class="kilo-card-header-left">
      <div class="kilo-header-icon">📺</div>
      <span class="kilo-header-title">Карточка инцидента</span>
    </div>
    <div class="kilo-badge {badge_class}"><span>{badge_emoji}</span><span>{label}</span></div>
  </div>
  <div class="kilo-body">
    <div class="kilo-section"><p class="kilo-section-title">Видео события</p>
      <div class="kilo-video-area">
        <div class="kilo-live-badge"><div class="kilo-live-dot"></div>LIVE</div>"""

        if first_video_path:
            data_url = _encode_video_base64(first_video_path)
            if data_url:
                html += f'<video controls style="max-width:100%;border-radius:8px;" preload="metadata"><source src="{data_url}" type="video/mp4">Видео не поддерживается.</video>'
            else:
                html += '<div class="kilo-video-placeholder"><div class="kilo-video-placeholder-icon">📷</div><div>Видео слишком большое для предпросмотра</div></div>'
        else:
            html += '<div class="kilo-video-placeholder"><div class="kilo-video-placeholder-icon">📷</div><div>Нет видео для предпросмотра</div></div>'

        html += '</div>'

        if has_videos:
            html += '<table class="kilo-video-table">'
            for _, v in videos.head(5).iterrows():
                ch = int(v.get("channel",0))
                dur = _format_duration(v.get("duration_seconds",0))
                sz_bytes = int(v.get("size_bytes",0))
                sz = f"{sz_bytes/1024/1024:.1f} МБ" if sz_bytes > 0 else "—"
                html += f"<tr><td>Канал {ch}</td><td>{dur}</td><td>{sz}</td></tr>"
            html += '</table>'
        else:
            html += '<p style="color:#64748B;font-size:13px;margin-top:8px;">Нет связанных видео</p>'

        html += f"""<div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;">
      <span class="kilo-chip kilo-chip-blue">📹 Камер: {video_count}</span>
      <span class="kilo-chip kilo-chip-blue">💾 {total_video_size/1024/1024:.1f} МБ</span>
      <span class="kilo-chip kilo-chip-blue">⏱ {_format_duration(total_video_duration)}</span>
    </div></div>
    <div class="kilo-section"><p class="kilo-section-title">Телеметрия и контекст</p>
    <div class="kilo-meta-row">{chips_html}</div>
    <div class="kilo-field"><span class="kilo-field-label">Госномер</span><span class="kilo-field-value">{unit_sn}</span></div>
    <div class="kilo-field"><span class="kilo-field-label">Скорость</span><span class="kilo-field-value" style="color:{risk_color};">{speed_val:.0f} км/ч</span></div>
    <div class="kilo-field"><span class="kilo-field-label">Время</span><span class="kilo-field-value">{begin} — {end}</span></div>"""

        if address and address != "nan":
            html += f'<div class="kilo-field"><span class="kilo-field-label">Адрес</span><span class="kilo-field-value">{address}</span></div>'

        html += f"""
    <div class="kilo-field"><span class="kilo-field-label">Пробег трека</span><span class="kilo-field-value">{total_mileage:.1f} км</span></div>
    <div class="kilo-field"><span class="kilo-field-label">Движение</span><span class="kilo-field-value">{total_duration}</span></div>
    <div class="kilo-field"><span class="kilo-field-label">Стоянка</span><span class="kilo-field-value">{parking_duration}</span></div>
    <div class="kilo-field"><span class="kilo-field-label">Скорость / Лимит</span><span class="kilo-field-value">{speed_val:.0f} / {SPEED_LIMIT_KMH} км/ч</span></div>
    <div class="kilo-timeline"><div class="kilo-timeline-bar"><div class="kilo-timeline-active" style="width:{timeline_pct}%;left:0;"></div></div><div class="kilo-timeline-labels"><span>{begin}</span><span>{end}</span></div></div>
    <div class="kilo-alert-box" style="border-color:{risk_color}40;background:{risk_color}10;">
      <div class="kilo-alert-title" style="color:{risk_color};">⚡ Анализ: {risk_label}</div>
      <div class="kilo-alert-text" style="color:{risk_color}">{analysis}</div>
    </div></div></div></div>"""

        st.markdown(_CSS, unsafe_allow_html=True)
        st.markdown(html, unsafe_allow_html=True)

        # Speed chart
        if not track_points.empty and "speed_kmh" in track_points.columns:
            st.markdown("#### График скорости")
            chart = build_track_speed_chart(track_points, alarm_id, ["#3B82F6"])
            st.altair_chart(chart, use_container_width=True)
        else:
            st.caption("Нет данных трека для графика скорости")

        # Actions
        st.markdown("### Действия")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("✅ Проверено", use_container_width=True):
                save_action(OUTPUT_DIR, row_id=f"{alarm_id[:8]}_{unit_sn}", action="mark_reviewed")
                st.toast("Помечено")
        with col2:
            if st.button("📋 Заявка", use_container_width=True):
                save_action(OUTPUT_DIR, row_id=f"{alarm_id[:8]}_{unit_sn}", action="create_task")
                st.toast("Заявка создана")
        with col3:
            if st.button("📄 Отчёт", use_container_width=True):
                save_action(OUTPUT_DIR, row_id=f"{alarm_id[:8]}_{unit_sn}", action="export_report")
                _export_report(alarm_id)
                st.toast("Отчёт сохранён")
        with col4:
            if st.button("← К списку", use_container_width=True):
                st.session_state["selected_alarm_id"] = None
                st.rerun()

        _render_voice_comment_box()


def _build_chips(raw_type: str, speed: float, mileage: float, begin: str) -> str:
    chips = ""
    if speed > SPEED_LIMIT_KMH:
        chips += f'<span class="kilo-chip kilo-chip-red">⚠ Превышение: {speed:.0f} км/ч</span>'
    elif speed > 60:
        chips += f'<span class="kilo-chip kilo-chip-yellow">🟡 Скорость: {speed:.0f} км/ч</span>'
    if raw_type in ("Drowsiness","Yawning"):
        chips += '<span class="kilo-chip kilo-chip-red">😴 Усталость водителя</span>'
    if raw_type == "Sabotage":
        chips += '<span class="kilo-chip kilo-chip-red">🚫 Саботаж камеры</span>'
    if mileage > 0:
        chips += f'<span class="kilo-chip kilo-chip-green">🛣 {mileage:.1f} км</span>'
    try:
        h = pd.Timestamp(begin).strftime("%H:%M")
    except Exception:
        h = "—"
    chips += f'<span class="kilo-chip kilo-chip-blue">🕐 {h}</span>'
    return chips


def _calc_timeline(track_points, begin: str, end: str) -> float:
    if track_points.empty or "timestamp_utc" not in track_points.columns:
        return 10.0
    try:
        b = pd.Timestamp(begin); e = pd.Timestamp(end)
        total = (e - b).total_seconds()
        if total <= 0:
            return 10.0
        first = pd.Timestamp(track_points["timestamp_utc"].iloc[0])
        last = pd.Timestamp(track_points["timestamp_utc"].iloc[-1])
        return min(max(round((last - first).total_seconds() / total * 100, 1), 5.0), 100.0)
    except Exception:
        return 10.0


def _encode_video_base64(path: Path) -> str:
    import base64
    if path.stat().st_size > 5 * 1024 * 1024:
        return ""
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:video/mp4;base64,{data}"


def _export_report(alarm_id: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rpt = OUTPUT_DIR / f"incident_{alarm_id[:8]}.md"
    datasets = _load_datasets()
    detail = _get_alarm_detail(datasets, alarm_id)
    alarm = detail["alarm"]
    if alarm is None:
        return
    lines = [f"# Инцидент {alarm_id[:8]}",
             f"- Госномер: {alarm.get('UnitStateNumber', '—')}",
             f"- Тип: {ALARM_TYPE_LABELS.get(str(alarm.get('Type', '')), str(alarm.get('Type', '')))}",
             f"- Скорость: {alarm.get('Speed', '?')} км/ч",
             f"- Время: {alarm.get('Begin', '—')} — {alarm.get('End', '—')}",
             f"- Адрес: {alarm.get('Address', '—')}",
             f"\n## Анализ: {_ANALYSIS.get(str(alarm.get('Type', '')), _DEFAULT_ANALYSIS)}"]
    if not detail["videos"].empty:
        lines.append(f"\n## Видео ({len(detail['videos'])})")
        for _, v in detail["videos"].head(5).iterrows():
            p = _get_video_path(v)
            lines.append(f"- Канал {v.get('channel', '?')}: {p or 'нет файла'}")
    if detail["track_summary"] is not None:
        lines.append("\n## Телеметрия")
        for col in detail["track_summary"].index:
            if pd.notna(detail["track_summary"][col]):
                lines.append(f"- {col}: {detail['track_summary'][col]}")
    lines.append(f"\n---\nОтчёт: {datetime.now().isoformat()}")
    rpt.write_text("\n".join(lines), encoding="utf-8")


def render_incident_card_screen() -> None:
    datasets = _load_datasets()
    selected_id = st.session_state.get("selected_alarm_id")
    if not selected_id:
        _render_selection(datasets)
    else:
        if st.button("← К списку"):
            st.session_state["selected_alarm_id"] = None
            st.session_state["voice_search"] = False
            st.rerun()
        _render_incident_card(selected_id, datasets, ALARM_TYPE_LABELS)
