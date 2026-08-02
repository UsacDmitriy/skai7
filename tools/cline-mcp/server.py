# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "mcp[cli]>=1.2,<2",
#   "httpx>=0.27",
#   "python-dotenv>=1.0",
# ]
# ///
"""FastMCP bridge to the ClinePass chat-completions API.

Model slugs and task routes are loaded exclusively from the committed
``models.env`` registry. Secrets and connection overrides stay in the ignored
``.env`` file. The in-memory audit ledger belongs to the current MCP process;
reset it at the beginning of each user task and report it in the final answer.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP


BASE_DIR = Path(__file__).resolve().parent
MODELS_FILE = BASE_DIR / "models.env"
load_dotenv(BASE_DIR / ".env")

CLINE_URL = os.getenv(
    "CLINE_API_URL", "https://api.cline.bot/api/v1/chat/completions"
)
CLINE_TIMEOUT_SECONDS = float(os.getenv("CLINE_TIMEOUT_SECONDS", "600"))
_SAFE_MODEL_PREFIX = "cline-pass/"
_CANONICAL_ROUTES = {"simple", "simple-structured", "code", "synthesis", "review"}
_PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN(?: [A-Z0-9]+)* PRIVATE KEY-----.*?"
    r"-----END(?: [A-Z0-9]+)* PRIVATE KEY-----",
    re.IGNORECASE | re.DOTALL,
)
_BEARER_PATTERN = re.compile(
    r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+"
)
_CREDENTIAL_URI_PATTERN = re.compile(
    r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s:@]+:[^@\s/]+@"
)
_SECRET_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|authorization|client[_-]?secret|credential|password|secret|token)\b"
    r"(\s*[:=]\s*)([^\s,;]+)"
)


def load_model_registry(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Load and validate model aliases and task routes from an env-style file."""
    if not path.is_file():
        raise RuntimeError(f"ClinePass model registry not found: {path}")

    models: dict[str, str] = {}
    routes: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Invalid models.env line {line_number}: expected KEY=VALUE")
        key, value = (part.strip() for part in line.split("=", 1))
        value = value.strip("'\"")
        if key.startswith("CLINE_MODEL_"):
            alias = key.removeprefix("CLINE_MODEL_").lower().replace("_", "-")
            if not value.startswith(_SAFE_MODEL_PREFIX):
                raise ValueError(
                    f"Model {alias!r} must use the {_SAFE_MODEL_PREFIX!r} prefix"
                )
            models[alias] = value
        elif key.startswith("CLINE_ROUTE_"):
            route = key.removeprefix("CLINE_ROUTE_").lower().replace("_", "-")
            routes[route] = value.lower().replace("_", "-")
        else:
            raise ValueError(f"Unsupported models.env key on line {line_number}: {key}")

    if not models:
        raise ValueError("models.env does not define any CLINE_MODEL_* entries")
    if not routes:
        raise ValueError("models.env does not define any CLINE_ROUTE_* entries")
    missing_routes = sorted(_CANONICAL_ROUTES - set(routes))
    if missing_routes:
        raise ValueError(
            "models.env is missing required canonical routes: "
            + ", ".join(missing_routes)
        )
    unexpected_routes = sorted(set(routes) - _CANONICAL_ROUTES)
    if unexpected_routes:
        raise ValueError(
            "models.env defines noncanonical routes: "
            + ", ".join(unexpected_routes)
        )
    missing_aliases = sorted(set(routes.values()) - set(models))
    if missing_aliases:
        raise ValueError(
            "ClinePass routes reference unknown model aliases: "
            + ", ".join(missing_aliases)
        )
    return models, routes


MODELS, ROUTES = load_model_registry(MODELS_FILE)
mcp = FastMCP("cline-bridge")
_AUDIT_LEDGER: list[dict[str, Any]] = []


def _api_key() -> str:
    key = os.getenv("CLINE_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "CLINE_API_KEY is not set. Copy tools/cline-mcp/.env.example to "
            "tools/cline-mcp/.env and add the project-scoped key."
        )
    return key


