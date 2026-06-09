"""Unit tests for b24: ai_flags + ai_runtime (§8.6)."""
from __future__ import annotations

import os
import json
import time
from pathlib import Path

import pytest

from api.core.ai_flags import (
    AiFeatureState,
    AiFlags,
    FeatureDisabledResponse,
    flags,
    require_feature,
)
from api.core.ai_runtime import (
    ai_call,
    disabled_state,
    DEFAULT_LATENCY_BUDGETS,
)


# ---------------------------------------------------------------------------
# AiFlags tests
# ---------------------------------------------------------------------------

class TestAiFlags:
    def test_all_enabled_by_default(self):
        f = AiFlags()
        for name in ("scene", "forecast", "zones", "fatigue", "copilot", "verdict"):
            assert f.is_enabled(name) is True

    def test_flag_disabled_via_env(self, monkeypatch):
        monkeypatch.setenv("SKAI_AI_FORECAST", "false")
        f = AiFlags()
        assert f.is_enabled("forecast") is False

    def test_flag_disabled_zero(self, monkeypatch):
        monkeypatch.setenv("SKAI_AI_SCENE", "0")
        f = AiFlags()
        assert f.is_enabled("scene") is False

    def test_flag_disabled_off(self, monkeypatch):
        monkeypatch.setenv("SKAI_AI_ZONES", "off")
        f = AiFlags()
        assert f.is_enabled("zones") is False

    def test_flag_enabled_explicit_true(self, monkeypatch):
        monkeypatch.setenv("SKAI_AI_FATIGUE", "true")
        f = AiFlags()
        assert f.is_enabled("fatigue") is True

    def test_unknown_feature_defaults_to_true(self):
        f = AiFlags()
        assert f.is_enabled("nonexistent_feature") is True

    def test_reload_picks_up_new_env(self, monkeypatch):
        f = AiFlags()
        assert f.is_enabled("verdict") is True
        monkeypatch.setenv("SKAI_AI_VERDICT", "0")
        f.reload()
        assert f.is_enabled("verdict") is False

    def test_as_dict_has_all_flags(self):
        f = AiFlags()
        d = f.as_dict()
        for name in ("scene", "forecast", "zones", "fatigue", "copilot", "verdict"):
            assert name in d

    def test_require_feature_true(self):
        # Module singleton — default all enabled
        old = os.environ.pop("SKAI_AI_SCENE", None)
        flags.reload()
        assert require_feature("scene") is True
        if old:
            os.environ["SKAI_AI_SCENE"] = old

    def test_require_feature_false(self, monkeypatch):
        monkeypatch.setenv("SKAI_AI_COPILOT", "false")
        flags.reload()
        assert require_feature("copilot") is False
        # Cleanup: restore
        monkeypatch.delenv("SKAI_AI_COPILOT", raising=False)
        flags.reload()


# ---------------------------------------------------------------------------
# AiFeatureState schema tests
# ---------------------------------------------------------------------------

class TestAiFeatureState:
    def test_valid_live(self):
        s = AiFeatureState(name="forecast", enabled=True, source="live", latency_ms=123.4)
        assert s.source == "live"
        assert s.latency_ms == 123.4

    def test_valid_cache(self):
        s = AiFeatureState(name="scene", enabled=True, source="cache", latency_ms=0.0)
        assert s.source == "cache"

    def test_valid_fallback(self):
        s = AiFeatureState(name="zones", enabled=False, source="fallback", latency_ms=0.0)
        assert s.enabled is False

    def test_invalid_source_raises(self):
        with pytest.raises(Exception):
            AiFeatureState(name="x", enabled=True, source="invalid", latency_ms=0.0)

    def test_feature_disabled_response(self):
        r = FeatureDisabledResponse()
        assert r.enabled is False
        assert r.detail == "feature disabled"


# ---------------------------------------------------------------------------
# ai_runtime: ai_call tests
# ---------------------------------------------------------------------------

