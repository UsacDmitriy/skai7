"""Схемы домена Hypercare (Гиперопека).

Правило надзора = триггер → окно → частота → камеры. Эвалюатор stateless:
правила приходят в теле POST /evidence. Имена полей snake_case.
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
