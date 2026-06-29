"""Сервис Hypercare: seed-каталог правил + stateless детерминированный эвалюатор.

Для event-правил берём инциденты с подходящими alarm_code; если в video_files
есть реальные клипы по запрошенным каналам → fulfilled; иначе pending с ETA.
Sensor/schedule-правила без alarm_codes — MVP-заглушка (пропуск).
Никакого Date.now()/random: ETA из hashlib по (rule_id, plate, ts).
"""
from __future__ import annotations

import hashlib

import duckdb

from api.domain.hypercare import (
    EvidenceClip,
    HypercareEvidence,
    HypercareRule,
    ManualRequest,
    TriggerSpec,
    WindowSpec,
)
from api.repositories import hypercare_repo


def _eta_for(rule_id: str, plate: str, ts: str) -> int:
    """Детерминированная ETA (30..150 с) из устойчивого хеша."""
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
        rule(
            "R-SABOTAGE", "Саботаж камеры", "security",
            TriggerSpec(kind="event", alarm_codes=["CAMERA_TAMPER"]),
            WindowSpec(before_sec=300, after_sec=120, mode="continuous"),
            [1, 5, 2, 3],
        ),
        rule(
            "R-SUBST", "Подмена водителя", "security",
            TriggerSpec(kind="event", alarm_codes=["DRIVER_SUBSTITUTION"]),
            WindowSpec(before_sec=0, after_sec=900, mode="interval", interval_sec=300),
            [5],
        ),
        rule(
            "R-CRASH", "Удар / ДТП", "dispatcher",
            TriggerSpec(kind="event", alarm_codes=["CRASH_SENSOR"]),
            WindowSpec(before_sec=10, after_sec=30, mode="continuous"),
            [1, 5, 2, 3],
        ),
        rule(
            "R-FUEL", "Слив топлива", "security",
            TriggerSpec(
                kind="sensor", metric="fuel_drop", op="lte",
                threshold=-10.0, window_sec=60,
            ),
            WindowSpec(before_sec=60, after_sec=120, mode="continuous", clip_len_sec=15),
            [1, 3],
        ),
        rule(
            "R-IGNITION", "Предрейс-контроль", "dispatcher",
            TriggerSpec(kind="sensor", metric="ignition_on"),
            WindowSpec(before_sec=0, after_sec=300, mode="interval", interval_sec=60),
            [5],
        ),
        rule(
            "R-MANUAL", "Ручной запрос", "dispatcher",
            TriggerSpec(kind="manual"),
            WindowSpec(before_sec=60, after_sec=120, mode="continuous"),
            [1, 5],
        ),
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
            continue
        codes = rule.trigger.alarm_codes or []
        if not codes:
            continue  # sensor/schedule без event-кодов — MVP-заглушка
        for inc in hypercare_repo.incidents_for_codes(db, codes):
            items, status = _clips_for(db, inc["id"], list(rule.cameras))
            out.append(HypercareEvidence(
                id=f"{rule.id}:{inc['id']}",
                rule_id=rule.id,
                rule_name=rule.name,
                vehicle_plate=inc["vehicle_plate"],
                driver=inc.get("driver"),
                trigger_ts=inc["ts"],
                trigger_label=inc.get("alarm_label_ru", rule.name),
                status=status,
                items=items,
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
        rule_id="R-MANUAL",
        rule_name="Ручной запрос",
        vehicle_plate=req.vehicle_plate,
        driver=None,
        trigger_ts=req.trigger_ts,
        trigger_label="Ручной запрос",
        status="pending",
        items=items,
    )
