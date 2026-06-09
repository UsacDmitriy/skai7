"""AI feature-flags + AiFeatureState schema (b24 · §8.6).

Feature flags control each AI capability independently. A disabled feature
returns HTTP 200 with {"enabled": false} — no 5xx. Source of truth: env vars
with SKAI_AI_ prefix; all default to True (enabled).

Flags: scene | forecast | zones | fatigue | copilot | verdict
"""
from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Schema (§8.6)
# ---------------------------------------------------------------------------

class AiFeatureState(BaseModel):
    """Metadata injected into AI endpoint responses (§8.6)."""

    name: str
    enabled: bool
    source: Literal["live", "cache", "fallback"]
    latency_ms: float


class FeatureDisabledResponse(BaseModel):
    """Standard response when a feature flag is off."""

    enabled: bool = False
    detail: str = "feature disabled"


# ---------------------------------------------------------------------------
# Flag resolution (env-driven, deterministic)
# ---------------------------------------------------------------------------

_FLAG_NAMES = ("scene", "forecast", "zones", "fatigue", "copilot", "verdict")


def _flag_env(name: str) -> bool:
    """Read SKAI_AI_<NAME> env var; absent/non-'0'/'false' → True (enabled)."""
    val = os.environ.get(f"SKAI_AI_{name.upper()}", "").strip().lower()
    return val not in ("0", "false", "off", "no")


class AiFlags:
    """Feature-flag registry. Read once at import; re-read via reload()."""

    def __init__(self) -> None:
        self._flags: dict[str, bool] = {}
        self.reload()

    def reload(self) -> None:
        """Re-read all flags from env (useful in tests)."""
        self._flags = {name: _flag_env(name) for name in _FLAG_NAMES}

    def is_enabled(self, feature: str) -> bool:
        """Return True if the feature flag is on.

        Unknown feature names default to True so unknown callers aren't blocked.
        """
        return self._flags.get(feature, True)

    def as_dict(self) -> dict[str, bool]:
        return dict(self._flags)


# Module-level singleton
flags = AiFlags()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def require_feature(feature: str) -> bool:
    """Return True if enabled; callers raise/return early on False."""
    return flags.is_enabled(feature)