class TestAiCall:
    def test_live_call_success(self):
        state, result = ai_call(
            "forecast",
            fn=lambda: {"items": [1, 2, 3]},
            latency_budget_ms=5000,
        )
        assert state.source == "live"
        assert state.enabled is True
        assert state.name == "forecast"
        assert result == {"items": [1, 2, 3]}
        assert state.latency_ms >= 0

    def test_fallback_on_exception(self):
        def bad_fn():
            raise ConnectionError("no network")

        state, result = ai_call(
            "scene",
            fn=bad_fn,
            fallback={"weather": "unknown"},
            latency_budget_ms=2000,
        )
        assert state.source == "fallback"
        assert result == {"weather": "unknown"}

    def test_cache_loader_used_on_exception(self):
        def bad_fn():
            raise RuntimeError("timeout")

        state, result = ai_call(
            "zones",
            fn=bad_fn,
            cache_loader=lambda: {"zones": ["z1", "z2"]},
            fallback={"zones": []},
            latency_budget_ms=2000,
        )
        assert state.source == "cache"
        assert result == {"zones": ["z1", "z2"]}

    def test_budget_exceeded_uses_cache(self):
        # fn takes "long" — simulate by using a tiny budget
        def slow_fn():
            time.sleep(0.05)  # 50ms
            return {"live": True}

        state, result = ai_call(
            "verdict",
            fn=slow_fn,
            cache_loader=lambda: {"cached": True},
            latency_budget_ms=1,  # 1ms budget — will always exceed
        )
        assert state.source == "cache"
        assert result == {"cached": True}

    def test_budget_exceeded_no_cache_serves_live(self):
        # No cache available → serve live even if budget exceeded
        def slow_fn():
            time.sleep(0.05)
            return {"live": True}

        state, result = ai_call(
            "fatigue",
            fn=slow_fn,
            cache_loader=None,
            fallback=None,
            latency_budget_ms=1,
        )
        # No cache → live result returned
        assert result == {"live": True}
        assert state.source == "live"

    def test_latency_ms_populated(self):
        state, _ = ai_call(
            "copilot",
            fn=lambda: "response",
            latency_budget_ms=5000,
        )
        assert isinstance(state.latency_ms, float)
        assert state.latency_ms >= 0

    def test_default_budget_exists_for_known_features(self):
        for name in ("scene", "forecast", "zones", "fatigue", "copilot", "verdict"):
            assert name in DEFAULT_LATENCY_BUDGETS
            assert DEFAULT_LATENCY_BUDGETS[name] > 0

    def test_fallback_none_on_exception(self):
        state, result = ai_call(
            "scene",
            fn=lambda: (_ for _ in ()).throw(Exception("err")),
            fallback=None,
            latency_budget_ms=2000,
        )
        assert state.source == "fallback"
        assert result is None


# ---------------------------------------------------------------------------
# ai_runtime: disabled_state helper
# ---------------------------------------------------------------------------

class TestDisabledState:
    def test_disabled_state(self):
        s = disabled_state("forecast")
        assert s.name == "forecast"
        assert s.enabled is False
        assert s.source == "fallback"
        assert s.latency_ms == 0.0


# ---------------------------------------------------------------------------
# File-based cache (integration-light)
# ---------------------------------------------------------------------------

class TestFileCacheLoading:
    def test_missing_file_returns_none(self, tmp_path, monkeypatch):
        from api.core import ai_runtime as rt
        monkeypatch.setattr(rt, "_AI_DIR", tmp_path)
        result = rt._load_json_cache("nonexistent", ttl_s=3600)
        assert result is None

    def test_valid_file_within_ttl(self, tmp_path, monkeypatch):
        from api.core import ai_runtime as rt
        monkeypatch.setattr(rt, "_AI_DIR", tmp_path)
        cache_file = tmp_path / "myfeature.json"
        cache_file.write_text(json.dumps({"ok": True}), encoding="utf-8")
        result = rt._load_json_cache("myfeature", ttl_s=3600)
        assert result == {"ok": True}

    def test_expired_file_returns_none(self, tmp_path, monkeypatch):
        from api.core import ai_runtime as rt
        monkeypatch.setattr(rt, "_AI_DIR", tmp_path)
        cache_file = tmp_path / "oldfeature.json"
        cache_file.write_text(json.dumps({"old": True}), encoding="utf-8")
        # Set mtime to 2 hours ago
        old_time = time.time() - 7200
        os.utime(cache_file, (old_time, old_time))
        result = rt._load_json_cache("oldfeature", ttl_s=3600)
        assert result is None

    def test_corrupt_file_returns_none(self, tmp_path, monkeypatch):
        from api.core import ai_runtime as rt
        monkeypatch.setattr(rt, "_AI_DIR", tmp_path)
        cache_file = tmp_path / "bad.json"
        cache_file.write_text("{not valid json", encoding="utf-8")
        result = rt._load_json_cache("bad", ttl_s=3600)
        assert result is None