def _redact(text: str) -> str:
    text = _PRIVATE_KEY_PATTERN.sub("[REDACTED PRIVATE KEY]", text)
    text = _CREDENTIAL_URI_PATTERN.sub(r"\1[REDACTED]@", text)
    text = _BEARER_PATTERN.sub(r"\1[REDACTED]", text)
    return _SECRET_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", text)


def _prompt_field(prompt: str, field: str, limit: int) -> str:
    prefix = f"{field}:"
    for line in prompt.splitlines():
        if line.upper().startswith(prefix):
            return _redact(line.split(":", 1)[1].strip())[:limit]
    return ""


def _purpose(prompt: str) -> str:
    return _prompt_field(prompt, "TASK", 240) or "unspecified"


def record_audit(
    *,
    model_alias: str,
    model_slug: str,
    prompt: str,
    system: str | None,
    max_tokens: int,
    status: str,
    finish_reason: str | None,
    usage: dict[str, Any] | None,
    response_chars: int,
) -> None:
    combined_instruction = prompt if system is None else f"SYSTEM: {system}\n{prompt}"
    task = _purpose(prompt)
    context_refs = _prompt_field(prompt, "CONTEXT_REFS", 700) or "not provided"
    _AUDIT_LEDGER.append(
        {
            "call": len(_AUDIT_LEDGER) + 1,
            "model": model_alias,
            "model_slug": model_slug,
            "purpose": task,
            "context_refs": context_refs,
            "instruction_preview": f"TASK: {task}\nCONTEXT_REFS: {context_refs}",
            "prompt_chars": len(combined_instruction),
            "prompt_sha256": hashlib.sha256(
                combined_instruction.encode("utf-8")
            ).hexdigest(),
            "max_tokens": max_tokens,
            "status": status,
            "finish_reason": finish_reason,
            "usage": usage,
            "response_chars": response_chars,
        }
    )


@mcp.tool()
def reset_audit() -> str:
    """Reset the process-local ClinePass ledger at the start of a user task."""
    _AUDIT_LEDGER.clear()
    return "ClinePass audit ledger reset"


@mcp.tool()
def audit_report() -> str:
    """Return the final-answer delegation report as stable JSON."""
    return json.dumps(
        {"total_calls": len(_AUDIT_LEDGER), "calls": _AUDIT_LEDGER},
        ensure_ascii=False,
        sort_keys=True,
    )


def _resolve_model(model: str) -> tuple[str, str]:
    if model in MODELS:
        return model, MODELS[model]
    raise ValueError(
        f"Unknown ClinePass model alias {model!r}; use configured_models() to inspect aliases"
    )


def _ask(
    model_alias: str,
    prompt: str,
    system: str | None = None,
    max_tokens: int = 4096,
) -> str:
    """Send one deterministic request and append its outcome to the audit ledger."""
    alias, model_slug = _resolve_model(model_alias)
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": model_slug,
        "messages": messages,
        "temperature": 0,
        "max_completion_tokens": max_tokens,
    }
    try:
        headers = {
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=CLINE_TIMEOUT_SECONDS) as client:
            response = client.post(CLINE_URL, json=payload, headers=headers)
            response.raise_for_status()
            envelope = response.json()
        body = envelope.get("data", envelope)
        choice = body["choices"][0]
        content = choice["message"]["content"]
        record_audit(
            model_alias=alias,
            model_slug=model_slug,
            prompt=prompt,
            system=system,
            max_tokens=max_tokens,
            status="ok",
            finish_reason=choice.get("finish_reason"),
            usage=body.get("usage"),
            response_chars=len(content),
        )
        return content
    except httpx.HTTPStatusError as error:
        body = error.response.text[:500]
        record_audit(
            model_alias=alias,
            model_slug=model_slug,
            prompt=prompt,
            system=system,
            max_tokens=max_tokens,
            status=f"http_error_{error.response.status_code}",
            finish_reason=None,
            usage=None,
            response_chars=0,
        )
        return f"[cline error {error.response.status_code}] model={model_slug}: {body}"
    except Exception as error:  # noqa: BLE001 - explicit error is an MCP result
        record_audit(
            model_alias=alias,
            model_slug=model_slug,
            prompt=prompt,
            system=system,
            max_tokens=max_tokens,
            status="bridge_error",
            finish_reason=None,
            usage=None,
            response_chars=0,
        )
        return f"[cline bridge error] model={model_slug}: {error!r}"


