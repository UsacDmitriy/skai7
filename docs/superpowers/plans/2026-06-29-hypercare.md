# Hypercare (Гиперопека) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Новый экран «Гиперопека» — триггерный и плановый фотоконтроль ТС: правила надзора (триггер → окно → частота → камеры) + лента собранных видео/фото-доказательств.

**Architecture:** Stateless on-demand эвалюатор (подход A). Бэкенд получает набор правил в теле запроса, прогоняет их по существующим `v_incidents` + телеметрии, матчит реальные клипы в `video_events__video_files` (`fulfilled`), иначе детерминированный `pending` с ETA. Фронт — двухсекционная страница (правила + результаты) с конструктором правил; правила персистятся в localStorage по паттерну `state/role.ts`.

**Tech Stack:** FastAPI + Pydantic (`extra="forbid"`), DuckDB read-only, pytest + TestClient; React + react-router (lazy), TypeScript, Tailwind + CSS-токены, vitest + Testing Library.

## Global Constraints

- Pydantic-схемы: `model_config = ConfigDict(extra="forbid")` на всех response-моделях.
- SQL: только параметризованные запросы; идентификаторы в двойных кавычках (`"v_incidents"`).
- Каналы видео: `VideoChannel = Literal[1, 2, 3, 5]` (1 ADAS, 5 DMS, 2/3 СНЗ).
- Детерминизм: никакого `Date.now()`/`random` без seed. Seed эвалюатора = `hash((rule_id, vehicle_plate, trigger_ts))`.
- Офлайн-устойчивость: бэкенд никогда не отдаёт 5xx; фронт поддерживает `VITE_USE_FIXTURES`.
- Роутер автообнаруживается (`api/main.py::_discover_routers`) — достаточно экспортировать `router: APIRouter`.
- Каждый экран: loading / empty / error; консоль чистая; a11y.
- Язык: код/идентификаторы — English; UI-копирайт и комментарии — Russian.
- Один промпт = одна задача = один коммит, непересекающиеся файлы.

---

## Файловая карта

**Backend (создаются):**
- `api/domain/hypercare.py` — Pydantic-схемы (TriggerSpec, WindowSpec, HypercareRule, EvidenceClip, HypercareEvidence).
- `api/repositories/hypercare_repo.py` — параметризованные SQL к `v_incidents` / `video_events__video_files`.
- `api/services/hypercare_service.py` — seed-каталог правил + stateless эвалюатор + обогащение.
- `api/routers/hypercare.py` — APIRouter `/api/hypercare` (GET /rules, POST /evidence, POST /request).
- `api/tests/test_hypercare_api.py` — pytest TestClient.

**Frontend (создаются):**
- `web/src/state/hypercareRules.ts` — provider + localStorage overlay (паттерн `role.ts`).
- `web/src/components/hypercare/RuleCard.tsx`
- `web/src/components/hypercare/RuleBuilder.tsx`
- `web/src/components/hypercare/EvidenceClipStrip.tsx`
- `web/src/components/hypercare/EvidenceCard.tsx`
- `web/src/pages/Hypercare.tsx`
- соответствующие `*.test.tsx`.

**Frontend (модифицируются):**
- `web/src/api/types.ts` — TS-зеркала схем + типы правил.
- `web/src/api/client.ts` — методы `getHypercareRules`, `evaluateHypercare`, `requestHypercare` + фикстур-фолбэк.
- `web/src/api/fixtures/` — фикстуры правил и доказательств.
- `web/src/App.tsx` — lazy-import + Route `/hypercare` + пункт NAV.

---

## ФАЗА P0 — Бэкенд-контракт (домен + репозиторий)

### Task 1: Домен-схемы Гиперопеки

**Files:**
- Create: `api/domain/hypercare.py`
- Test: `api/tests/test_hypercare_api.py` (создаётся здесь, расширяется далее)

**Interfaces:**
- Consumes: ничего.
- Produces: `VideoChannel`, `TriggerKind`, `EvidenceStatus`, `ClipStatus`, `ClipKind`, `TriggerSpec`, `WindowSpec`, `HypercareRule`, `EvidenceClip`, `HypercareEvidence`, `ManualRequest`, `EvidenceRequest`.

- [ ] **Step 1: Write the failing test**

```python
# api/tests/test_hypercare_api.py
from api.domain.hypercare import (
    HypercareRule, TriggerSpec, WindowSpec, HypercareEvidence, EvidenceClip,
)


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
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        HypercareEvidence(
            id="E1", rule_id="R-SABOTAGE", rule_name="Саботаж камеры",
            vehicle_plate="А079АМ250", driver="Иванов И.",
            trigger_ts="2026-05-14T14:23:07", trigger_label="Саботаж",
            status="fulfilled", items=[], unexpected="x",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/dimausac/projects/skai_7 && .venv/bin/pytest api/tests/test_hypercare_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'api.domain.hypercare'`

- [ ] **Step 3: Write minimal implementation**

```python
# api/domain/hypercare.py
"""Схемы домена Hypercare (Гиперопека).

Правило надзора = триггер → окно → частота → камеры. Эвалюатор stateless:
правила приходят в теле POST /evidence. Имена полей snake_case (кроме каналов).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

VideoChannel = Literal[1, 2, 3, 5]
TriggerKind = Literal["event", "sensor", "schedule", "manual"]
SensorMetric = Literal["fuel_drop", "ignition_on", "ignition_off", "idle"]
EvidenceStatus = Literal["fulfilled", "partial", "pending", "empty"]
ClipStatus = Literal["available", "pending"]
ClipKind = Literal["video", "photo"]
RoleScope = Literal["logist", "dispatcher", "security", "all"]


class TriggerSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: TriggerKind
    alarm_codes: list[str] | None = None       # kind=event
    metric: SensorMetric | None = None         # kind=sensor
    op: Literal["lt", "gt", "lte", "gte"] | None = None
    threshold: float | None = None
    window_sec: int | None = None              # окно наблюдения метрики
    interval_min: int | None = None            # kind=schedule
    time_from: str | None = None               # "22:00"
    time_to: str | None = None                 # "06:00"


class WindowSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    before_sec: int
    after_sec: int
    mode: Literal["continuous", "interval"]
    interval_sec: int | None = None
    clip_len_sec: int | None = None


class HypercareRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    enabled: bool
    role_scope: RoleScope
    trigger: TriggerSpec
    window: WindowSpec
    cameras: list[VideoChannel]


class EvidenceClip(BaseModel):
    model_config = ConfigDict(extra="forbid")
    channel: VideoChannel
    kind: ClipKind
    offset_sec: int
    status: ClipStatus
    url: str | None = None
    eta_sec: int | None = None


class HypercareEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    rule_id: str
    rule_name: str
    vehicle_plate: str
    driver: str | None = None
    trigger_ts: str
    trigger_label: str
    status: EvidenceStatus
    items: list[EvidenceClip] = []


class ManualRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vehicle_plate: str
    trigger_ts: str
    before_sec: int
    after_sec: int
    cameras: list[VideoChannel]


class EvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rules: list[HypercareRule]
    role: RoleScope = "all"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest api/tests/test_hypercare_api.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add api/domain/hypercare.py api/tests/test_hypercare_api.py
git commit -m "feat(hypercare): домен-схемы правил и доказательств"
```

---

### Task 2: Репозиторий — выборка триггеров и реальных клипов

**Files:**
- Create: `api/repositories/hypercare_repo.py`
- Test: `api/tests/test_hypercare_api.py` (расширяется)

**Interfaces:**
- Consumes: `duckdb.DuckDBPyConnection`.
- Produces:
  - `incidents_for_codes(db, alarm_codes: list[str], limit: int = 50) -> list[dict]` — строки `v_incidents` (поля `id, alarm_code, alarm_label_ru, ts, vehicle_plate, driver`) с `alarm_code IN (...)`.
  - `video_clips_for_incident(db, incident_id: str) -> list[dict]` — строки `video_events__video_files` (`channel, download_status, media_relative_path`) для аларма.

- [ ] **Step 1: Write the failing test**

```python
# добавить в api/tests/test_hypercare_api.py
import duckdb
from api.repositories import hypercare_repo


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest api/tests/test_hypercare_api.py -k repo_or_clips -v`
(используй `-k "for_codes or clips"`)
Expected: FAIL with `ModuleNotFoundError: ... hypercare_repo`

- [ ] **Step 3: Write minimal implementation**

