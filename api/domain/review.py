"""Схемы домена review-queue (контракт §11.2).

Статусная модель верификации инцидента: `pending|validated|dismissed`. Источник
истины статуса — журнал `output/review_queue.csv` (§11.0), не отдельная таблица.
Имена полей — дословно по §11.2; общий `entities.py` не трогаем (кросс-трек гонки).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from api.domain.common import Severity

# Статус ревью (§11.0): нет решения → pending; решение перезаписываемо.
ReviewStatus = Literal["pending", "validated", "dismissed"]
# Допустимое решение POST (§11.1): pending выставить нельзя — это «нет решения».
ReviewDecision = Literal["validated", "dismissed"]


class ReviewItem(BaseModel):
    """Строка очереди верификации (§11.2): инцидент + его статус ревью."""

    model_config = ConfigDict(extra="forbid")

    incident_id: str
    alarm_code: str
    severity: Severity
    vehicle_plate: str
    ts: str
    video_available: bool
    status: ReviewStatus
    note: str | None = None
    decided_at: str | None = None


class ReviewCounts(BaseModel):
    """Счётчики по статусам (§11.2): сумма = всего инцидентов в `v_incidents`."""

    pending: int
    validated: int
    dismissed: int


class ReviewQueue(BaseModel):
    """Ответ GET /api/review-queue (§11.2): инциденты + счётчики + контекст доверия."""

    items: list[ReviewItem]
    counts: ReviewCounts
    evidence_rate: float
