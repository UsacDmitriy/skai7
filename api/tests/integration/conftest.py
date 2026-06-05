"""Общие фикстуры интеграционных тестов API (T2, CONTRACT §3 / §7.4 / §7.5).

`fastapi.testclient.TestClient` против собранного приложения + живой DuckDB.
Каждая фикстура **чисто скипается**, если база не собрана (`make db`), чтобы
набор оставался переносимым в свежем worktree (тот же приём, что и
`api/tests/test_incidents_api.py`). Продуктовый код не правится — проверяется
только HTTP-контракт.
"""

from __future__ import annotations

import duckdb
import pytest
from fastapi.testclient import TestClient

from api.core.config import settings
from api.main import app
from api.services import actions_service


def _skip_if_no_db() -> None:
    if not settings.db_path.exists():
        pytest.skip(f"DuckDB не собран ({settings.db_path}); запусти `make db`.")


# ---------------------------------------------------------------------------
# Базовые фикстуры: HTTP-клиент и read-only коннект к БД.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def client() -> TestClient:
    """TestClient против live-приложения (триггерит lifespan)."""
    _skip_if_no_db()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def db() -> duckdb.DuckDBPyConnection:
    """Отдельный read-only коннект для резолва якорных id из данных."""
    _skip_if_no_db()
    conn = duckdb.connect(str(settings.db_path), read_only=True)
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def _reset_action_overrides():
    """Сброс рантайм-статусов инцидентов между тестами (POST /api/actions их меняет).

    Гарантирует независимость тестов фильтра по `status` от записи действий.
    """
    actions_service.reset_overrides()
    yield
    actions_service.reset_overrides()


# ---------------------------------------------------------------------------
# Якоря из живых данных — id/госномера для detail/alerts/trips/reb/reports.
# ---------------------------------------------------------------------------


@pytest.fixture
def incidents(client: TestClient) -> list[dict]:
    """Лента инцидентов; skip при пустой выдаче (нет данных для проверок)."""
    data = client.get("/api/incidents").json()
    if not data:
        pytest.skip("v_incidents пуст — нет данных для интеграционных проверок.")
    return data


@pytest.fixture
def first_incident(incidents: list[dict]) -> dict:
    """Первый инцидент ленты — якорь для detail/alerts/trips/video."""
    return incidents[0]


@pytest.fixture
def first_incident_id(first_incident: dict) -> str:
    return first_incident["id"]


@pytest.fixture
def driver_plate(db: duckdb.DuckDBPyConnection) -> str:
    """Госномер из `driver_reference` (§7.1) — для отчёта по водителю."""
    row = db.execute(
        'SELECT "vehicle_plate" FROM "driver_reference" LIMIT 1'
    ).fetchone()
    if not row:
        pytest.skip("driver_reference пуст.")
    return row[0]


@pytest.fixture
def vehicle_plate(db: duckdb.DuckDBPyConnection) -> str:
    """Госномер из `driver_trips` (1 ТС = N водителей) — для отчёта по ТС."""
    row = db.execute(
        'SELECT "vehicle_plate" FROM "driver_trips" LIMIT 1'
    ).fetchone()
    if not row:
        pytest.skip("driver_trips пуст.")
    return row[0]


@pytest.fixture
def reb_id(db: duckdb.DuckDBPyConnection) -> str:
    """`public_unit_id` (чистый UUID) для /api/reb/{id} — без спецсимволов в пути.

    `vehicle_id` навигации содержит пробелы и `/` (напр. `А 230 КУ/550 RUS`);
    `public_unit_id` резолвится тем же сервисом, но безопасен для URL.
    """
    row = db.execute(
        'SELECT "public_unit_id" FROM "navigation__track_periods" '
        'WHERE "public_unit_id" IS NOT NULL LIMIT 1'
    ).fetchone()
    if not row:
        pytest.skip("navigation__track_periods пуст.")
    return row[0]