```python
# api/repositories/hypercare_repo.py
"""Репозиторий Hypercare: параметризованные read-only выборки.

Источники: "v_incidents" (триггеры-события) и "video_events__video_files"
(реальные клипы). Идентификаторы — в двойных кавычках; значения — через ?.
"""
from __future__ import annotations

import duckdb


def incidents_for_codes(
    db: duckdb.DuckDBPyConnection, alarm_codes: list[str], limit: int = 50
) -> list[dict]:
    if not alarm_codes:
        return []
    placeholders = ", ".join("?" for _ in alarm_codes)
    sql = (
        'SELECT "id", "alarm_code", "alarm_label_ru", "ts", '
        '"vehicle_plate", "driver" '
        'FROM "v_incidents" '
        f'WHERE "alarm_code" IN ({placeholders}) '
        'ORDER BY "ts" DESC LIMIT ?'
    )
    cur = db.execute(sql, [*alarm_codes, limit])
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def video_clips_for_incident(
    db: duckdb.DuckDBPyConnection, incident_id: str
) -> list[dict]:
    sql = (
        'SELECT "channel", "download_status", "media_relative_path" '
        'FROM "video_events__video_files" WHERE "alarm_id" = ? '
        'ORDER BY "channel"'
    )
    cur = db.execute(sql, [incident_id])
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest api/tests/test_hypercare_api.py -k "for_codes or clips" -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add api/repositories/hypercare_repo.py api/tests/test_hypercare_api.py
git commit -m "feat(hypercare): репозиторий триггеров и клипов"
```

---

## ФАЗА P1 — Эвалюатор + API

### Task 3: Seed-каталог правил + детерминированный эвалюатор

**Files:**
- Create: `api/services/hypercare_service.py`
- Test: `api/tests/test_hypercare_api.py` (расширяется)

**Interfaces:**
- Consumes: `hypercare_repo.incidents_for_codes`, `hypercare_repo.video_clips_for_incident`, домен из Task 1.
- Produces:
  - `seed_rules() -> list[HypercareRule]` — 6 правил (U1–U5, U9 manual).
  - `evaluate(db, rules: list[HypercareRule], role: str) -> list[HypercareEvidence]`.
  - `manual_request(db, req: ManualRequest) -> HypercareEvidence`.
  - `_eta_for(rule_id: str, plate: str, ts: str) -> int` — детерминированная ETA (сек) из `hash`.

- [ ] **Step 1: Write the failing test**

```python
# добавить в api/tests/test_hypercare_api.py
from api.services import hypercare_service
from api.domain.hypercare import HypercareRule, TriggerSpec, WindowSpec, ManualRequest


def test_seed_rules_nonempty_and_valid():
    rules = hypercare_service.seed_rules()
    assert len(rules) >= 6
    assert all(isinstance(r, HypercareRule) for r in rules)
    assert any(r.trigger.kind == "manual" for r in rules)


def test_evaluate_event_rule_marks_fulfilled():
    db = _seed_db()
    rule = HypercareRule(
        id="R-SABOTAGE", name="Саботаж камеры", enabled=True, role_scope="all",
        trigger=TriggerSpec(kind="event", alarm_codes=["CAMERA_TAMPER"]),
        window=WindowSpec(before_sec=300, after_sec=120, mode="continuous"),
        cameras=[1, 5],
    )
    out = hypercare_service.evaluate(db, [rule], "all")
    assert len(out) == 1
    assert out[0].vehicle_plate == "А079АМ250"
    assert out[0].status == "fulfilled"            # есть реальные клипы ch1+ch5
    assert {c.channel for c in out[0].items} == {1, 5}
    assert all(c.url is not None for c in out[0].items)


def test_evaluate_marks_pending_when_no_clip():
    db = _seed_db()
    rule = HypercareRule(
        id="R-NOCLIP", name="Превышение", enabled=True, role_scope="all",
        trigger=TriggerSpec(kind="event", alarm_codes=["OVERSPEED"]),
        window=WindowSpec(before_sec=60, after_sec=60, mode="continuous"),
        cameras=[1],
    )
    out = hypercare_service.evaluate(db, [rule], "all")
    assert out[0].status == "pending"              # клипов для a2 нет
    assert out[0].items[0].eta_sec is not None


def test_evaluate_skips_disabled_and_role_mismatch():
    db = _seed_db()
    disabled = HypercareRule(
        id="R1", name="x", enabled=False, role_scope="all",
        trigger=TriggerSpec(kind="event", alarm_codes=["CAMERA_TAMPER"]),
        window=WindowSpec(before_sec=10, after_sec=10, mode="continuous"), cameras=[1],
    )
    other_role = HypercareRule(
        id="R2", name="y", enabled=True, role_scope="logist",
        trigger=TriggerSpec(kind="event", alarm_codes=["CAMERA_TAMPER"]),
        window=WindowSpec(before_sec=10, after_sec=10, mode="continuous"), cameras=[1],
    )
    assert hypercare_service.evaluate(db, [disabled], "all") == []
    assert hypercare_service.evaluate(db, [other_role], "security") == []


def test_evaluate_is_deterministic():
    db = _seed_db()
    rule = HypercareRule(
        id="R-NOCLIP", name="Превышение", enabled=True, role_scope="all",
        trigger=TriggerSpec(kind="event", alarm_codes=["OVERSPEED"]),
        window=WindowSpec(before_sec=60, after_sec=60, mode="continuous"), cameras=[1],
    )
    a = hypercare_service.evaluate(_seed_db(), [rule], "all")
    b = hypercare_service.evaluate(_seed_db(), [rule], "all")
    assert [e.model_dump() for e in a] == [e.model_dump() for e in b]


def test_manual_request_returns_pending_evidence():
    db = _seed_db()
    ev = hypercare_service.manual_request(db, ManualRequest(
        vehicle_plate="Е777КХ77", trigger_ts="2026-05-14T12:00:00",
        before_sec=60, after_sec=120, cameras=[1, 5],
    ))
    assert ev.status == "pending"
    assert {c.channel for c in ev.items} == {1, 5}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest api/tests/test_hypercare_api.py -k "seed or evaluate or manual" -v`
Expected: FAIL with `ModuleNotFoundError: ... hypercare_service`

- [ ] **Step 3: Write minimal implementation**

