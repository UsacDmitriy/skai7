# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "mcp[cli]>=1.2.0",
#   "httpx>=0.27",
#   "python-dotenv>=1.0",
# ]
# ///
"""
OpenRouter MCP bridge — ролевая оркестрация моделей (METHODOLOGY §3–§5).

stdio-сервер: проксирует запросы в OpenRouter chat/completions через httpx.
Оркестратор (Opus/Sonnet) делегирует подзадачи китайским моделям инструментами
ask_glm / ask_deepseek / ask_qwen / ask_kimi / ask_deepseek_flash.

Ключ: OPENROUTER_API_KEY из окружения или из tools/openrouter-mcp/.env.
Slug'и моделей переопределяются переменными окружения (см. MODELS ниже) —
сверяйте с https://openrouter.ai/models под свой аккаунт.
"""
from __future__ import annotations

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# .env рядом с сервером (gitignored).
load_dotenv(Path(__file__).with_name(".env"))

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Реестр моделей (METHODOLOGY §3). Slug переопределяется env-переменной —
# актуальность версий сверяется в одном месте, без правок кода.
MODELS: dict[str, str] = {
    "glm": os.getenv("OPENROUTER_GLM_MODEL", "z-ai/glm-5.2"),
    "deepseek": os.getenv("OPENROUTER_DEEPSEEK_MODEL", "deepseek/deepseek-v4-pro"),
    "deepseek_flash": os.getenv("OPENROUTER_DEEPSEEK_FLASH_MODEL", "deepseek/deepseek-v4-flash"),
    "qwen": os.getenv("OPENROUTER_QWEN_MODEL", "qwen/qwen3.7-max"),
    "kimi": os.getenv("OPENROUTER_KIMI_MODEL", "moonshotai/kimi-k2.7-code"),
}

mcp = FastMCP("openrouter-bridge")


def _api_key() -> str:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY не задан. Создайте tools/openrouter-mcp/.env с "
            "OPENROUTER_API_KEY=sk-or-v1-... (см. .env.example)."
        )
    return key


def _ask(model_slug: str, prompt: str, system: str | None = None) -> str:
    """Один запрос к OpenRouter chat/completions. Детерминизм: temperature=0."""
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {"model": model_slug, "messages": messages, "temperature": 0}
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
        # Опционально для рейтингов OpenRouter — не обязательны.
        "HTTP-Referer": "https://localhost/skai_7",
        "X-Title": "skai_7 openrouter-mcp",
    }
    try:
        with httpx.Client(timeout=120) as cli:
            r = cli.post(OPENROUTER_URL, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        return data["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as e:
        body = e.response.text[:500]
        return f"[openrouter error {e.response.status_code}] model={model_slug}: {body}"
    except Exception as e:  # noqa: BLE001 — мост никогда не падает молча
        return f"[openrouter bridge error] model={model_slug}: {e!r}"


@mcp.tool()
def configured_models() -> str:
    """Проверка ключа и активных slug'ов моделей (METHODOLOGY §3)."""
    has_key = bool(os.getenv("OPENROUTER_API_KEY", "").strip())
    lines = [f"OPENROUTER_API_KEY: {'OK' if has_key else 'НЕ ЗАДАН'}", "Модели:"]
    lines += [f"  ask_{name:<14} → {slug}" for name, slug in MODELS.items()]
    return "\n".join(lines)


@mcp.tool()
def ask(model: str, prompt: str, system: str | None = None) -> str:
    """Произвольный вызов: model — это либо ключ реестра (glm/deepseek/...),
    либо полный OpenRouter-slug (vendor/model)."""
    slug = MODELS.get(model, model)
    return _ask(slug, prompt, system)


@mcp.tool()
def ask_deepseek(prompt: str, system: str | None = None) -> str:
    """DeepSeek V4 Pro — атомарные backend-подзадачи, алгоритмы, паттерны (§4)."""
    return _ask(MODELS["deepseek"], prompt, system)


@mcp.tool()
def ask_deepseek_flash(prompt: str, system: str | None = None) -> str:
    """DeepSeek V4 Flash — самый дешёвый: черновики, первый драфт, мелкие фиксы (§4)."""
    return _ask(MODELS["deepseek_flash"], prompt, system)


@mcp.tool()
def ask_glm(prompt: str, system: str | None = None) -> str:
    """GLM 5.2 — фронт: компоненты, вёрстка, CSS, React/Vue (§4, приоритет на UI)."""
    return _ask(MODELS["glm"], prompt, system)


@mcp.tool()
def ask_qwen(prompt: str, system: str | None = None) -> str:
    """Qwen 3.7 Max — scaffold, CRUD, data-слой (§4)."""
    return _ask(MODELS["qwen"], prompt, system)


@mcp.tool()
def ask_kimi(prompt: str, system: str | None = None) -> str:
    """Kimi K2.7 Code — длинный контекст, чтение крупных логов/файлов (§4)."""
    return _ask(MODELS["kimi"], prompt, system)


if __name__ == "__main__":
    mcp.run()
