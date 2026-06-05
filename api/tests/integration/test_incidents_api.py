"""Интеграционные тесты домена incidents + actions (CONTRACT §3.1–§3.4).

Контракт ответа валидируется прогоном JSON обратно через Pydantic-схему
(`IncidentSummary`/`IncidentDetail` с `extra="forbid"`) — это строгая проверка
набора полей, а не только кодов ответа.
"""

from __future__ import annotations

import csv

import duckdb
import pytest
from fastapi.testclient import TestClient

from api.core.config import settings
from api.domain.incidents import IncidentDetail, IncidentSummary


# ---------------------------------------------------------------------------
# GET /api/health
# ---------------------------------------------------------------------------


def test_health_ok(client: TestClient):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /api/incidents — лента (§3.2)
# ---------------------------------------------------------------------------


class TestIncidentsList:
    def test_list_ok_and_schema(self, incidents: list[dict]):
        # 200 + непустой список; каждая строка валидна по IncidentSummary.
        assert isinstance(incidents, list) and len(incidents) > 0
        for item in incidents:
            model = IncidentSummary(**item)  # extra="forbid" → строгий контракт
            assert isinstance(model.risk_score, int)
            assert model.driver  # обогащение заполнено (§3.1)
            assert model.vehicle_model

    def test_limit_bounds_output(self, client: TestClient):
        r = client.get("/api/incidents", params={"limit": 5})
        assert r.status_code == 200
        assert len(r.json()) <= 5


class TestIncidentsFilters:
    """Фильтры `?severity=&source=&status=&vehicle_plate=` сужают выдачу."""

    def test_filter_severity(self, client: TestClient, incidents: list[dict]):
        severity = incidents[0]["severity"]
        data = client.get("/api/incidents", params={"severity": severity}).json()
        assert data, "фильтр по severity не должен опустошать выдачу для своего значения"
        assert all(i["severity"] == severity for i in data)
        assert len(data) <= len(incidents)

    def test_filter_source(self, client: TestClient, incidents: list[dict]):
        source = incidents[0]["source"]
        data = client.get("/api/incidents", params={"source": source}).json()
        assert data
        assert all(i["source"] == source for i in data)

    def test_filter_vehicle_plate(self, client: TestClient, incidents: list[dict]):
        plate = incidents[0]["vehicle_plate"]
        data = client.get(
            "/api/incidents", params={"vehicle_plate": plate}
        ).json()
        assert data
        assert all(i["vehicle_plate"] == plate for i in data)

    def test_filter_status_runtime(self, client: TestClient, incidents: list[dict]):
        # Дефолтный рантайм-статус — "active": фильтр оставляет только совпадающие.
        active = client.get("/api/incidents", params={"status": "active"}).json()
        assert all(i["status"] == "active" for i in active)
        # Несуществующий в рантайме статус — пустая выдача (полное сужение).
        closed = client.get("/api/incidents", params={"status": "closed"}).json()
        assert all(i["status"] == "closed" for i in closed)


# ---------------------------------------------------------------------------
# GET /api/incidents/{id} — карточка (§3.1)
# ---------------------------------------------------------------------------


class TestIncidentDetail:
    def test_detail_ok_and_schema(self, client: TestClient, first_incident_id: str):
        r = client.get(f"/api/incidents/{first_incident_id}")
        assert r.status_code == 200
        d = r.json()
        model = IncidentDetail(**d)  # строгий контракт §3.1 (detail-поля)
        # Явно проверяем поля, перечисленные в задании T2.
        assert isinstance(model.cameras, list)
        assert isinstance(model.telemetry, list)
        assert isinstance(model.confidence, int)
        assert model.driver_region
        assert isinstance(model.cam_extra, list)

    def test_detail_404_on_missing_id(self, client: TestClient):
        r = client.get("/api/incidents/no-such-id")
        assert r.status_code == 404
        assert "detail" in r.json()


# ---------------------------------------------------------------------------
# GET /api/incidents/{id}/video/{channel} — FileResponse (§3.2)
# ---------------------------------------------------------------------------


def _incident_with_downloaded_video(
    db: duckdb.DuckDBPyConnection,
) -> tuple[str, int]:
    """(alarm_id, channel) с mp4, реально лежащим на диске, иначе skip.

    `datasets/media` gitignored → в свежем worktree файлов нет: happy-path
    проверяется только когда файл доступен (skip, а не падение).
    """
    from api.routers.incidents import _resolve_media_path

    rows = db.execute(
        'SELECT vf."alarm_id", vf."channel", vf."media_relative_path" '
        'FROM "video_events__video_files" vf '
        'JOIN v_incidents i ON i.id = vf."alarm_id" '
        'WHERE vf."media_relative_path" IS NOT NULL '
        "  AND vf.\"download_status\" = 'downloaded' "
        'ORDER BY vf."alarm_id", vf."channel"'
    ).fetchall()
    for alarm_id, channel, rel_path in rows:
        if _resolve_media_path(rel_path).is_file():
            return str(alarm_id), int(channel)
    pytest.skip("Нет mp4 на диске (datasets/media gitignored) — happy-path неприменим.")


class TestIncidentVideo:
    def test_video_happy_path_returns_mp4(
        self, client: TestClient, db: duckdb.DuckDBPyConnection
    ):
        alarm_id, channel = _incident_with_downloaded_video(db)
        r = client.get(f"/api/incidents/{alarm_id}/video/{channel}")
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("video/mp4")
        assert len(r.content) > 0

    def test_video_invalid_channel_404(
        self, client: TestClient, first_incident_id: str
    ):
        r = client.get(f"/api/incidents/{first_incident_id}/video/9")
        assert r.status_code == 404

    def test_video_missing_incident_404(self, client: TestClient):
        r = client.get("/api/incidents/no-such-id/video/5")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/actions — журнал (§3.4): пишет строку в output/actions.csv
# ---------------------------------------------------------------------------


class TestActions:
    @pytest.fixture
    def isolated_output(self, tmp_path, monkeypatch):
        """Изолирует output/actions.csv во временную папку (без порчи реального журнала)."""
        monkeypatch.setattr(settings, "output_dir", tmp_path)
        return tmp_path / "actions.csv"

    @pytest.mark.parametrize("action", ["validate", "stop_vehicle"])
    def test_action_records_row_and_status(
        self,
        client: TestClient,
        first_incident_id: str,
        isolated_output,
        action: str,
    ):
        r = client.post(
            "/api/actions",
            json={
                "incident_id": first_incident_id,
                "action": action,
                "comment": "t2-integration",
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["incident_id"] == first_incident_id
        assert body["action"] == action
        assert body["status"] in {"active", "in_progress", "validated", "closed"}

        # Строка дописана в output/actions.csv.
        assert isolated_output.exists()
        with isolated_output.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert any(
            row["incident_id"] == first_incident_id and row["action"] == action
            for row in rows
        )

    def test_action_invalid_type_422(
        self, client: TestClient, first_incident_id: str, isolated_output
    ):
        # action вне enum (§3.4) → ошибка валидации тела (422).
        r = client.post(
            "/api/actions",
            json={"incident_id": first_incident_id, "action": "nope"},
        )
        assert r.status_code == 422