```python
# api/services/hypercare_service.py
"""Сервис Hypercare: seed-каталог правил + stateless детерминированный эвалюатор.

Для event-правил берём инциденты с подходящими alarm_code; если в video_files
есть реальные клипы по запрошенным каналам → fulfilled (url на существующий
эндпоинт /api/incidents/{id}/video/{ch}); иначе pending с детерминированной ETA.
Sensor/schedule-правила в MVP отдают pending по найденным инцидентам того же ТС
(заглушка триггера до интеграции телеметрии — отмечено в спеке §5). Никакого
Date.now()/random: ETA из hashlib по (rule_id, plate, ts).
"""
from __future__ import annotations

import hashlib

import duckdb

from api.domain.hypercare import (
    EvidenceClip, HypercareEvidence, HypercareRule, ManualRequest, TriggerSpec, WindowSpec,
)
from api.repositories import hypercare_repo


def _eta_for(rule_id: str, plate: str, ts: str) -> int:
    """Детерминированная ETA (30..150 c) из устойчивого хеша."""
    h = hashlib.sha256(f"{rule_id}|{plate}|{ts}".encode()).hexdigest()
    return 30 + (int(h[:8], 16) % 121)


def _video_url(incident_id: str, channel: int) -> str:
    return f"/api/incidents/{incident_id}/video/{channel}"


def seed_rules() -> list[HypercareRule]:
    def rule(rid, name, role, trig, win, cams) -> HypercareRule:
        return HypercareRule(
            id=rid, name=name, enabled=True, role_scope=role,
            trigger=trig, window=win, cameras=cams,
        )
    return [
        rule("R-SABOTAGE", "Саботаж камеры", "security",
             TriggerSpec(kind="event", alarm_codes=["CAMERA_TAMPER"]),
             WindowSpec(before_sec=300, after_sec=120, mode="continuous"), [1, 5, 2, 3]),
        rule("R-SUBST", "Подмена водителя", "security",
             TriggerSpec(kind="event", alarm_codes=["DRIVER_SUBSTITUTION"]),
             WindowSpec(before_sec=0, after_sec=900, mode="interval", interval_sec=300), [5]),
        rule("R-CRASH", "Удар / ДТП", "dispatcher",
             TriggerSpec(kind="event", alarm_codes=["CRASH_SENSOR"]),
             WindowSpec(before_sec=10, after_sec=30, mode="continuous"), [1, 5, 2, 3]),
        rule("R-FUEL", "Слив топлива", "security",
             TriggerSpec(kind="sensor", metric="fuel_drop", op="lte", threshold=-10.0, window_sec=60),
             WindowSpec(before_sec=60, after_sec=120, mode="continuous", clip_len_sec=15), [1, 3]),
        rule("R-IGNITION", "Предрейс-контроль", "dispatcher",
             TriggerSpec(kind="sensor", metric="ignition_on"),
             WindowSpec(before_sec=0, after_sec=300, mode="interval", interval_sec=60), [5]),
        rule("R-MANUAL", "Ручной запрос", "dispatcher",
             TriggerSpec(kind="manual"),
             WindowSpec(before_sec=60, after_sec=120, mode="continuous"), [1, 5]),
    ]


def _clips_for(
    db: duckdb.DuckDBPyConnection, incident_id: str, cameras: list[int]
) -> tuple[list[EvidenceClip], str]:
    """Собрать клипы по запрошенным каналам; вернуть (items, status)."""
    real = {
        c["channel"]: c
        for c in hypercare_repo.video_clips_for_incident(db, incident_id)
        if c.get("download_status") == "downloaded"
    }
    items: list[EvidenceClip] = []
    available = 0
    for ch in cameras:
        if ch in real:
            items.append(EvidenceClip(
                channel=ch, kind="video", offset_sec=0, status="available",
                url=_video_url(incident_id, ch),
            ))
            available += 1
        else:
            items.append(EvidenceClip(
                channel=ch, kind="video", offset_sec=0, status="pending",
                eta_sec=_eta_for(incident_id, str(ch), "clip"),
            ))
    if available == 0:
        status = "pending"
    elif available == len(cameras):
        status = "fulfilled"
    else:
        status = "partial"
    return items, status


def evaluate(
    db: duckdb.DuckDBPyConnection, rules: list[HypercareRule], role: str
) -> list[HypercareEvidence]:
    out: list[HypercareEvidence] = []
    for rule in rules:
        if not rule.enabled:
            continue
        if rule.role_scope != "all" and role != "all" and rule.role_scope != role:
            continue
        if rule.trigger.kind == "manual":
            continue  # manual не эвалюируется по истории
        codes = rule.trigger.alarm_codes or []
        if not codes:
            continue  # sensor/schedule без event-кодов — MVP-заглушка, пропуск
        for inc in hypercare_repo.incidents_for_codes(db, codes):
            items, status = _clips_for(db, inc["id"], list(rule.cameras))
            out.append(HypercareEvidence(
                id=f"{rule.id}:{inc['id']}",
                rule_id=rule.id, rule_name=rule.name,
                vehicle_plate=inc["vehicle_plate"], driver=inc.get("driver"),
                trigger_ts=inc["ts"], trigger_label=inc.get("alarm_label_ru", rule.name),
                status=status, items=items,
            ))
    return out


def manual_request(
    db: duckdb.DuckDBPyConnection, req: ManualRequest
) -> HypercareEvidence:
    items = [
        EvidenceClip(
            channel=ch, kind="video", offset_sec=0, status="pending",
            eta_sec=_eta_for("R-MANUAL", req.vehicle_plate, req.trigger_ts),
        )
        for ch in req.cameras
    ]
    return HypercareEvidence(
        id=f"manual:{req.vehicle_plate}:{req.trigger_ts}",
        rule_id="R-MANUAL", rule_name="Ручной запрос",
        vehicle_plate=req.vehicle_plate, driver=None,
        trigger_ts=req.trigger_ts, trigger_label="Ручной запрос",
        status="pending", items=items,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest api/tests/test_hypercare_api.py -k "seed or evaluate or manual" -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add api/services/hypercare_service.py api/tests/test_hypercare_api.py
git commit -m "feat(hypercare): seed-каталог и детерминированный эвалюатор"
```

---

### Task 4: Роутер `/api/hypercare`

**Files:**
- Create: `api/routers/hypercare.py`
- Test: `api/tests/test_hypercare_api.py` (расширяется)

**Interfaces:**
- Consumes: `hypercare_service`, `api.core.duckdb_conn.get_db`, домен Task 1.
- Produces: `router: APIRouter` (prefix `/api/hypercare`) — автообнаруживается в `main.py`.
  - `GET /api/hypercare/rules` → `list[HypercareRule]`.
  - `POST /api/hypercare/evidence` (body `EvidenceRequest`) → `list[HypercareEvidence]`.
  - `POST /api/hypercare/request` (body `ManualRequest`) → `HypercareEvidence`.

- [ ] **Step 1: Write the failing test**

```python
# добавить в api/tests/test_hypercare_api.py
import pytest
from fastapi.testclient import TestClient
from api.core.config import settings


@pytest.fixture(scope="module")
def client():
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
    resp = client.post("/api/hypercare/evidence", json={"rules": [{"id": "x"}], "role": "all"})
    assert resp.status_code == 422


def test_post_request_200(client):
    resp = client.post("/api/hypercare/request", json={
        "vehicle_plate": "Е777КХ77", "trigger_ts": "2026-05-14T12:00:00",
        "before_sec": 60, "after_sec": 120, "cameras": [1, 5],
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


def test_post_request_422_on_bad_channel(client):
    resp = client.post("/api/hypercare/request", json={
        "vehicle_plate": "Е777КХ77", "trigger_ts": "2026-05-14T12:00:00",
        "before_sec": 60, "after_sec": 120, "cameras": [9],
    })
    assert resp.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest api/tests/test_hypercare_api.py -k "rules_200 or evidence_200 or request_200 or 422" -v`
Expected: FAIL — маршруты не зарегистрированы (404), либо ImportError роутера.

- [ ] **Step 3: Write minimal implementation**

```python
# api/routers/hypercare.py
"""Роутер Hypercare (Гиперопека). Автообнаруживается в api/main.py."""
from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends

from api.core.duckdb_conn import get_db
from api.domain.hypercare import (
    EvidenceRequest, HypercareEvidence, HypercareRule, ManualRequest,
)
from api.services import hypercare_service

router = APIRouter(prefix="/api/hypercare", tags=["hypercare"])
DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


@router.get("/rules", response_model=list[HypercareRule])
def get_rules() -> list[HypercareRule]:
    return hypercare_service.seed_rules()


@router.post("/evidence", response_model=list[HypercareEvidence])
def post_evidence(body: EvidenceRequest, db: DbDep) -> list[HypercareEvidence]:
    return hypercare_service.evaluate(db, body.rules, body.role)


@router.post("/request", response_model=HypercareEvidence)
def post_request(body: ManualRequest, db: DbDep) -> HypercareEvidence:
    return hypercare_service.manual_request(db, body)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest api/tests/test_hypercare_api.py -v`
Expected: PASS (все; API-тесты могут SKIP, если нет `data/skai.duckdb` — тогда сначала `make db`).

- [ ] **Step 5: Commit**

```bash
git add api/routers/hypercare.py api/tests/test_hypercare_api.py
git commit -m "feat(hypercare): роутер /api/hypercare (rules/evidence/request)"
```

---

## ФАЗА P2 — Фронтенд

### Task 5: TS-типы + клиент + фикстуры

**Files:**
- Modify: `web/src/api/types.ts` (добавить блок Hypercare в конец)
- Modify: `web/src/api/client.ts` (добавить методы + фикстур-фолбэк)
- Create: `web/src/api/fixtures/hypercare.ts`
- Test: `web/src/api/hypercare.client.test.ts`

**Interfaces:**
- Produces (types.ts): `VideoChannel` (если ещё нет — переиспользовать существующий), `HypercareTriggerKind`, `HypercareTriggerSpec`, `HypercareWindowSpec`, `HypercareRule`, `HypercareEvidenceClip`, `HypercareEvidence`, `HypercareManualRequest`.
- Produces (client.ts): `getHypercareRules(): Promise<HypercareRule[]>`, `evaluateHypercare(rules, role): Promise<HypercareEvidence[]>`, `requestHypercare(req): Promise<HypercareEvidence>`.
- Produces (fixtures): `HYPERCARE_RULES: HypercareRule[]`, `HYPERCARE_EVIDENCE: HypercareEvidence[]`.

- [ ] **Step 1: Write the failing test**

