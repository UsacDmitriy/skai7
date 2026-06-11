"""Unit-покрытие security baseline (b26) — §8.9, идея #20.

`SecurityMiddleware` — демо-уровневый каркас, который НЕ ломает текущие эндпоинты:
  * auth — активен только при `settings.security_enabled` (флаг читается на запрос);
  * throttle — лимит частоты + размер STT-файла на тяжёлых эндпоинтах (всегда);
  * audit — мутации дописываются строкой в `output/audit.csv` (best-effort, детерм. схема).

Проверяем (Check tu-security): флаг off → passthrough; флаг on → 401/проход;
audit-строка пишется; throttle → 429; размер → 413. Без сети: `TestClient` —
in-process ASGI, реальных сокетов нет. Middleware монтируется на минимальном app
с путями-двойниками реальных (`/api/incidents`, `/api/actions`, `/api/copilot/chat`,
`/api/reports/transcribe`).
"""

from __future__ import annotations

import csv

import pytest

from api.core import audit, security
from api.core.config import settings
from api.core.security import SecurityMiddleware


@pytest.fixture(autouse=True)
def _reset_throttle() -> None:
    """Чистый счётчик частоты перед каждым тестом (in-memory, per process)."""
    security.reset_throttle()


@pytest.fixture
def app():
    """Минимальный FastAPI с путями-двойниками под middleware (без доменной логики)."""
    from fastapi import FastAPI

    application = FastAPI()
    application.add_middleware(SecurityMiddleware)

    @application.get("/")
    def root() -> dict:
        return {"ok": True}

    @application.get("/api/incidents/ping")
    def protected() -> dict:
        return {"ok": True}

    @application.post("/api/actions")
    def actions() -> dict:
        return {"recorded": True}

    @application.post("/api/copilot/chat")
    def copilot() -> dict:
        return {"answer": "ok"}

    @application.post("/api/reports/transcribe")
    def transcribe() -> dict:
        return {"text": "ok"}

    return application


@pytest.fixture
def http(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        yield client


# ---------------------------------------------------------------------------
# Обратная совместимость: флаг OFF (демо/dev) → passthrough.
# ---------------------------------------------------------------------------


def test_flag_off_passthrough(http, monkeypatch) -> None:
    """`SECURITY_ENABLED=false` → защищённый эндпоинт доступен без токена (регресс)."""
    monkeypatch.setattr(settings, "security_enabled", False)

    resp = http.get("/api/incidents/ping")

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_flag_off_mutation_passthrough(http, monkeypatch) -> None:
    """Флаг off → мутации проходят как раньше (не ломаем P0–P2 Волны 4)."""
    monkeypatch.setattr(settings, "security_enabled", False)

    assert http.post("/api/actions").status_code == 200


# ---------------------------------------------------------------------------
# Auth: флаг ON → 401 без токена, проход с токеном; открытые пути всегда открыты.
# ---------------------------------------------------------------------------


def test_flag_on_no_token_401(http, monkeypatch) -> None:
    """`SECURITY_ENABLED=true` + нет токена → 401 на защищённом пути."""
    monkeypatch.setattr(settings, "security_enabled", True)

    resp = http.get("/api/incidents/ping")

    assert resp.status_code == 401


def test_flag_on_bearer_token_passes(http, monkeypatch) -> None:
    """Флаг on + валидный Bearer-токен → проход (200)."""
    monkeypatch.setattr(settings, "security_enabled", True)

    resp = http.get(
        "/api/incidents/ping", headers={"Authorization": "Bearer demo-token"}
    )

    assert resp.status_code == 200


def test_flag_on_api_key_passes(http, monkeypatch) -> None:
    """Флаг on + X-API-Key → проход (scaffold принимает наличие ключа)."""
    monkeypatch.setattr(settings, "security_enabled", True)

    resp = http.get("/api/incidents/ping", headers={"X-API-Key": "k-123"})

    assert resp.status_code == 200


def test_flag_on_open_path_no_token(http, monkeypatch) -> None:
    """Открытый путь (`/`) доступен без токена даже при включённом флаге."""
    monkeypatch.setattr(settings, "security_enabled", True)

    assert http.get("/").status_code == 200


def test_flag_on_empty_bearer_rejected(http, monkeypatch) -> None:
    """Пустой Bearer не считается токеном → 401 (scaffold проверяет непустоту)."""
    monkeypatch.setattr(settings, "security_enabled", True)

    resp = http.get("/api/incidents/ping", headers={"Authorization": "Bearer "})

    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Audit-trail: мутации пишут детерминированную строку в output/audit.csv.
# ---------------------------------------------------------------------------


def test_audit_row_written_for_mutation(http, monkeypatch, tmp_path) -> None:
    """POST `/api/actions` дописывает строку аудита с фиксированной схемой."""
    monkeypatch.setattr(settings, "security_enabled", False)
    monkeypatch.setattr(settings, "output_dir", tmp_path)

    assert http.post("/api/actions").status_code == 200

    audit_csv = tmp_path / "audit.csv"
    assert audit_csv.exists()

    with audit_csv.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))

    # Детерминированная схема (без Date.now в логике — порядок колонок фиксирован).
    assert rows[0] == audit.AUDIT_HEADER
    data = [r for r in rows[1:] if r]
    assert any(r[1] == "mutation" and r[2] == "actions" for r in data)


