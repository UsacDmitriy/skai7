"""Тесты API Гиперопеки (M-HYPERCARE).

T1: домен-схемы · T2: репозиторий · T3: эвалюатор · T4: роутер.
"""
import duckdb
import pytest
from fastapi.testclient import TestClient

from api.domain.hypercare import (
    EvidenceRequest,
    HypercareEvidence,
    HypercareRule,
    ManualRequest,
    TriggerSpec,
    WindowSpec,
)


# ── T1: домен-схемы ───────────────────────────────────────────────────────────


def test_rule_roundtrip_serialization():
    rule = HypercareRule(
        id="R-SABOTAGE",
        name="Саботаж камеры",
        enabled=True,
        role_scope="security",
        trigger=TriggerSpec(kind="event", alarm_codes=["CAMERA_TAMPER"]),
        window=WindowSpec(before_sec=300, after_sec=120, mode="continuous"),
        cameras=[1, 5, 2, 3],
    )
    dumped = rule.model_dump()
    assert HypercareRule(**dumped) == rule


def test_evidence_forbids_extra_fields():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        HypercareEvidence(
            id="E1",
            rule_id="R-SABOTAGE",
            rule_name="Саботаж камеры",
            vehicle_plate="А079АМ250",
            driver="Иванов И.",
            trigger_ts="2026-05-14T14:23:07",
            trigger_label="Саботаж",
            status="fulfilled",
            items=[],
            unexpected="x",
        )


# ── Общая in-memory БД для T2/T3 ──────────────────────────────────────────────


def _seed_db() -> duckdb.DuckDBPyConnection:
    db = duckdb.connect(":memory:")
    db.execute("""
        CREATE TABLE v_incidents (
            id VARCHAR, alarm_code VARCHAR, alarm_label_ru VARCHAR,
            ts VARCHAR, vehicle_plate VARCHAR, driver VARCHAR
        )""")
    db.execute("""INSERT INTO v_incidents VALUES
        ('a1','CAMERA_TAMPER','Саботаж','2026-05-14T14:23:07','А079АМ250','Иванов И.'),
        ('a2','OVERSPEED','Превышение','2026-05-14T10:00:00','В224ВВ125','Петров П.')""")
    db.execute("""
        CREATE TABLE video_events__video_files (
            alarm_id VARCHAR, channel INTEGER,
            download_status VARCHAR, media_relative_path VARCHAR
        )""")
    db.execute("""INSERT INTO video_events__video_files VALUES
        ('a1',1,'downloaded','video_events/a1_ch1.mp4'),
        ('a1',5,'downloaded','video_events/a1_ch5.mp4')""")
    return db


# ── T2: репозиторий ───────────────────────────────────────────────────────────


from api.repositories import hypercare_repo  # noqa: E402


def test_incidents_for_codes_filters():
    db = _seed_db()
    rows = hypercare_repo.incidents_for_codes(db, ["CAMERA_TAMPER"])
    assert len(rows) == 1
    assert rows[0]["vehicle_plate"] == "А079АМ250"


def test_incidents_for_codes_empty_when_no_match():
    db = _seed_db()
    assert hypercare_repo.incidents_for_codes(db, ["CRASH_SENSOR"]) == []


def test_video_clips_for_incident():
    db = _seed_db()
    clips = hypercare_repo.video_clips_for_incident(db, "a1")
    channels = {c["channel"] for c in clips}
    assert channels == {1, 5}


# ── T3: эвалюатор ────────────────────────────────────────────────────────────


from api.services import hypercare_service  # noqa: E402


def test_seed_rules_nonempty_and_valid():
    rules = hypercare_service.seed_rules()
    assert len(rules) >= 6
    assert all(isinstance(r, HypercareRule) for r in rules)
    assert any(r.trigger.kind == "manual" for r in rules)


def test_evaluate_event_rule_marks_fulfilled():
    db = _seed_db()
    rule = HypercareRule(
        id="R-SABOTAGE",
        name="Саботаж камеры",
        enabled=True,
        role_scope="all",
        trigger=TriggerSpec(kind="event", alarm_codes=["CAMERA_TAMPER"]),
        window=WindowSpec(before_sec=300, after_sec=120, mode="continuous"),
        cameras=[1, 5],
    )
    out = hypercare_service.evaluate(db, [rule], "all")
    assert len(out) == 1
    assert out[0].vehicle_plate == "А079АМ250"
    assert out[0].status == "fulfilled"
    assert {c.channel for c in out[0].items} == {1, 5}
    assert all(c.url is not None for c in out[0].items)