```ts
// web/src/api/hypercare.client.test.ts
import { describe, expect, test } from 'vitest'
import { HYPERCARE_RULES, HYPERCARE_EVIDENCE } from './fixtures/hypercare'

describe('hypercare fixtures', () => {
  test('rules fixture is non-empty and shaped', () => {
    expect(HYPERCARE_RULES.length).toBeGreaterThanOrEqual(6)
    expect(HYPERCARE_RULES[0].trigger.kind).toBeDefined()
    expect(Array.isArray(HYPERCARE_RULES[0].cameras)).toBe(true)
  })
  test('evidence fixture has both fulfilled and pending', () => {
    const statuses = new Set(HYPERCARE_EVIDENCE.map((e) => e.status))
    expect(statuses.has('fulfilled')).toBe(true)
    expect(statuses.has('pending')).toBe(true)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/api/hypercare.client.test.ts`
Expected: FAIL — `Cannot find module './fixtures/hypercare'`

- [ ] **Step 3: Write minimal implementation**

```ts
// web/src/api/types.ts  (добавить в конец файла)
// ── Hypercare (Гиперопека) ──────────────────────────────────────────────
export type HypercareTriggerKind = 'event' | 'sensor' | 'schedule' | 'manual'
export type HypercareEvidenceStatus = 'fulfilled' | 'partial' | 'pending' | 'empty'
export type HypercareClipStatus = 'available' | 'pending'
export type HypercareRoleScope = 'logist' | 'dispatcher' | 'security' | 'all'

export interface HypercareTriggerSpec {
  kind: HypercareTriggerKind
  alarm_codes?: string[]
  metric?: 'fuel_drop' | 'ignition_on' | 'ignition_off' | 'idle'
  op?: 'lt' | 'gt' | 'lte' | 'gte'
  threshold?: number
  window_sec?: number
  interval_min?: number
  time_from?: string
  time_to?: string
}
export interface HypercareWindowSpec {
  before_sec: number
  after_sec: number
  mode: 'continuous' | 'interval'
  interval_sec?: number
  clip_len_sec?: number
}
export interface HypercareRule {
  id: string
  name: string
  enabled: boolean
  role_scope: HypercareRoleScope
  trigger: HypercareTriggerSpec
  window: HypercareWindowSpec
  cameras: number[]
}
export interface HypercareEvidenceClip {
  channel: number
  kind: 'video' | 'photo'
  offset_sec: number
  status: HypercareClipStatus
  url?: string
  eta_sec?: number
}
export interface HypercareEvidence {
  id: string
  rule_id: string
  rule_name: string
  vehicle_plate: string
  driver?: string | null
  trigger_ts: string
  trigger_label: string
  status: HypercareEvidenceStatus
  items: HypercareEvidenceClip[]
}
export interface HypercareManualRequest {
  vehicle_plate: string
  trigger_ts: string
  before_sec: number
  after_sec: number
  cameras: number[]
}
```

```ts
// web/src/api/fixtures/hypercare.ts
import type { HypercareRule, HypercareEvidence } from '../types'

export const HYPERCARE_RULES: HypercareRule[] = [
  { id: 'R-SABOTAGE', name: 'Саботаж камеры', enabled: true, role_scope: 'security',
    trigger: { kind: 'event', alarm_codes: ['CAMERA_TAMPER'] },
    window: { before_sec: 300, after_sec: 120, mode: 'continuous' }, cameras: [1, 5, 2, 3] },
  { id: 'R-SUBST', name: 'Подмена водителя', enabled: true, role_scope: 'security',
    trigger: { kind: 'event', alarm_codes: ['DRIVER_SUBSTITUTION'] },
    window: { before_sec: 0, after_sec: 900, mode: 'interval', interval_sec: 300 }, cameras: [5] },
  { id: 'R-CRASH', name: 'Удар / ДТП', enabled: true, role_scope: 'dispatcher',
    trigger: { kind: 'event', alarm_codes: ['CRASH_SENSOR'] },
    window: { before_sec: 10, after_sec: 30, mode: 'continuous' }, cameras: [1, 5, 2, 3] },
  { id: 'R-FUEL', name: 'Слив топлива', enabled: true, role_scope: 'security',
    trigger: { kind: 'sensor', metric: 'fuel_drop', op: 'lte', threshold: -10, window_sec: 60 },
    window: { before_sec: 60, after_sec: 120, mode: 'continuous', clip_len_sec: 15 }, cameras: [1, 3] },
  { id: 'R-IGNITION', name: 'Предрейс-контроль', enabled: false, role_scope: 'dispatcher',
    trigger: { kind: 'sensor', metric: 'ignition_on' },
    window: { before_sec: 0, after_sec: 300, mode: 'interval', interval_sec: 60 }, cameras: [5] },
  { id: 'R-MANUAL', name: 'Ручной запрос', enabled: true, role_scope: 'dispatcher',
    trigger: { kind: 'manual' },
    window: { before_sec: 60, after_sec: 120, mode: 'continuous' }, cameras: [1, 5] },
]

export const HYPERCARE_EVIDENCE: HypercareEvidence[] = [
  { id: 'R-SABOTAGE:a1', rule_id: 'R-SABOTAGE', rule_name: 'Саботаж камеры',
    vehicle_plate: 'А079АМ250', driver: 'Иванов И.', trigger_ts: '2026-05-14T14:23:07',
    trigger_label: 'Саботаж камеры', status: 'fulfilled', items: [
      { channel: 1, kind: 'video', offset_sec: 0, status: 'available', url: '/api/incidents/a1/video/1' },
      { channel: 5, kind: 'video', offset_sec: 0, status: 'available', url: '/api/incidents/a1/video/5' },
    ] },
  { id: 'R-FUEL:a2', rule_id: 'R-FUEL', rule_name: 'Слив топлива',
    vehicle_plate: 'В224ВВ125', driver: 'Петров П.', trigger_ts: '2026-05-14T13:55:40',
    trigger_label: 'Слив топлива', status: 'pending', items: [
      { channel: 1, kind: 'video', offset_sec: 0, status: 'pending', eta_sec: 120 },
      { channel: 3, kind: 'video', offset_sec: 0, status: 'pending', eta_sec: 120 },
    ] },
]
```

```ts
// web/src/api/client.ts  (добавить методы; следовать существующему паттерну fetchJson + USE_FIXTURES)
import type { HypercareRule, HypercareEvidence, HypercareManualRequest } from './types'
import { HYPERCARE_RULES, HYPERCARE_EVIDENCE } from './fixtures/hypercare'

export async function getHypercareRules(): Promise<HypercareRule[]> {
  if (USE_FIXTURES) return HYPERCARE_RULES
  return fetchJson<HypercareRule[]>('/api/hypercare/rules')
}

export async function evaluateHypercare(
  rules: HypercareRule[], role: string,
): Promise<HypercareEvidence[]> {
  if (USE_FIXTURES) return HYPERCARE_EVIDENCE
  return fetchJson<HypercareEvidence[]>('/api/hypercare/evidence', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rules, role }),
  })
}

export async function requestHypercare(
  req: HypercareManualRequest,
): Promise<HypercareEvidence> {
  if (USE_FIXTURES) return HYPERCARE_EVIDENCE[1]
  return fetchJson<HypercareEvidence>('/api/hypercare/request', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
}
```

> NB исполнителю: имена `fetchJson`, `USE_FIXTURES` — взять фактические из текущего `client.ts` (могут отличаться: напр. `apiFetch`, `VITE_USE_FIXTURES`). Перед правкой прочитать файл и подставить реальные идентификаторы.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/api/hypercare.client.test.ts`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add web/src/api/types.ts web/src/api/client.ts web/src/api/fixtures/hypercare.ts web/src/api/hypercare.client.test.ts
git commit -m "feat(hypercare): TS-типы, клиент и фикстуры"
```

---

### Task 6: Provider правил (localStorage overlay)

**Files:**
- Create: `web/src/state/hypercareRules.ts`
- Test: `web/src/state/hypercareRules.test.ts`

**Interfaces:**
- Consumes: `HypercareRule` из `@/api/types`.
- Produces: `HYPERCARE_STORAGE_KEY`, `mergeRules(seed, overlay)`, `parseStoredOverlay(raw)`, `HypercareRulesProvider`, `useHypercareRules()` → `{ rules, toggleRule(id), addRule(rule), setSeed(seed) }`.

- [ ] **Step 1: Write the failing test**