def test_audit_copilot_mutation_logged(http, monkeypatch, tmp_path) -> None:
    """POST `/api/copilot/chat` тоже аудируется (feature=copilot)."""
    monkeypatch.setattr(settings, "security_enabled", False)
    monkeypatch.setattr(settings, "output_dir", tmp_path)

    assert http.post("/api/copilot/chat").status_code == 200

    with (tmp_path / "audit.csv").open(newline="", encoding="utf-8") as fh:
        data = [r for r in csv.reader(fh) if r][1:]
    assert any(r[2] == "copilot" for r in data)


def test_get_request_not_audited(http, monkeypatch, tmp_path) -> None:
    """GET-чтения не пишут аудит (логируем только мутации)."""
    monkeypatch.setattr(settings, "security_enabled", False)
    monkeypatch.setattr(settings, "output_dir", tmp_path)

    http.get("/api/incidents/ping")

    assert not (tmp_path / "audit.csv").exists()


# ---------------------------------------------------------------------------
# Throttle / rate-limit и размер STT — защита тяжёлых эндпоинтов.
# ---------------------------------------------------------------------------


def test_throttle_returns_429_over_limit(http, monkeypatch) -> None:
    """Превышение лимита частоты на `/api/copilot/chat` → 429."""
    monkeypatch.setattr(settings, "security_enabled", False)
    monkeypatch.setattr(security, "_HEAVY", {"/api/copilot/chat": (2, 60)})

    assert http.post("/api/copilot/chat").status_code == 200
    assert http.post("/api/copilot/chat").status_code == 200
    blocked = http.post("/api/copilot/chat")

    assert blocked.status_code == 429
    assert blocked.headers.get("Retry-After") == "60"


def test_throttle_independent_of_auth_flag(http, monkeypatch) -> None:
    """Throttle работает и при выключенном auth-флаге (защита ресурсов на демо)."""
    monkeypatch.setattr(settings, "security_enabled", False)
    monkeypatch.setattr(security, "_HEAVY", {"/api/copilot/chat": (1, 60)})

    assert http.post("/api/copilot/chat").status_code == 200
    assert http.post("/api/copilot/chat").status_code == 429


def test_stt_size_limit_returns_413(http, monkeypatch) -> None:
    """STT-загрузка больше лимита (по Content-Length) → 413, до чтения тела."""
    monkeypatch.setattr(settings, "security_enabled", False)
    monkeypatch.setattr(security, "_MAX_STT_BYTES", 100)

    resp = http.post("/api/reports/transcribe", content=b"x" * 200)

    assert resp.status_code == 413


def test_stt_within_limit_passes(http, monkeypatch) -> None:
    """Небольшая STT-загрузка проходит (порог не задевает легальный запрос)."""
    monkeypatch.setattr(settings, "security_enabled", False)
    monkeypatch.setattr(security, "_MAX_STT_BYTES", 1000)

    resp = http.post("/api/reports/transcribe", content=b"x" * 10)

    assert resp.status_code == 200


def test_non_heavy_path_not_throttled(http, monkeypatch) -> None:
    """Лёгкий эндпоинт (`/api/actions`) не попадает под throttle при потоке запросов."""
    monkeypatch.setattr(settings, "security_enabled", False)
    monkeypatch.setattr(security, "_HEAVY", {"/api/copilot/chat": (1, 60)})

    for _ in range(5):
        assert http.post("/api/actions").status_code == 200
