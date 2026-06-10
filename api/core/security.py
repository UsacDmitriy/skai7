"""Security baseline middleware (b26 · §8.9) — auth / throttle / audit.

Демо-уровневый каркас безопасности, который **не ломает** текущие эндпоинты:

1. **Auth** (bearer / API-key scaffold) — активен ТОЛЬКО при `settings.security_enabled`
   (env `SKAI_SECURITY_ENABLED=true` на старте процесса). При дефолтном `False` — полный
   no-op: ветка 401 недостижима, ни один эндпоинт/тест P0–P2 не меняет поведение.
   Значение флага читается на КАЖДОМ запросе (не кэшируется на импорте модуля).

2. **Throttle** — лимит частоты запросов + размер STT-файла на тяжёлых эндпоинтах
   (`/api/reports/transcribe`, `/api/copilot/chat`). Превышение → 429 с понятным телом.
   Работает независимо от auth-флага (защита ресурсов на демо). Лимиты щадящие, чтобы
   не задеть существующие тесты/регресс.

3. **Audit** — мутации (`POST/PUT/PATCH/DELETE` на `/api/actions`, `/api/copilot/chat`,
   `/api/tickets`) дописываются в `output/audit.csv` через `api.core.audit` (best-effort).

Регистрируется в `api/main.py` аддитивно (`app.add_middleware(SecurityMiddleware)`),
не трогая роутеры и контракты ответов.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from api.core import audit
from api.core.config import settings


# ---------------------------------------------------------------------------
# Конфигурация (env-override, но с щадящими дефолтами для демо).
# ---------------------------------------------------------------------------

def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


# Открытые пути — auth их не трогает даже при security_enabled.
_OPEN_PATHS = frozenset({"/", "/api/health", "/docs", "/redoc", "/openapi.json"})

# Тяжёлые эндпоинты под throttle: суффикс пути → (макс. запросов, окно сек).
_HEAVY = {
    "/api/reports/transcribe": (
        _int_env("SKAI_THROTTLE_STT_MAX", 20),
        _int_env("SKAI_THROTTLE_WINDOW_SEC", 60),
    ),
    "/api/copilot/chat": (
        _int_env("SKAI_THROTTLE_COPILOT_MAX", 30),
        _int_env("SKAI_THROTTLE_WINDOW_SEC", 60),
    ),
}

# Предельный размер STT-загрузки (Content-Length), байт. 25 МБ по умолчанию.
_MAX_STT_BYTES = _int_env("SKAI_MAX_STT_BYTES", 25 * 1024 * 1024)

# Пути-мутации под audit: точное совпадение пути запроса.
_AUDITED = {
    "/api/actions": "actions",
    "/api/copilot/chat": "copilot",
    "/api/tickets": "tickets",
}
_MUTATION_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


# ---------------------------------------------------------------------------
# Скользящее окно частоты запросов (in-memory, per process).
# ---------------------------------------------------------------------------

# key = (client_ip, path) → монотонные таймстемпы последних запросов.
_hits: dict[tuple[str, str], Deque[float]] = defaultdict(deque)


def _rate_limited(client: str, path: str, limit: int, window: int) -> bool:
    """True, если частота для (client, path) превысила limit за window секунд."""
    now = time.monotonic()
    bucket = _hits[(client, path)]
    cutoff = now - window
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= limit:
        return True
    bucket.append(now)
    return False


def reset_throttle() -> None:
    """Сброс счётчиков (для тестов/перезапуска)."""
    _hits.clear()


def _has_token(request: Request) -> bool:
    """Scaffold-проверка: непустой Bearer-токен или X-API-Key (наличие)."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer ") and auth[7:].strip():
        return True
    return bool(request.headers.get("x-api-key", "").strip())


def _client(request: Request) -> str:
    return request.client.host if request.client else "anonymous"


def _path(request: Request) -> str:
    """Нормализованный путь без хвостового слэша (кроме корня)."""
    p = request.url.path
    return p[:-1] if len(p) > 1 and p.endswith("/") else p


# ---------------------------------------------------------------------------
# Middleware.
# ---------------------------------------------------------------------------

class SecurityMiddleware(BaseHTTPMiddleware):
    """Auth (gated флагом) + throttle (всегда) + audit мутаций (best-effort)."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = _path(request)
        method = request.method.upper()

        # 1) Throttle тяжёлых эндпоинтов — до любой работы.
        if path in _HEAVY and method in _MUTATION_METHODS:
            limit, window = _HEAVY[path]
            # Размер STT-файла — отбой до чтения тела (по Content-Length).
            if path == "/api/reports/transcribe":
                clen = request.headers.get("content-length")
                if clen and clen.isdigit() and int(clen) > _MAX_STT_BYTES:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": "payload too large",
                            "limit_bytes": _MAX_STT_BYTES,
                        },
                    )
            if _rate_limited(_client(request), path, limit, window):
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "rate limit exceeded",
                        "limit": limit,
                        "window_sec": window,
                    },
                    headers={"Retry-After": str(window)},
                )

        # 2) Auth — no-op при security_enabled=False (флаг читается на каждом запросе).
        if settings.security_enabled and path not in _OPEN_PATHS:
            if not _has_token(request):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "missing or invalid credentials"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # 3) Стампим время приёма запроса (событие), затем выполняем эндпоинт.
        ts = audit.now_iso()
        response = await call_next(request)

        # 4) Audit мутаций — после ответа, best-effort, не влияет на контракт.
        feature = _AUDITED.get(path)
        if feature and method in _MUTATION_METHODS:
            audit.record(
                event="mutation",
                feature=feature,
                tool=f"{method} {path}",
                source="api",
                args={"path": path, "status": response.status_code},
                ts=ts,
            )

        return response