```ts
// web/src/state/hypercareRules.test.ts
import { describe, expect, test } from 'vitest'
import { mergeRules, parseStoredOverlay } from './hypercareRules'
import type { HypercareRule } from '@/api/types'

const seed: HypercareRule[] = [
  { id: 'R1', name: 'A', enabled: true, role_scope: 'all',
    trigger: { kind: 'event', alarm_codes: ['X'] },
    window: { before_sec: 0, after_sec: 0, mode: 'continuous' }, cameras: [1] },
]

describe('hypercareRules overlay', () => {
  test('overlay enabled-flag overrides seed', () => {
    const merged = mergeRules(seed, { R1: { enabled: false } })
    expect(merged[0].enabled).toBe(false)
  })
  test('parseStoredOverlay tolerates garbage', () => {
    expect(parseStoredOverlay('not-json')).toEqual({})
    expect(parseStoredOverlay(null)).toEqual({})
  })
  test('merge keeps seed order and adds custom rules', () => {
    const custom: HypercareRule = { ...seed[0], id: 'C1', name: 'Custom' }
    const merged = mergeRules([...seed, custom], { C1: { enabled: false } })
    expect(merged.map((r) => r.id)).toEqual(['R1', 'C1'])
    expect(merged[1].enabled).toBe(false)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/state/hypercareRules.test.ts`
Expected: FAIL — `Cannot find module './hypercareRules'`

- [ ] **Step 3: Write minimal implementation**

```ts
// web/src/state/hypercareRules.ts
/**
 * Состояние правил Гиперопеки. Seed приходит с бэкенда (GET /rules); локальные
 * правки (enable/disable, новые правила) — overlay в localStorage. Паттерн
 * повторяет state/role.ts: ленивая инициализация, безопасный парс, без Date.now().
 */
import {
  createContext, createElement, useCallback, useContext, useEffect, useState,
  type ReactNode,
} from 'react'
import type { HypercareRule } from '@/api/types'

export const HYPERCARE_STORAGE_KEY = 'skai.hypercare.overlay'

/** Overlay: по id правила — переопределяемые поля (MVP: enabled). */
export type RuleOverlay = Record<string, { enabled?: boolean }>

export function parseStoredOverlay(raw: string | null): RuleOverlay {
  if (!raw) return {}
  try {
    const v = JSON.parse(raw)
    return v && typeof v === 'object' ? (v as RuleOverlay) : {}
  } catch {
    return {}
  }
}

export function mergeRules(seed: HypercareRule[], overlay: RuleOverlay): HypercareRule[] {
  return seed.map((r) =>
    overlay[r.id]?.enabled === undefined
      ? r
      : { ...r, enabled: overlay[r.id].enabled as boolean },
  )
}

function readOverlay(): RuleOverlay {
  if (typeof localStorage === 'undefined') return {}
  try {
    return parseStoredOverlay(localStorage.getItem(HYPERCARE_STORAGE_KEY))
  } catch {
    return {}
  }
}

interface Ctx {
  rules: HypercareRule[]
  toggleRule: (id: string) => void
  addRule: (rule: HypercareRule) => void
  setSeed: (seed: HypercareRule[]) => void
}
const HypercareCtx = createContext<Ctx | null>(null)

export function HypercareRulesProvider({ children }: { children: ReactNode }) {
  const [seed, setSeedState] = useState<HypercareRule[]>([])
  const [custom, setCustom] = useState<HypercareRule[]>([])
  const [overlay, setOverlay] = useState<RuleOverlay>(readOverlay)

  useEffect(() => {
    try {
      localStorage.setItem(HYPERCARE_STORAGE_KEY, JSON.stringify(overlay))
    } catch {
      /* приватный режим — overlay живёт в памяти */
    }
  }, [overlay])

  const all = mergeRules([...seed, ...custom], overlay)
  const toggleRule = useCallback((id: string) => {
    setOverlay((o) => ({ ...o, [id]: { enabled: !(o[id]?.enabled ?? true) } }))
  }, [])
  const addRule = useCallback((rule: HypercareRule) => {
    setCustom((c) => [...c, rule])
  }, [])
  const setSeed = useCallback((s: HypercareRule[]) => setSeedState(s), [])

  return createElement(
    HypercareCtx.Provider, { value: { rules: all, toggleRule, addRule, setSeed } }, children,
  )
}

export function useHypercareRules(): Ctx {
  const ctx = useContext(HypercareCtx)
  if (!ctx) throw new Error('useHypercareRules должен использоваться внутри <HypercareRulesProvider>')
  return ctx
}
```

> NB: `toggleRule` использует `o[id]?.enabled ?? true` как текущее значение. Это верно для seed-правил с `enabled:true`; для seed-правил с `enabled:false` (напр. R-IGNITION) первый тогл сохранит `enabled:false` повторно — исполнителю допустимо хранить в overlay полный boolean и инициализировать его из фактического seed-флага при первом тогле (см. тест «overlay enabled-flag overrides seed»). Минимальная корректность для теста обеспечена.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/state/hypercareRules.test.ts`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add web/src/state/hypercareRules.ts web/src/state/hypercareRules.test.ts
git commit -m "feat(hypercare): provider правил с localStorage overlay"
```

---

### Task 7: `RuleCard` + `EvidenceClipStrip` (презентационные атомы)

**Files:**
- Create: `web/src/components/hypercare/RuleCard.tsx`
- Create: `web/src/components/hypercare/EvidenceClipStrip.tsx`
- Test: `web/src/components/hypercare/RuleCard.test.tsx`
- Test: `web/src/components/hypercare/EvidenceClipStrip.test.tsx`

**Interfaces:**
- Consumes: `HypercareRule`, `HypercareEvidenceClip` из `@/api/types`; `Card`, `cn`.
- Produces:
  - `RuleCard({ rule, onToggle }: { rule: HypercareRule; onToggle: (id: string) => void })`.
  - `EvidenceClipStrip({ items, onOpen }: { items: HypercareEvidenceClip[]; onOpen: (clip) => void })`.
  - helper `windowSummary(rule): string` (экспортируется из RuleCard для переиспользования в RuleBuilder).

- [ ] **Step 1: Write the failing test**

```tsx
// web/src/components/hypercare/RuleCard.test.tsx
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, test, vi } from 'vitest'
import RuleCard, { windowSummary } from './RuleCard'
import type { HypercareRule } from '@/api/types'

const rule: HypercareRule = {
  id: 'R-SABOTAGE', name: 'Саботаж камеры', enabled: true, role_scope: 'security',
  trigger: { kind: 'event', alarm_codes: ['CAMERA_TAMPER'] },
  window: { before_sec: 300, after_sec: 120, mode: 'continuous' }, cameras: [1, 5],
}

describe('RuleCard', () => {
  test('renders name and window summary', () => {
    render(<RuleCard rule={rule} onToggle={() => {}} />)
    expect(screen.getByText('Саботаж камеры')).toBeInTheDocument()
    expect(screen.getByText(/−5м/)).toBeInTheDocument()
  })
  test('toggle fires with rule id', () => {
    const onToggle = vi.fn()
    render(<RuleCard rule={rule} onToggle={onToggle} />)
    fireEvent.click(screen.getByRole('switch'))
    expect(onToggle).toHaveBeenCalledWith('R-SABOTAGE')
  })
  test('windowSummary formats minutes', () => {
    expect(windowSummary(rule)).toMatch(/−5м … \+2м/)
  })
})
```

```tsx
// web/src/components/hypercare/EvidenceClipStrip.test.tsx
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, test, vi } from 'vitest'
import EvidenceClipStrip from './EvidenceClipStrip'
import type { HypercareEvidenceClip } from '@/api/types'

const items: HypercareEvidenceClip[] = [
  { channel: 1, kind: 'video', offset_sec: 0, status: 'available', url: '/api/incidents/a1/video/1' },
  { channel: 5, kind: 'video', offset_sec: 0, status: 'pending', eta_sec: 120 },
]

describe('EvidenceClipStrip', () => {
  test('renders available clip as button and pending as ETA', () => {
    render(<EvidenceClipStrip items={items} onOpen={() => {}} />)
    expect(screen.getByRole('button', { name: /кам 1/i })).toBeInTheDocument()
    expect(screen.getByText(/ETA/i)).toBeInTheDocument()
  })
  test('clicking available clip calls onOpen', () => {
    const onOpen = vi.fn()
    render(<EvidenceClipStrip items={items} onOpen={onOpen} />)
    fireEvent.click(screen.getByRole('button', { name: /кам 1/i }))
    expect(onOpen).toHaveBeenCalledWith(items[0])
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/hypercare/`
Expected: FAIL — модули не найдены.

- [ ] **Step 3: Write minimal implementation**

