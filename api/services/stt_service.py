"""STT-сервис (§7.3): локальная транскрипция голоса на `faster-whisper` `large-v3`.

Языки RU/KK/EN. Модель тяжёлая → **ленивая загрузка** один раз на процесс:
импорт `faster_whisper` и создание `WhisperModel` происходят только внутри
`_get_model()`, поэтому `import stt_service` не тянет тяжёлую зависимость при
старте API. Всё локально: никакого `GROQ`/сети (STT и NLU независимы).
"""

from __future__ import annotations

import io
import math
from typing import Any

from api.core.config import settings

# Ленивый синглтон модели (грузится один раз на процесс при первом transcribe).
_model: Any | None = None
# Флаг недоступности тяжёлой зависимости — чтобы не пытаться импортировать каждый раз.
_model_unavailable = False


def _get_model() -> Any | None:
    """Создаёт и кэширует `WhisperModel` при первом вызове.

    Импорт `faster_whisper` — **внутри** функции (не на уровне модуля). Если
    зависимость/веса недоступны, возвращает `None` (graceful-fallback в `transcribe`).
    """
    global _model, _model_unavailable
    if _model is not None:
        return _model
    if _model_unavailable:
        return None
    try:
        from faster_whisper import WhisperModel  # тяжёлый импорт, изолирован здесь
    except Exception:
        _model_unavailable = True
        return None
    whisper_model = getattr(settings, "whisper_model", "large-v3")
    whisper_device = getattr(settings, "whisper_device", "cpu")
    compute_type = "int8" if whisper_device == "cpu" else "float16"
    try:
        _model = WhisperModel(
            whisper_model, device=whisper_device, compute_type=compute_type
        )
    except Exception:
        _model_unavailable = True
        return None
    return _model


def _fallback(lang: str | None) -> dict:
    """Валидный пустой ответ (нет модели / пустой вход / тишина)."""
    return {"text": "", "lang": lang or "ru", "confidence": 0.0}


def transcribe(wav_bytes: bytes, lang: str | None = None) -> dict:
    """Транскрибирует WAV-байты в текст.

    -> {"text": str, "lang": str, "confidence": float}

    `lang` ∈ {"ru","kk","en"} фиксирует язык; иначе — автоопределение.
    Битый/не-WAV поток → `ValueError` (роутер вернёт 400).
    """
    # Пустой вход не доходит до тяжёлого декодирования.
    if not wav_bytes:
        return _fallback(lang)

    model = _get_model()
    if model is None:
        # Нет модели/весов/`faster-whisper` — детерминированный graceful-fallback.
        return _fallback(lang)

    try:
        segments, info = model.transcribe(io.BytesIO(wav_bytes), language=lang)
        # `segments` — ленивый генератор; материализуем для агрегации.
        segments = list(segments)
    except Exception as exc:  # битый/не-WAV байт-поток
        raise ValueError(f"cannot decode WAV audio: {exc}") from exc

    text = "".join(seg.text for seg in segments).strip()
    resolved_lang = lang or getattr(info, "language", None) or "ru"

    if segments:
        # Среднее exp(avg_logprob) по сегментам, clamp [0,1].
        probs = [math.exp(seg.avg_logprob) for seg in segments]
        confidence = sum(probs) / len(probs)
        confidence = max(0.0, min(1.0, confidence))
    else:
        # Пустое распознавание (тишина) — 0.0 (без NULL).
        confidence = 0.0

    return {"text": text, "lang": resolved_lang, "confidence": confidence}
