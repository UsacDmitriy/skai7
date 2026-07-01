# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "mcp[cli]>=1.2.0",
#   "httpx>=0.27",
#   "python-dotenv>=1.0",
# ]
# ///
"""
Cline API MCP bridge — ролевая оркестрация моделей (METHODOLOGY §3–§5).

stdio-сервер: проксирует запросы в Cline API chat/completions через httpx.
Эндпоинт OpenAI-совместимый (ответ обёрнут в {"data": {...}}). Реестр моделей —
подписка clinepass. Оркестратор (Opus/Sonnet) делегирует подзадачи по ролям.

Ключ: CLINE_API_KEY из окружения или из tools/cline-mcp/.env (gitignored).
Получить ключ: https://app.cline.bot → Settings → API Keys.
Slug'и переопределяются переменными окружения (см. MODELS ниже) — сверяйте в
дашборде app.cline.bot.
"""
from __future__ import annotations

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# .env рядом с сервером (gitignored).
load_dotenv(Path(__file__).with_name(".env"))

CLINE_URL = "https://api.cline.bot/api/v1/chat/completions"

# Реестр моделей clinepass (METHODOLOGY §3). Роль → slug. Slug переопределяется
# env-переменной — актуальность версий сверяется в одном месте, без правок кода.
#
# ВАЖНО: префикс "cline-pass/" роутит запрос через подписку ClinePass (flat
# $9.99/мес). Голый "vendor/model" пошёл бы через usage-billing = кредиты.
# Поэтому все дефолты — с префиксом cline-pass/.
MODELS: dict[str, str] = {
    "glm": os.getenv("CLINE_GLM_MODEL", "cline-pass/glm-5.2"),
    "kimi_code": os.getenv("CLINE_KIMI_CODE_MODEL", "cline-pass/kimi-k2.7-code"),
    "kimi": os.getenv("CLINE_KIMI_MODEL", "cline-pass/kimi-k2.6"),
    "deepseek": os.getenv("CLINE_DEEPSEEK_MODEL", "cline-pass/deepseek-v4-pro"),
    "deepseek_flash": os.getenv("CLINE_DEEPSEEK_FLASH_MODEL", "cline-pass/deepseek-v4-flash"),
    "minimax": os.getenv("CLINE_MINIMAX_MODEL", "cline-pass/minimax-m3"),
    "mimo": os.getenv("CLINE_MIMO_MODEL", "cline-pass/mimo-v2.5"),
    "mimo_pro": os.getenv("CLINE_MIMO_PRO_MODEL", "cline-pass/mimo-v2.5-pro"),
    "qwen_max": os.getenv("CLINE_QWEN_MAX_MODEL", "cline-pass/qwen3.7-max"),
    "qwen": os.getenv("CLINE_QWEN_MODEL", "cline-pass/qwen3.7-plus"),
}

mcp = FastMCP("cline-bridge")


def _api_key() -> str:
    key = os.getenv("CLINE_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "CLINE_API_KEY не задан. Создайте tools/cline-mcp/.env с "
            "CLINE_API_KEY=... (см. .env.example, ключ: app.cline.bot → API Keys)."
        )
    return key


def _ask(model_slug: str, prompt: str, system: str | None = None) -> str:
    """Один запрос к Cline API chat/completions. Детерминизм: temperature=0."""
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {"model": model_slug, "messages": messages, "temperature": 0}
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=120) as cli:
            r = cli.post(CLINE_URL, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        # Cline оборачивает OpenAI-ответ в {"data": {...}}; обычный OpenAI — нет.
        body = data.get("data", data)
        return body["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as e:
        body = e.response.text[:500]
        return f"[cline error {e.response.status_code}] model={model_slug}: {body}"
    except Exception as e:  # noqa: BLE001 — мост никогда не падает молча
        return f"[cline bridge error] model={model_slug}: {e!r}"


@mcp.tool()
def configured_models() -> str:
    """Проверка ключа и активных slug'ов моделей (METHODOLOGY §3)."""
    has_key = bool(os.getenv("CLINE_API_KEY", "").strip())
    lines = [f"CLINE_API_KEY: {'OK' if has_key else 'НЕ ЗАДАН'}", "Модели:"]
    lines += [f"  ask_{name:<15} → {slug}" for name, slug in MODELS.items()]
    return "\n".join(lines)


@mcp.tool()
def ask(model: str, prompt: str, system: str | None = None) -> str:
    """Произвольный вызов: model — ключ реестра (glm/kimi/deepseek/...) либо
    полный Cline-slug (vendor/model)."""
    slug = MODELS.get(model, model)
    return _ask(slug, prompt, system)


@mcp.tool()
def ask_glm(prompt: str, system: str | None = None) -> str:
    """GLM 5.2 — сложное планирование, архитектурный анализ, многошаговые задачи."""
    return _ask(MODELS["glm"], prompt, system)


@mcp.tool()
def ask_kimi_code(prompt: str, system: str | None = None) -> str:
    """Kimi K2.7 Code — кодинг, правки по проекту, агентная работа в репозитории."""
    return _ask(MODELS["kimi_code"], prompt, system)


@mcp.tool()
def ask_kimi(prompt: str, system: str | None = None) -> str:
    """Kimi K2.6 — длинные агентные workflows, когда нужно много итераций."""
    return _ask(MODELS["kimi"], prompt, system)


@mcp.tool()
def ask_deepseek(prompt: str, system: str | None = None) -> str:
    """DeepSeek V4 Pro — большие изменения в кодовой базе."""
    return _ask(MODELS["deepseek"], prompt, system)


@mcp.tool()
def ask_deepseek_flash(prompt: str, system: str | None = None) -> str:
    """DeepSeek V4 Flash — быстрые мелкие правки, проверка гипотез, простые скрипты."""
    return _ask(MODELS["deepseek_flash"], prompt, system)


@mcp.tool()
def ask_minimax(prompt: str, system: str | None = None) -> str:
    """MiniMax M3 — универсальная модель «по умолчанию»."""
    return _ask(MODELS["minimax"], prompt, system)


@mcp.tool()
def ask_mimo(prompt: str, system: str | None = None) -> str:
    """MiMo V2.5 — экономные правки, небольшие изменения."""
    return _ask(MODELS["mimo"], prompt, system)


@mcp.tool()
def ask_mimo_pro(prompt: str, system: str | None = None) -> str:
    """MiMo V2.5 Pro — более тяжёлая работа у MiMo."""
    return _ask(MODELS["mimo_pro"], prompt, system)


@mcp.tool()
def ask_qwen_max(prompt: str, system: str | None = None) -> str:
    """Qwen3.7 Max — нагрузочные/объёмные задачи, генерация большого кода."""
    return _ask(MODELS["qwen_max"], prompt, system)


@mcp.tool()
def ask_qwen(prompt: str, system: str | None = None) -> str:
    """Qwen3.7 Plus — баланс цена/качество/скорость."""
    return _ask(MODELS["qwen"], prompt, system)


if __name__ == "__main__":
    mcp.run()
