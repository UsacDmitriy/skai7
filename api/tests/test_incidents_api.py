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
# No-video инцидент достижим (w3-5) — empty-state + «Запросить архив»
# ---------------------------------------------------------------------------


def _no_video_incident_id(client: TestClient) -> str:
    """id первого инцидента с `video_available=false`, иначе skip.

    Путь №2 (seed) уже влит → строка есть. Если путь №1 (Волна 2, невидеосорсы
    через UNION) ещё не реализован и seed убрали — skip, чтобы тест не падал до
    появления no-video источников (см. w3-5 / §1.3).
    """
    rows = client.get("/api/incidents").json()
    for r in rows:
        if r.get("video_available") is False:
            return r["id"]
    pytest.skip("Нет инцидента с video_available=false (нет seed / источников Волны 2).")


class TestNoVideoIncident:
    def test_detail_no_video_empty_state(self, client: TestClient):
        iid = _no_video_incident_id(client)
        r = client.get(f"/api/incidents/{iid}")
        assert r.status_code == 200, r.text
        d = r.json()
        # Ветка empty-state: видео нет, но §2-поля для no-video заполнены.
        assert d["video_available"] is False
        assert d["video_count"] == 0
        assert d["sensor_active_after_sec"] is not None
        assert 1 <= d["sensor_active_after_sec"] <= 10
        # Камеры: ровно 3 канала, все offline (строк video_files нет).
        assert len(d["cameras"]) == 3
        assert all(c["status"] == "offline" for c in d["cameras"])
        assert d["cam_front_url"] is None
        assert d["cam_dms_url"] is None

    def test_no_video_video_endpoint_404(self, client: TestClient):
        iid = _no_video_incident_id(client)
        # Видео нет ни на одном канале → легитимный 404 (не 5xx).
        assert client.get(f"/api/incidents/{iid}/video/5").status_code == 404