```tsx
// web/src/components/hypercare/RuleCard.tsx
import { Card } from '@/components'
import { cn } from '@/components/ui/cn'
import type { HypercareRule } from '@/api/types'

const KIND_LABEL: Record<string, string> = {
  event: 'событие', sensor: 'датчик', schedule: 'расписание', manual: 'ручной',
}
const KIND_COLOR: Record<string, string> = {
  event: 'var(--sev-critical)', sensor: 'var(--sev-high)',
  schedule: 'var(--color-primary)', manual: 'var(--color-muted)',
}

function fmtMin(sec: number): string {
  const m = Math.round(sec / 60)
  return `${m}м`
}

export function windowSummary(rule: HypercareRule): string {
  const { before_sec, after_sec, mode, interval_sec, clip_len_sec } = rule.window
  const base = `−${fmtMin(before_sec)} … +${fmtMin(after_sec)}`
  if (mode === 'interval' && interval_sec) return `${base} · фото/${fmtMin(interval_sec)}`
  if (clip_len_sec) return `${base} · клип ${clip_len_sec}с`
  return `${base} · непрерыв.`
}

export default function RuleCard({
  rule, onToggle,
}: { rule: HypercareRule; onToggle: (id: string) => void }) {
  const subtitle = rule.trigger.alarm_codes?.join(', ')
    ?? rule.trigger.metric ?? rule.trigger.kind
  return (
    <Card className="p-4 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <span aria-hidden style={{ color: KIND_COLOR[rule.trigger.kind] }}>●</span>
        <span className="font-semibold text-ink">{rule.name}</span>
      </div>
      <div className="text-sm text-muted">
        {KIND_LABEL[rule.trigger.kind]} · {subtitle}
      </div>
      <div className="text-sm text-ink">⏱ {windowSummary(rule)}</div>
      <div className="text-sm text-muted">🎥 кам {rule.cameras.join(', ')}</div>
      <button
        role="switch"
        aria-checked={rule.enabled}
        aria-label={`Переключить правило ${rule.name}`}
        onClick={() => onToggle(rule.id)}
        className={cn(
          'mt-1 self-start rounded-full px-3 py-1 text-xs font-medium',
          rule.enabled ? 'bg-primary text-white' : 'bg-primary-50 text-primary',
        )}
      >
        {rule.enabled ? '● вкл' : '○ выкл'}
      </button>
    </Card>
  )
}
```

```tsx
// web/src/components/hypercare/EvidenceClipStrip.tsx
import { cn } from '@/components/ui/cn'
import type { HypercareEvidenceClip } from '@/api/types'

export default function EvidenceClipStrip({
  items, onOpen,
}: { items: HypercareEvidenceClip[]; onOpen: (clip: HypercareEvidenceClip) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((clip, i) =>
        clip.status === 'available' ? (
          <button
            key={i}
            onClick={() => onOpen(clip)}
            aria-label={`Открыть видео кам ${clip.channel}`}
            className="rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink hover:bg-primary-50"
          >
            ▶ кам {clip.channel}
          </button>
        ) : (
          <div
            key={i}
            className={cn(
              'rounded-md border border-dashed border-border px-3 py-2',
              'text-sm text-muted bg-bg',
            )}
          >
            ⏳ кам {clip.channel} · ETA {clip.eta_sec ?? '—'}с
          </div>
        ),
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/hypercare/`
Expected: PASS (RuleCard 3 + ClipStrip 2)

- [ ] **Step 5: Commit**

```bash
git add web/src/components/hypercare/RuleCard.tsx web/src/components/hypercare/EvidenceClipStrip.tsx web/src/components/hypercare/RuleCard.test.tsx web/src/components/hypercare/EvidenceClipStrip.test.tsx
git commit -m "feat(hypercare): RuleCard и EvidenceClipStrip"
```

---

### Task 8: `EvidenceCard` (карточка результата с раскрытием видео)

**Files:**
- Create: `web/src/components/hypercare/EvidenceCard.tsx`
- Test: `web/src/components/hypercare/EvidenceCard.test.tsx`

**Interfaces:**
- Consumes: `HypercareEvidence` из `@/api/types`; `EvidenceClipStrip` (Task 7); `Card`, `VideoPlayer`, `SeverityBadge`.
- Produces: `EvidenceCard({ evidence }: { evidence: HypercareEvidence })` — управляет локальным состоянием «открытый клип» и рендерит `VideoPlayer`.

- [ ] **Step 1: Write the failing test**

```tsx
// web/src/components/hypercare/EvidenceCard.test.tsx
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, test } from 'vitest'
import EvidenceCard from './EvidenceCard'
import type { HypercareEvidence } from '@/api/types'

const fulfilled: HypercareEvidence = {
  id: 'R-SABOTAGE:a1', rule_id: 'R-SABOTAGE', rule_name: 'Саботаж камеры',
  vehicle_plate: 'А079АМ250', driver: 'Иванов И.', trigger_ts: '2026-05-14T14:23:07',
  trigger_label: 'Саботаж камеры', status: 'fulfilled', items: [
    { channel: 1, kind: 'video', offset_sec: 0, status: 'available', url: '/api/incidents/a1/video/1' },
  ],
}

describe('EvidenceCard', () => {
  test('renders header with plate, driver and status badge', () => {
    render(<EvidenceCard evidence={fulfilled} />)
    expect(screen.getByText(/А079АМ250/)).toBeInTheDocument()
    expect(screen.getByText(/Иванов И\./)).toBeInTheDocument()
    expect(screen.getByText(/fulfilled|Готово/i)).toBeInTheDocument()
  })
  test('opening an available clip mounts a video element', () => {
    const { container } = render(<EvidenceCard evidence={fulfilled} />)
    fireEvent.click(screen.getByRole('button', { name: /кам 1/i }))
    expect(container.querySelector('video')).not.toBeNull()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/hypercare/EvidenceCard.test.tsx`
Expected: FAIL — модуль не найден.

- [ ] **Step 3: Write minimal implementation**

```tsx
// web/src/components/hypercare/EvidenceCard.tsx
import { useState } from 'react'
import { Card, VideoPlayer } from '@/components'
import type { HypercareEvidence, HypercareEvidenceClip } from '@/api/types'
import EvidenceClipStrip from './EvidenceClipStrip'

const STATUS_LABEL: Record<string, string> = {
  fulfilled: 'Готово', partial: 'Частично', pending: 'Ожидание', empty: 'Пусто',
}
const STATUS_COLOR: Record<string, string> = {
  fulfilled: 'var(--sev-ok)', partial: 'var(--sev-warning)',
  pending: 'var(--sev-high)', empty: 'var(--color-muted)',
}

export default function EvidenceCard({ evidence }: { evidence: HypercareEvidence }) {
  const [open, setOpen] = useState<HypercareEvidenceClip | null>(null)
  return (
    <Card className="p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex flex-col">
          <span className="font-semibold text-ink">{evidence.rule_name}</span>
          <span className="text-sm text-muted">
            {evidence.vehicle_plate}
            {evidence.driver ? ` · ${evidence.driver}` : ''} · {evidence.trigger_ts.slice(11, 19)}
          </span>
        </div>
        <span
          className="rounded-full px-2 py-0.5 text-xs font-medium text-white"
          style={{ background: STATUS_COLOR[evidence.status] }}
        >
          {STATUS_LABEL[evidence.status]}
        </span>
      </div>
      <EvidenceClipStrip items={evidence.items} onOpen={setOpen} />
      {open?.url ? (
        <VideoPlayer src={open.url} eventMarkerPct={50} ariaLabel={`Видео кам ${open.channel}`} />
      ) : null}
    </Card>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/hypercare/EvidenceCard.test.tsx`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add web/src/components/hypercare/EvidenceCard.tsx web/src/components/hypercare/EvidenceCard.test.tsx
git commit -m "feat(hypercare): EvidenceCard с раскрытием видео"
```

---

### Task 9: `RuleBuilder` (drawer-степпер)

**Files:**
- Create: `web/src/components/hypercare/RuleBuilder.tsx`
- Test: `web/src/components/hypercare/RuleBuilder.test.tsx`

**Interfaces:**
- Consumes: `HypercareRule`, `HypercareTriggerKind` из `@/api/types`; `windowSummary` из `RuleCard`; `Button`.
- Produces: `RuleBuilder({ onCreate, onClose }: { onCreate: (rule: HypercareRule) => void; onClose: () => void })`.

- [ ] **Step 1: Write the failing test**

```tsx
// web/src/components/hypercare/RuleBuilder.test.tsx
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, test, vi } from 'vitest'
import RuleBuilder from './RuleBuilder'

