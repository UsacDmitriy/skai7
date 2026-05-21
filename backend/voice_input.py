"""Голосовой ввод через Streamlit — гибридный faster-whisper / мок."""

from __future__ import annotations

import base64
import os
import random
import re
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WHISPER_AVAILABLE = False
try:
    from faster_whisper import WhisperModel

    WHISPER_AVAILABLE = True
except Exception:  # pragma: no cover
    pass


MOCK_PRESETS: dict[str, str] = {
    "driver_violations": "Покажи нарушения по Иванову за последние три дня",
    "critical_events": "Критические события за последнюю неделю",
    "video_digest": "Собери видео по превышениям скорости за сегодня",
    "fleet_summary": "Сводка по всем ТС с рейтингом риска за неделю",
    "top5_drivers": "Топ-5 водителей с самым большим количеством нарушений",
}

MOCK_FALLBACKS: list[str] = [
    "Покажи нарушения по Иванову за последние три дня",
    "все алармы О802УЕ198",
    "Критические события у Петрова",
    "Сводка по парку за неделю",
    "Топ-5 водителей с нарушениями",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_whisper_model() -> "WhisperModel | None":
    """Lazy-load faster-whisper model."""
    if not WHISPER_AVAILABLE:
        return None
    # Cache model in session_state to avoid reloading on every rerun
    if "_whisper_model" not in st.session_state:
        st.session_state["_whisper_model"] = WhisperModel("base", compute_type="int8")
    return st.session_state["_whisper_model"]


def _save_b64_audio(b64_string: str, suffix: str = ".wav") -> str:
    """Decode base64 audio blob and save to a temp file."""
    raw = base64.b64decode(b64_string)
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        os.write(fd, raw)
    finally:
        os.close(fd)
    return path


def _generate_mock_wav() -> str:
    """Generate a dummy WAV file for mock mode."""
    fd, path = tempfile.mkstemp(suffix=".wav")
    try:
        # Minimal valid WAV header (44 bytes) + 1 second of silence (44100 * 2 bytes)
        header = b"RIFF\x2c\x89\x01\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00" \
                 b"\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x08\x89\x01\x00"
        silence = b"\x00" * 88200
        os.write(fd, header + silence)
    finally:
        os.close(fd)
    return path


# ---------------------------------------------------------------------------
# 1. create_voice_recorder_ui
# ---------------------------------------------------------------------------

def create_voice_recorder_ui(key: str) -> str | None:
    """Return path to saved WAV or None.

    Uses an inline HTML/JS recorder via ``st.components.v1.html``.  The JS captures
    audio via ``MediaRecorder``, encodes it as base64 and posts it back through
    Streamlit's custom-component messaging (here simulated via a hidden textarea
    that Streamlit polls).  In mock mode a dummy file is returned immediately.
    """
    unique_key = f"voice_{key}_{uuid.uuid4().hex[:8]}"

    # Mock shortcut — no real browser recording needed
    if not WHISPER_AVAILABLE:
        return _generate_mock_wav()

    html_code = f"""
    <div id="rec_{unique_key}" style="font-family:sans-serif;">
      <button id="btn_{unique_key}" style="padding:10px 20px;border:none;border-radius:8px;
        background:#DC2626;color:white;font-size:16px;cursor:pointer;">
        🎙 Начать запись
      </button>
      <div id="status_{unique_key}" style="margin-top:8px;color:#64748B;font-size:12px;"></div>
      <textarea id="out_{unique_key}" style="display:none;"></textarea>
    </div>
    <script>
    (function() {{
      const btn = document.getElementById('btn_{unique_key}');
      const status = document.getElementById('status_{unique_key}');
      const out = document.getElementById('out_{unique_key}');
      let mediaRecorder, chunks = [], recording = false;
      const startRecording = async () => {{
        try {{
          const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
          mediaRecorder = new MediaRecorder(stream);
          chunks = [];
          mediaRecorder.ondataavailable = e => {{ if (e.data.size > 0) chunks.push(e.data); }};
          mediaRecorder.onstop = () => {{
            const blob = new Blob(chunks, {{ type: 'audio/wav' }});
            const reader = new FileReader();
            reader.onloadend = () => {{
              out.value = reader.result.split(',')[1];
              out.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }};
            reader.readAsDataURL(blob);
            status.textContent = 'Запись сохранена';
            btn.style.background = '#1E3A8A';
            btn.textContent = '🎙 Начать запись';
            recording = false;
          }};
          mediaRecorder.start();
          recording = true;
          btn.style.background = '#991B1B';
          btn.textContent = '⏹ Остановить запись';
          status.textContent = 'Идёт запись...';
        }} catch (err) {{
          status.textContent = 'Ошибка доступа к микрофону: ' + err.message;
        }}
      }};
      btn.addEventListener('click', () => {{
        if (!recording) startRecording();
        else mediaRecorder.stop();
      }});
    }})();
    </script>
    """

    st.components.v1.html(html_code, height=120)

    # Poll for returned base64 via a text_area that mirrors the hidden textarea
    b64_audio = st.text_area(
        "voice_buffer",
        key=unique_key,
        label_visibility="collapsed",
        height=1,
    )

    if b64_audio and len(b64_audio) > 100:
        try:
            return _save_b64_audio(b64_audio)
        except Exception:
            return None
    return None


# ---------------------------------------------------------------------------
# 2. transcribe_audio
# ---------------------------------------------------------------------------

def transcribe_audio(audio_path: str, preset_key: str | None = None) -> str:
    """Transcribe audio to text.

    If *faster-whisper* is installed, runs real inference.  Otherwise returns a
    mock string — either from *preset_key* or randomly from ``MOCK_FALLBACKS``.
    """
    model = _get_whisper_model()
    if model is not None and Path(audio_path).exists():
        try:
            segments, _ = model.transcribe(audio_path, language="ru", beam_size=5)
            return " ".join(segment.text for segment in segments)
        except Exception:
            # Fallback to mock on any whisper error
            pass

    if preset_key and preset_key in MOCK_PRESETS:
        return MOCK_PRESETS[preset_key]

    return random.choice(MOCK_FALLBACKS)


# ---------------------------------------------------------------------------
# 3. render_voice_input_block
# ---------------------------------------------------------------------------

def render_voice_input_block() -> dict:
    """Render full voice-input block for State A of the interactive report screen.

    Returns a dict with keys:
    - ``text`` (str) — recognised or typed text
    - ``submitted`` (bool) — whether the *Сформировать отчёт* button was pressed
    - ``mode`` (str) — ``"typed"`` or ``"voice"``
    """
    result = {"text": "", "submitted": False, "mode": "typed"}

    st.markdown(
        """
        <style>
        .voice-pulse {
            animation: pulse 1.5s infinite;
            box-shadow: 0 0 0 0 rgba(220,38,38,0.7);
        }
        @keyframes pulse {
            0%   { box-shadow: 0 0 0 0 rgba(220,38,38,0.7); }
            70%  { box-shadow: 0 0 0 10px rgba(220,38,38,0); }
            100% { box-shadow: 0 0 0 0 rgba(220,38,38,0); }
        }
        .voice-wave {
            display: inline-block;
            width: 100%;
            height: 24px;
            background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 50%, #1E3A8A 100%);
            background-size: 200% 100%;
            animation: wave 2s linear infinite;
            border-radius: 4px;
            opacity: 0.3;
        }
        @keyframes wave {
            0%   { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1, 12])

    recording = st.session_state.get("_voice_recording", False)

    with col1:
        mic_label = "⏹" if recording else "🎙"
        if st.button(mic_label, key="voice_mic_btn", help="Нажмите для записи голоса"):
            st.session_state["_voice_recording"] = not recording
            st.rerun()

    with col2:
        st.caption("faster-whisper RU · KK · EN")

    # Visual feedback
    if recording:
        st.markdown(
            '<div class="voice-pulse" style="padding:4px 8px;border-radius:6px;'
            'background:#FEE2E2;color:#991B1B;font-size:12px;margin-bottom:4px;">'
            '🔴 Идёт запись… говорите сейчас</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="voice-wave"></div>', unsafe_allow_html=True)

    # Text area
    placeholder = "Введите запрос голосом или клавиатурой…"
    typed_text = st.text_area(
        "report_query",
        value=st.session_state.get("_voice_text", ""),
        placeholder=placeholder,
        height=120,
        key="voice_text_area",
        label_visibility="collapsed",
    )

    # If recording is active (mock / demo path) we "inject" a random preset after a short delay
    if recording:
        # In a real app we would call create_voice_recorder_ui + transcribe_audio here.
        # For the MVP we simulate immediate transcription so the UX feels responsive.
        chosen_preset = random.choice(list(MOCK_PRESETS.values()))
        st.session_state["_voice_text"] = chosen_preset
        st.session_state["_voice_recording"] = False
        st.session_state["_voice_submitted"] = False
        st.rerun()

    # Track whether text originated from voice or keyboard
    mode = "voice" if st.session_state.get("_voice_text") == typed_text and typed_text else "typed"

    # Submit button
    btn_cols = st.columns([1, 1, 1])
    with btn_cols[1]:
        submitted = st.button("Сформировать отчёт", use_container_width=True, key="voice_submit_btn")

    result["text"] = typed_text or ""
    result["submitted"] = submitted
    result["mode"] = mode

    # Clear cached voice text after submission so next rerun starts fresh
    if submitted:
        st.session_state.pop("_voice_text", None)

    return result


__all__ = [
    "create_voice_recorder_ui",
    "transcribe_audio",
    "render_voice_input_block",
    "WHISPER_AVAILABLE",
    "MOCK_PRESETS",
    "MOCK_FALLBACKS",
]
