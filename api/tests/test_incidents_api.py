"""Tests for the incidents API at the router level (CONTRACT §3.2).

Uses FastAPI `TestClient` against the assembled app + live DuckDB. Each test
skips cleanly when the DB is not built (`make db`).

Covers x3 smoke expectations: list / detail / 404 / 501 stub / video happy-path.
"""

from __future__ import annotations

import duckdb
import pytest
from fastapi.testclient import TestClient

from api.core.config import settings
from api.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client() -> TestClient:
    if not settings.db_path.exists():
        pytest.skip(f"DuckDB не собран ({settings.db_path}); запусти `make db`.")
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def db() -> duckdb.DuckDBPyConnection:
    if not settings.db_path.exists():
        pytest.skip(f"DuckDB не собран ({settings.db_path}); запусти `make db`.")
    conn = duckdb.connect(str(settings.db_path), read_only=True)
    yield conn
    conn.close()


def _incident_with_downloaded_video(db: duckdb.DuckDBPyConnection) -> tuple[str, int]:
    """(alarm_id, channel) для алярма, чей mp4 РЕАЛЬНО есть на диске, иначе skip.

    Медиа (`datasets/media/`) gitignored → в свежем worktree файлов нет: проверяем
    наличие через продакшн-хелпер `_resolve_media_path`, чтобы тест был переносим
    (skip без медиа, а не падение).
    """
    from api.routers.incidents import _resolve_media_path

    rows = db.execute(
        'SELECT vf."alarm_id", vf."channel", vf."media_relative_path" '
        'FROM "video_events__video_files" vf '
        'JOIN v_incidents i ON i.id = vf."alarm_id" '
        "WHERE vf.\"media_relative_path\" IS NOT NULL "
        "  AND vf.\"download_status\" = 'downloaded' "
        'ORDER BY vf."alarm_id", vf."channel"'
    ).fetchall()
    for alarm_id, channel, rel_path in rows:
        if _resolve_media_path(rel_path).is_file():
            return str(alarm_id), int(channel)
    pytest.skip("Нет mp4 на диске (datasets/media gitignored) — happy-path неприменим.")


# ---------------------------------------------------------------------------
# GET /api/incidents — список
# ---------------------------------------------------------------------------


class TestIncidentsList:
    def test_list_ok_and_enriched(self, client: TestClient):
        r = client.get("/api/incidents")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) > 0
        first = data[0]
        # Обогащение заполнено (§3.1): driver/vehicle_model/risk_score не NULL.
        assert first["driver"]
        assert first["vehicle_model"]
        assert isinstance(first["risk_score"], int)


# ---------------------------------------------------------------------------
# GET /api/incidents/{id} — карточка
# ---------------------------------------------------------------------------


class TestIncidentDetail:
    def test_detail_ok(self, client: TestClient):
        first_id = client.get("/api/incidents").json()[0]["id"]
        r = client.get(f"/api/incidents/{first_id}")
        assert r.status_code == 200
        d = r.json()
        for key in ("cameras", "telemetry", "evidence_summary",
                    "speed_limit_kmh", "is_night"):
            assert key in d
        assert isinstance(d["cameras"], list)
        assert isinstance(d["telemetry"], list)

    def test_detail_404_on_missing_id(self, client: TestClient):
        r = client.get("/api/incidents/no-such-id")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/incidents/{id}/video/{channel} — FileResponse (DEF-1)
# ---------------------------------------------------------------------------


class TestIncidentVideo:
    def test_video_happy_path_returns_mp4(
        self, client: TestClient, db: duckdb.DuckDBPyConnection
    ):
        alarm_id, channel = _incident_with_downloaded_video(db)
        r = client.get(f"/api/incidents/{alarm_id}/video/{channel}")
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("video/mp4")
        assert len(r.content) > 0

    def test_video_invalid_channel_404(self, client: TestClient):
        first_id = client.get("/api/incidents").json()[0]["id"]
        r = client.get(f"/api/incidents/{first_id}/video/9")
        assert r.status_code == 404

    def test_video_missing_incident_404(self, client: TestClient):
        r = client.get("/api/incidents/no-such-id/video/5")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Заглушки — 501 (§3.4)
# ---------------------------------------------------------------------------


class TestStubsReturn501:
    @pytest.mark.parametrize("path", ["/api/fuel/summary", "/api/sensors", "/api/navigation"])
    def test_stub_501(self, client: TestClient, path: str):
        r = client.get(path)
        assert r.status_code == 501
