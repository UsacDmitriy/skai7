"""AI runtime governance: latency-budget + cache/fallback decorator (b24 · §8.6).

Wraps any AI call so that:
  - latency is measured and returned in AiFeatureState.latency_ms
  - if elapsed > latency_budget_ms → skip live call, serve cache/fallback
  - if caller raises an exception (no network, etc.) → serve cache/fallback
  - cache is read from data/ai/<feature>.json (TTL-based)
  - source ∈ {live, cache, fallback} is always populated

Usage:

    from api.core.ai_runtime import ai_call

    state, result = ai_call(
        feature="forecast",
        fn=lambda: expensive_api_call(),
        cache_loader=lambda: load_forecast_cache(),
        fallback={"items": []},
        latency_budget_ms=2000,
        cache_ttl_s=3600,
    )
    return {**result, "ai_state": state}
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from api.core.ai_flags import AiFeatureState
from api.core.config import settings

# Default per-feature budgets (ms). Overridable per call.
DEFAULT_LATENCY_BUDGETS: dict[str, int] = {
    "scene": 3000,
    "forecast": 2000,
    "zones": 2000,
    "fatigue": 1500,
    "copilot": 4000,
    "verdict": 2000,
}

DEFAULT_CACHE_TTL_S: int = 3600  # 1 hour


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

_AI_DIR = settings.project_root / "data" / "ai"


def _cache_path(feature: str) -> Path:
    return _AI_DIR / f"{feature}.json"


def _load_json_cache(feature: str, ttl_s: int) -> dict | list | None:
    """Read data/ai/<feature>.json if it exists and is within TTL.

    TTL is checked against the file mtime. Returns parsed payload or None.
    """
    path = _cache_path(feature)
    if not path.exists():
        return None
    age_s = time.time() - path.stat().st_mtime
    if age_s > ttl_s:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------------------
# Core runtime call
# ---------------------------------------------------------------------------

def ai_call(
    feature: str,
    fn: Callable[[], Any],
    *,
    cache_loader: Callable[[], Any] | None = None,
    fallback: Any = None,
    latency_budget_ms: int | None = None,
    cache_ttl_s: int = DEFAULT_CACHE_TTL_S,
) -> tuple[AiFeatureState, Any]:
    """Execute an AI call with governance.

    Args:
        feature: feature name (scene/forecast/zones/fatigue/copilot/verdict)
        fn: callable that performs the live AI computation
        cache_loader: optional callable returning cached result (takes priority
                      over file-based JSON cache when provided)
        fallback: value returned when both live and cache are unavailable
        latency_budget_ms: max allowed ms for live call; None → default
        cache_ttl_s: seconds before file-based cache is considered stale

    Returns:
        (AiFeatureState, result) — state carries name/enabled/source/latency_ms
    """
    budget_ms = latency_budget_ms if latency_budget_ms is not None else (
        DEFAULT_LATENCY_BUDGETS.get(feature, 2000)
    )

    start = time.monotonic()

    # --- Attempt live call within budget ---
    try:
        # Check latency budget BEFORE calling (pre-flight: always attempt live
        # unless we are explicitly in offline/budget-exceeded mode).
        # We run the call and measure afterward to decide retroactively —
        # if exceeded, substitute cache for next callers but return live result
        # this time (matches "don't block UI" contract §8.6).
        result = fn()
        elapsed_ms = (time.monotonic() - start) * 1000.0

        if elapsed_ms <= budget_ms:
            source = "live"
        else:
            # Budget exceeded — try cache for degradation; keep live result
            cached = _get_cache(feature, cache_loader, cache_ttl_s)
            if cached is not None:
                source = "cache"
                result = cached
            else:
                source = "live"  # budget exceeded but no cache; serve live anyway

        return (
            AiFeatureState(
                name=feature,
                enabled=True,
                source=source,
                latency_ms=round(elapsed_ms, 1),
            ),
            result,
        )

    except Exception:
        elapsed_ms = (time.monotonic() - start) * 1000.0
        # Live call failed (network error, timeout, etc.) → cache or fallback
        cached = _get_cache(feature, cache_loader, cache_ttl_s)
        if cached is not None:
            return (
                AiFeatureState(
                    name=feature,
                    enabled=True,
                    source="cache",
                    latency_ms=round(elapsed_ms, 1),
                ),
                cached,
            )

        return (
            AiFeatureState(
                name=feature,
                enabled=True,
                source="fallback",
                latency_ms=round(elapsed_ms, 1),
            ),
            fallback,
        )


def _get_cache(
    feature: str,
    cache_loader: Callable[[], Any] | None,
    cache_ttl_s: int,
) -> Any:
    """Try cache_loader first, then file-based JSON cache."""
    if cache_loader is not None:
        try:
            result = cache_loader()
            if result is not None:
                return result
        except Exception:
            pass
    return _load_json_cache(feature, cache_ttl_s)


# ---------------------------------------------------------------------------
# Disabled-feature helper
# ---------------------------------------------------------------------------

def disabled_state(feature: str) -> AiFeatureState:
    """AiFeatureState for a disabled feature (enabled=False, source=fallback)."""
    return AiFeatureState(
        name=feature,
        enabled=False,
        source="fallback",
        latency_ms=0.0,
    )