@mcp.tool()
def configured_models() -> str:
    """Show the loaded model registry, task routes, and key readiness."""
    lines = [
        f"CLINE_API_KEY: {'OK' if os.getenv('CLINE_API_KEY', '').strip() else 'NOT SET'}",
        f"registry: {MODELS_FILE}",
        "models:",
    ]
    lines.extend(f"  {alias:<18} -> {slug}" for alias, slug in MODELS.items())
    lines.append("routes:")
    lines.extend(f"  {route:<18} -> {alias}" for route, alias in ROUTES.items())
    return "\n".join(lines)


@mcp.tool()
def ask(
    model: str,
    prompt: str,
    system: str | None = None,
    max_tokens: int = 4096,
) -> str:
    """Call a model alias from the committed models.env registry."""
    return _ask(model, prompt, system, max_tokens)


@mcp.tool()
def ask_route(
    route: str,
    prompt: str,
    system: str | None = None,
    max_tokens: int = 4096,
) -> str:
    """Call the model assigned to a task route in models.env."""
    if route not in ROUTES:
        raise ValueError(f"Unknown ClinePass route {route!r}")
    return _ask(ROUTES[route], prompt, system, max_tokens)


@mcp.tool()
def ask_glm(prompt: str, system: str | None = None, max_tokens: int = 4096) -> str:
    """Call the configured GLM model."""
    return _ask("glm", prompt, system, max_tokens)


@mcp.tool()
def ask_kimi_k3(
    prompt: str, system: str | None = None, max_tokens: int = 4096
) -> str:
    """Call the configured Kimi K3 model."""
    return _ask("kimi-k3", prompt, system, max_tokens)


@mcp.tool()
def ask_kimi_code(
    prompt: str, system: str | None = None, max_tokens: int = 4096
) -> str:
    """Call the configured Kimi coding model."""
    return _ask("kimi-code", prompt, system, max_tokens)


@mcp.tool()
def ask_kimi(prompt: str, system: str | None = None, max_tokens: int = 4096) -> str:
    """Call the configured general Kimi model."""
    return _ask("kimi", prompt, system, max_tokens)


@mcp.tool()
def ask_deepseek(
    prompt: str, system: str | None = None, max_tokens: int = 4096
) -> str:
    """Call the configured DeepSeek synthesis model."""
    return _ask("deepseek-pro", prompt, system, max_tokens)


@mcp.tool()
def ask_deepseek_flash(
    prompt: str, system: str | None = None, max_tokens: int = 4096
) -> str:
    """Call the configured DeepSeek flash model."""
    return _ask("deepseek-flash", prompt, system, max_tokens)


@mcp.tool()
def ask_minimax(
    prompt: str, system: str | None = None, max_tokens: int = 4096
) -> str:
    """Call the configured MiniMax model."""
    return _ask("minimax", prompt, system, max_tokens)


@mcp.tool()
def ask_mimo(prompt: str, system: str | None = None, max_tokens: int = 4096) -> str:
    """Call the configured MiMo model."""
    return _ask("mimo", prompt, system, max_tokens)


@mcp.tool()
def ask_mimo_pro(
    prompt: str, system: str | None = None, max_tokens: int = 4096
) -> str:
    """Call the configured MiMo Pro model."""
    return _ask("mimo-pro", prompt, system, max_tokens)


@mcp.tool()
def ask_qwen_max(
    prompt: str, system: str | None = None, max_tokens: int = 4096
) -> str:
    """Call the configured Qwen Max model."""
    return _ask("qwen-max", prompt, system, max_tokens)


@mcp.tool()
def ask_qwen(prompt: str, system: str | None = None, max_tokens: int = 4096) -> str:
    """Call the configured Qwen model."""
    return _ask("qwen", prompt, system, max_tokens)


if __name__ == "__main__":
    mcp.run()