def test_evaluate_marks_pending_when_no_clip():
    db = _seed_db()
    rule = HypercareRule(
        id="R-NOCLIP",
        name="Превышение",
        enabled=True,
        role_scope="all",
        trigger=TriggerSpec(kind="event", alarm_codes=["OVERSPEED"]),
        window=WindowSpec(before_sec=60, after_sec=60, mode="continuous"),
        cameras=[1],
    )
    out = hypercare_service.evaluate(db, [rule], "all")
    assert out[0].status == "pending"
    assert out[0].items[0].eta_sec is not None


def test_evaluate_skips_disabled_and_role_mismatch():
    db = _seed_db()
    disabled = HypercareRule(
        id="R1",
        name="x",
        enabled=False,
        role_scope="all",
        trigger=TriggerSpec(kind="event", alarm_codes=["CAMERA_TAMPER"]),
        window=WindowSpec(before_sec=10, after_sec=10, mode="continuous"),
        cameras=[1],
    )
    other_role = HypercareRule(
        id="R2",
        name="y",
        enabled=True,
        role_scope="logist",
        trigger=TriggerSpec(kind="event", alarm_codes=["CAMERA_TAMPER"]),
        window=WindowSpec(before_sec=10, after_sec=10, mode="continuous"),
        cameras=[1],
    )
    assert hypercare_service.evaluate(db, [disabled], "all") == []
    assert hypercare_service.evaluate(db, [other_role], "security") == []


def test_evaluate_is_deterministic():
    rule = HypercareRule(
        id="R-NOCLIP",
        name="Превышение",
        enabled=True,
        role_scope="all",
        trigger=TriggerSpec(kind="event", alarm_codes=["OVERSPEED"]),
        window=WindowSpec(before_sec=60, after_sec=60, mode="continuous"),
        cameras=[1],
    )
    a = hypercare_service.evaluate(_seed_db(), [rule], "all")
    b = hypercare_service.evaluate(_seed_db(), [rule], "all")
    assert [e.model_dump() for e in a] == [e.model_dump() for e in b]


def test_manual_request_returns_pending_evidence():
    db = _seed_db()
    ev = hypercare_service.manual_request(
        db,
        ManualRequest(
            vehicle_plate="Е777КХ77",
            trigger_ts="2026-05-14T12:00:00",
            before_sec=60,
            after_sec=120,
            cameras=[1, 5],
        ),
    )
    assert ev.status == "pending"
    assert {c.channel for c in ev.items} == {1, 5}


# ── T4: роутер (требует реальной DuckDB) ─────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    from api.core.config import settings

    if not settings.db_path.exists():
        pytest.skip(f"DuckDB не собран ({settings.db_path}); запусти `make db`.")
    from api.main import app

    with TestClient(app) as c:
        yield c


def test_get_rules_200(client):
    resp = client.get("/api/hypercare/rules")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) and len(data) >= 6
    assert "trigger" in data[0] and "window" in data[0]


def test_post_evidence_200_and_schema(client):
    rules = client.get("/api/hypercare/rules").json()
    resp = client.post("/api/hypercare/evidence", json={"rules": rules, "role": "all"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_post_evidence_422_on_bad_rule(client):
    resp = client.post(
        "/api/hypercare/evidence", json={"rules": [{"id": "x"}], "role": "all"}
    )
    assert resp.status_code == 422


def test_post_request_200(client):
    resp = client.post(
        "/api/hypercare/request",
        json={
            "vehicle_plate": "Е777КХ77",
            "trigger_ts": "2026-05-14T12:00:00",
            "before_sec": 60,
            "after_sec": 120,
            "cameras": [1, 5],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


def test_post_request_422_on_bad_channel(client):
    resp = client.post(
        "/api/hypercare/request",
        json={
            "vehicle_plate": "Е777КХ77",
            "trigger_ts": "2026-05-14T12:00:00",
            "before_sec": 60,
            "after_sec": 120,
            "cameras": [9],
        },
    )
    assert resp.status_code == 422