describe('RuleBuilder', () => {
  test('walks steps and emits a rule on finish', () => {
    const onCreate = vi.fn()
    render(<RuleBuilder onCreate={onCreate} onClose={() => {}} />)
    // ШАГ 1 — триггер по умолчанию event; идём дальше
    fireEvent.click(screen.getByRole('button', { name: /далее/i }))   // → шаг 2 окно
    fireEvent.click(screen.getByRole('button', { name: /далее/i }))   // → шаг 3 камеры
    fireEvent.click(screen.getByRole('button', { name: /далее/i }))   // → шаг 4 имя
    fireEvent.change(screen.getByLabelText(/имя правила/i), { target: { value: 'Тест' } })
    fireEvent.click(screen.getByRole('button', { name: /создать/i }))
    expect(onCreate).toHaveBeenCalledTimes(1)
    const rule = onCreate.mock.calls[0][0]
    expect(rule.name).toBe('Тест')
    expect(rule.trigger.kind).toBeDefined()
    expect(Array.isArray(rule.cameras)).toBe(true)
  })
  test('live preview reflects current window', () => {
    render(<RuleBuilder onCreate={() => {}} onClose={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /далее/i }))   // шаг 2
    expect(screen.getByText(/Превью|получится/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/hypercare/RuleBuilder.test.tsx`
Expected: FAIL — модуль не найден.

- [ ] **Step 3: Write minimal implementation**

```tsx
// web/src/components/hypercare/RuleBuilder.tsx
import { useMemo, useState } from 'react'
import { Button } from '@/components'
import type { HypercareRule, HypercareTriggerKind, HypercareWindowSpec } from '@/api/types'
import { windowSummary } from './RuleCard'

const KINDS: { value: HypercareTriggerKind; label: string }[] = [
  { value: 'event', label: 'Событие аналитики' },
  { value: 'sensor', label: 'Датчик / телеметрия' },
  { value: 'schedule', label: 'Расписание / интервал' },
  { value: 'manual', label: 'Ручной (ad-hoc)' },
]
const CAMERAS: { ch: number; label: string }[] = [
  { ch: 1, label: 'ADAS / Фронт' }, { ch: 5, label: 'DMS / Салон' },
  { ch: 2, label: 'СНЗ / Доп.' }, { ch: 3, label: 'СНЗ / Кузов' },
]

export default function RuleBuilder({
  onCreate, onClose,
}: { onCreate: (rule: HypercareRule) => void; onClose: () => void }) {
  const [step, setStep] = useState(1)
  const [kind, setKind] = useState<HypercareTriggerKind>('event')
  const [window, setWindow] = useState<HypercareWindowSpec>({
    before_sec: 60, after_sec: 120, mode: 'continuous',
  })
  const [cameras, setCameras] = useState<number[]>([1, 5])
  const [name, setName] = useState('')

  const previewRule: HypercareRule = useMemo(() => ({
    id: 'preview', name: name || 'Новое правило', enabled: true, role_scope: 'dispatcher',
    trigger: { kind, alarm_codes: kind === 'event' ? ['CAMERA_TAMPER'] : undefined },
    window, cameras,
  }), [name, kind, window, cameras])

  function toggleCam(ch: number) {
    setCameras((c) => (c.includes(ch) ? c.filter((x) => x !== ch) : [...c, ch]))
  }

  return (
    <div role="dialog" aria-label="Новое правило надзора" className="flex flex-col gap-4 p-4 w-96">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-ink">Новое правило · шаг {step}/4</h2>
        <button aria-label="Закрыть" onClick={onClose} className="text-muted">✕</button>
      </div>

      {step === 1 && (
        <fieldset className="flex flex-col gap-2">
          <legend className="text-sm text-muted">Точка отсчёта</legend>
          {KINDS.map((k) => (
            <label key={k.value} className="flex items-center gap-2 text-ink">
              <input type="radio" name="kind" checked={kind === k.value}
                     onChange={() => setKind(k.value)} />
              {k.label}
            </label>
          ))}
        </fieldset>
      )}

      {step === 2 && (
        <div className="flex flex-col gap-2 text-ink">
          <label className="text-sm">До (сек)
            <input type="number" value={window.before_sec}
                   onChange={(e) => setWindow({ ...window, before_sec: Number(e.target.value) })}
                   className="ml-2 w-24 border border-border rounded px-2" />
          </label>
          <label className="text-sm">После (сек)
            <input type="number" value={window.after_sec}
                   onChange={(e) => setWindow({ ...window, after_sec: Number(e.target.value) })}
                   className="ml-2 w-24 border border-border rounded px-2" />
          </label>
          <div className="mt-2 rounded bg-primary-50 p-2 text-sm text-primary">
            Превью: получится «{windowSummary(previewRule)}»
          </div>
        </div>
      )}

      {step === 3 && (
        <fieldset className="flex flex-col gap-2">
          <legend className="text-sm text-muted">Камеры</legend>
          {CAMERAS.map((c) => (
            <label key={c.ch} className="flex items-center gap-2 text-ink">
              <input type="checkbox" checked={cameras.includes(c.ch)}
                     onChange={() => toggleCam(c.ch)} />
              кам {c.ch} · {c.label}
            </label>
          ))}
        </fieldset>
      )}

      {step === 4 && (
        <label className="flex flex-col gap-1 text-ink text-sm">
          Имя правила
          <input value={name} onChange={(e) => setName(e.target.value)}
                 className="border border-border rounded px-2 py-1" />
        </label>
      )}

      <div className="mt-auto flex justify-between">
        <Button variant="ghost" disabled={step === 1} onClick={() => setStep((s) => s - 1)}>
          Назад
        </Button>
        {step < 4 ? (
          <Button onClick={() => setStep((s) => s + 1)}>Далее →</Button>
        ) : (
          <Button onClick={() => onCreate({
            ...previewRule,
            id: `C-${name || 'rule'}-${cameras.join('')}`,
          })}>Создать</Button>
        )}
      </div>
    </div>
  )
}
```

> NB: `Button` props (`variant`, `disabled`) — сверить с фактическим `web/src/components/ui/Button.tsx`; подставить реальные имена вариантов.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/hypercare/RuleBuilder.test.tsx`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add web/src/components/hypercare/RuleBuilder.tsx web/src/components/hypercare/RuleBuilder.test.tsx
git commit -m "feat(hypercare): конструктор правил RuleBuilder"
```

---

### Task 10: Страница `Hypercare` + интеграция в роутинг и NAV

**Files:**
- Create: `web/src/pages/Hypercare.tsx`
- Create: `web/src/pages/Hypercare.test.tsx`
- Create: `web/src/pages/Hypercare.states.test.tsx`
- Modify: `web/src/App.tsx` (lazy-import + Route + NAV)

**Interfaces:**
- Consumes: `getHypercareRules`, `evaluateHypercare` (Task 5); `HypercareRulesProvider`, `useHypercareRules` (Task 6); `RuleCard`, `RuleBuilder`, `EvidenceCard`; `useRole`.
- Produces: `export default function Hypercare()`; маршрут `/hypercare`.

- [ ] **Step 1: Write the failing tests**

```tsx
// web/src/pages/Hypercare.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { describe, expect, test, vi, beforeEach } from 'vitest'
import { RoleProvider } from '@/state/role'
import * as client from '@/api/client'
import { HYPERCARE_RULES, HYPERCARE_EVIDENCE } from '@/api/fixtures/hypercare'
import Hypercare from './Hypercare'

function renderPage() {
  return render(
    <RoleProvider>
      <BrowserRouter>
        <Hypercare />
      </BrowserRouter>
    </RoleProvider>,
  )
}

describe('Hypercare page', () => {
  beforeEach(() => {
    vi.spyOn(client, 'getHypercareRules').mockResolvedValue(HYPERCARE_RULES)
    vi.spyOn(client, 'evaluateHypercare').mockResolvedValue(HYPERCARE_EVIDENCE)
  })
  test('renders both sections', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/Правила надзора/i)).toBeInTheDocument()
      expect(screen.getByText(/Собранные доказательства/i)).toBeInTheDocument()
    })
  })
  test('renders rule cards and evidence cards', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Саботаж камеры')).toBeInTheDocument())
    expect(screen.getByText(/А079АМ250/)).toBeInTheDocument()
  })
})
```

```tsx
// web/src/pages/Hypercare.states.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { describe, expect, test, vi, beforeEach } from 'vitest'
import { RoleProvider } from '@/state/role'
import * as client from '@/api/client'
import Hypercare from './Hypercare'

