"""Unit-покрытие STT-сервиса (b8) — §7.3, транскрипция с graceful-fallback.

`faster-whisper` может быть установлен в окружении, поэтому модель **всегда
мокается** (`_get_model`) — никакой загрузки весов и сети. Проверяем:
детерминированный fallback без модели, агрегацию текста/уверенности при наличии
модели, корректную обработку битого и пустого входа.
"""

from __future__ import annotations

import math

import pytest

from api.services import stt_service as stt


# ---------------------------------------------------------------------------
# Тестовые дублёры модели faster-whisper.
# ---------------------------------------------------------------------------


class _Segment:
    def __init__(self, text: str, avg_logprob: float) -> None:
        self.text = text
        self.avg_logprob = avg_logprob


class _Info:
    language = "en"


class _Model:
    """Модель с двумя сегментами — happy-path транскрипции."""

    def transcribe(self, buffer, language=None):  # noqa: ARG002 — сигнатура faster-whisper
        return iter([_Segment("привет ", -0.2), _Segment("мир", -0.1)]), _Info()


class _EmptyModel:
    def transcribe(self, buffer, language=None):  # noqa: ARG002
        return iter([]), _Info()


class _BrokenModel:
    def transcribe(self, buffer, language=None):  # noqa: ARG002
        raise RuntimeError("not a WAV stream")


# ---------------------------------------------------------------------------
# Fallback без модели — детерминированный валидный объект {text,lang,confidence}.
# ---------------------------------------------------------------------------


class TestFallbackWithoutModel:
    def test_empty_input_returns_fallback(self) -> None:
        # Пустой вход не доходит до модели вовсе (graceful).
        assert stt.transcribe(b"") == {"text": "", "lang": "ru", "confidence": 0.0}
        assert stt.transcribe(b"", lang="en") == {
            "text": "",
            "lang": "en",
            "confidence": 0.0,
        }

    def test_no_model_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(stt, "_get_model", lambda: None)
        out = stt.transcribe(b"RIFFsome-bytes")
        assert out == {"text": "", "lang": "ru", "confidence": 0.0}

    def test_fallback_is_deterministic(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(stt, "_get_model", lambda: None)
        first = stt.transcribe(b"same-input", lang="kk")
        second = stt.transcribe(b"same-input", lang="kk")
        assert first == second == {"text": "", "lang": "kk", "confidence": 0.0}


# ---------------------------------------------------------------------------
# С моделью — агрегация текста и уверенности.
# ---------------------------------------------------------------------------


class TestWithModel:
    def test_transcribes_and_aggregates_confidence(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(stt, "_get_model", lambda: _Model())
        out = stt.transcribe(b"RIFFwav-bytes")
        assert out["text"] == "привет мир"  # склейка + strip
        assert out["lang"] == "en"  # из info.language (lang не задан)
        expected = (math.exp(-0.2) + math.exp(-0.1)) / 2
        assert out["confidence"] == pytest.approx(expected)
        assert 0.0 <= out["confidence"] <= 1.0

    def test_explicit_lang_overrides_detection(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(stt, "_get_model", lambda: _Model())
        out = stt.transcribe(b"RIFFwav-bytes", lang="ru")
        assert out["lang"] == "ru"

    def test_empty_segments_zero_confidence(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(stt, "_get_model", lambda: _EmptyModel())
        out = stt.transcribe(b"RIFFsilence", lang="ru")
        assert out == {"text": "", "lang": "ru", "confidence": 0.0}

    def test_broken_audio_raises_value_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Битый/не-WAV поток → ValueError (роутер вернёт 400) — не падает наружу.
        monkeypatch.setattr(stt, "_get_model", lambda: _BrokenModel())
        with pytest.raises(ValueError):
            stt.transcribe(b"not-a-wav")