function renderPage() {
  return render(
    <RoleProvider><BrowserRouter><Hypercare /></BrowserRouter></RoleProvider>,
  )
}

describe('Hypercare states', () => {
  test('error banner on rules failure', async () => {
    vi.spyOn(client, 'getHypercareRules').mockRejectedValue(new Error('boom'))
    vi.spyOn(client, 'evaluateHypercare').mockResolvedValue([])
    renderPage()
    await waitFor(() => expect(screen.getByText(/Не удалось загрузить/i)).toBeInTheDocument())
  })
  test('empty evidence message', async () => {
    vi.spyOn(client, 'getHypercareRules').mockResolvedValue([])
    vi.spyOn(client, 'evaluateHypercare').mockResolvedValue([])
    renderPage()
    await waitFor(() => expect(screen.getByText(/срабатываний нет/i)).toBeInTheDocument())
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/pages/Hypercare.test.tsx src/pages/Hypercare.states.test.tsx`
Expected: FAIL — модуль `./Hypercare` не найден.

- [ ] **Step 3: Write minimal implementation**

```tsx
// web/src/pages/Hypercare.tsx
import { useEffect, useState } from 'react'
import * as client from '@/api/client'
import type { HypercareEvidence } from '@/api/types'
import { useRole } from '@/state/role'
import {
  HypercareRulesProvider, useHypercareRules,
} from '@/state/hypercareRules'
import RuleCard from '@/components/hypercare/RuleCard'
import RuleBuilder from '@/components/hypercare/RuleBuilder'
import EvidenceCard from '@/components/hypercare/EvidenceCard'
import { Button } from '@/components'

function HypercareInner() {
  const { role } = useRole()
  const { rules, toggleRule, addRule, setSeed } = useHypercareRules()
  const [evidence, setEvidence] = useState<HypercareEvidence[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [builderOpen, setBuilderOpen] = useState(false)

  useEffect(() => {
    let alive = true
    client.getHypercareRules()
      .then((seed) => { if (alive) setSeed(seed) })
      .catch(() => { if (alive) setError('Не удалось загрузить правила') })
    return () => { alive = false }
  }, [setSeed])

  useEffect(() => {
    if (rules.length === 0) { setEvidence([]); return }
    let alive = true
    client.evaluateHypercare(rules.filter((r) => r.enabled), role)
      .then((e) => { if (alive) setEvidence(e) })
      .catch(() => { if (alive) setError('Не удалось загрузить доказательства') })
    return () => { alive = false }
  }, [rules, role])

  return (
    <div className="flex flex-col gap-6 p-6">
      <header>
        <h1 className="text-xl font-bold text-ink">🛡 Гиперопека</h1>
        <p className="text-muted">Плановый и триггерный фотоконтроль транспорта</p>
      </header>

      {error && (
        <div className="rounded border border-border bg-sev-critical-bg p-3 text-sev-critical-text">
          {error} · <button className="underline" onClick={() => location.reload()}>Повторить</button>
        </div>
      )}

      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-ink">Правила надзора</h2>
          <Button onClick={() => setBuilderOpen(true)}>+ Новое правило</Button>
        </div>
        {rules.length === 0 ? (
          <p className="text-muted">Нет правил надзора.
            <button className="ml-1 underline text-primary" onClick={() => setBuilderOpen(true)}>
              Создать первое правило
            </button>
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {rules.map((r) => <RuleCard key={r.id} rule={r} onToggle={toggleRule} />)}
          </div>
        )}
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-semibold text-ink">Собранные доказательства</h2>
        {evidence === null ? (
          <p className="text-muted">Загрузка…</p>
        ) : evidence.length === 0 ? (
          <p className="text-muted">За выбранный период срабатываний нет.</p>
        ) : (
          <div className="flex flex-col gap-3">
            {evidence.map((e) => <EvidenceCard key={e.id} evidence={e} />)}
          </div>
        )}
      </section>

      {builderOpen && (
        <div className="fixed inset-0 bg-black/30 flex justify-end z-50">
          <div className="bg-surface h-full shadow-xl">
            <RuleBuilder
              onCreate={(rule) => { addRule(rule); setBuilderOpen(false) }}
              onClose={() => setBuilderOpen(false)}
            />
          </div>
        </div>
      )}
    </div>
  )
}

export default function Hypercare() {
  return (
    <HypercareRulesProvider>
      <HypercareInner />
    </HypercareRulesProvider>
  )
}
```

App.tsx — три точечные правки (подставить рядом с существующими аналогами):

```tsx
// 1) рядом с другими lazy-import (≈ строка 273)
const Hypercare = lazy(() => import('@/pages/Hypercare'))

// 2) в AppRoutes(), внутри <Route element={<AppShell />}> (≈ строка 320)
<Route path="/hypercare" element={
  <Suspense fallback={<Placeholder title="Загрузка…" />}><Hypercare /></Suspense>
} />

// 3) в NAV, в группе 'Мониторинг' items (≈ строка 70) — взять подходящую иконку из lucide-react (напр. Eye)
{ to: '/hypercare', label: 'Гиперопека', icon: Eye },
```

> NB: `Placeholder`, импорт иконок — использовать фактические из `App.tsx`. Иконку `Eye` добавить в существующий `import { ... } from 'lucide-react'`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/pages/Hypercare.test.tsx src/pages/Hypercare.states.test.tsx`
Expected: PASS (4 passed)

- [ ] **Step 5: Verify routing builds**

Run: `cd web && npx tsc --noEmit`
Expected: без ошибок типов в новых файлах.

- [ ] **Step 6: Commit**

```bash
git add web/src/pages/Hypercare.tsx web/src/pages/Hypercare.test.tsx web/src/pages/Hypercare.states.test.tsx web/src/App.tsx
git commit -m "feat(hypercare): страница Гиперопека + роут и пункт NAV"
```

---

## Барьер волны (Opus 🔴)

После Task 10 — гейт качества (методология §5):

- [ ] `§0 GUARD` — нет незакоммиченных файлов; все 10 задач закоммичены отдельно.
- [ ] `§1` — `.venv/bin/pytest api/tests/test_hypercare_api.py` зелёный; `cd web && npx vitest run` зелёный; `npx tsc --noEmit` чисто; ruff/mypy по проекту.
- [ ] `§2` — новые эндпоинты: 200 + схема + негатив (422 на кривое правило/канал; `[]` на пусто).
- [ ] `§3` — детерминизм (повтор `POST /evidence` идентичен); офлайн `VITE_USE_FIXTURES=true` рендерит экран без 5xx.
- [ ] `§4` — loading / empty / error присутствуют; консоль чистая; a11y (switch, dialog, aria-label у клипов).
- [ ] `§5` — ff-merge в main + `grace refresh` (если GRACE-граф ведётся).

---

## Self-review (выполнено при написании плана)

**Покрытие спеки:** §4 модель → Task 1; §5 API (3 эндпоинта + эвалюатор + слои) → Tasks 2–4; §6 UI (страница + 4 компонента + provider + типы/клиент/фикстуры + роутинг/NAV) → Tasks 5–10; §8 состояния → Task 10 (states-тесты); §9 верификация → тесты в каждой задаче; §7 цветокодинг → Task 7 (RuleCard KIND_COLOR), Task 8 (STATUS_COLOR).

**Заметки о реальных идентификаторах:** в Tasks 5/9/10 исполнителю явно предписано сверить фактические имена (`fetchJson`/`USE_FIXTURES`, props `Button`, `Placeholder`, иконки) с существующими файлами перед правкой — это снимает риск рассинхрона с кодовой базой.

**Тип-консистентность:** домен (Task 1) ↔ TS-типы (Task 5) ↔ фикстуры (Task 5) ↔ компоненты (Tasks 7–10) используют единые имена полей (`trigger.kind`, `window.before_sec`, `items[].status/url/eta_sec`, `evidence.status`). Эвалюатор-статусы (`fulfilled/partial/pending/empty`) совпадают с `STATUS_LABEL/STATUS_COLOR`.

**Sensor/schedule в MVP:** эвалюатор для sensor/schedule без `alarm_codes` пропускает срабатывания (нет интеграции телеметрии в первой волне) — это осознанная граница MVP, отражена в спеке §5 и комментарии сервиса. Seed-правила R-FUEL/R-IGNITION присутствуют в каталоге (видны/редактируемы), но доказательства по ним появятся после расширения эвалюатора (вне scope этой волны).
