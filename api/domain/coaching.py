"""Схемы домена Coaching Loop (контракт §12.3).

Цикл обучения водителя Оздоева: инцидент → курс → тест (порог 18/20) →
KPI прохождения + повторных нарушений. **Данные синтетические** (§12.0):
`CoachingCard` несёт литерал `synthetic: true`, UI обязан это показывать.
Имена полей — дословно §12.3; общий `entities.py` не трогаем (кросс-трек гонки).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

# Статус назначения (§12.3) — вычисляется в сервисе, не хранится в таблице:
# passed (passed=true) · failed (completed_at есть, passed=false) · incomplete (completed_at пуст).
CoachingStatus = Literal["passed", "failed", "incomplete"]


class CoachingAssignment(BaseModel):
    """Назначение курса по инциденту (§12.3)."""

    model_config = ConfigDict(extra="forbid")

    assignment_id: str
    incident_id: str
    course_id: str
    course_title_ru: str
    assigned_at: str
    due_at: str
    test_score: int
    status: CoachingStatus
    completed_at: str | None = None
    repeat_within_30d: bool


class CoachingKpi(BaseModel):
    """KPI цикла обучения (§12.3) — все доли ∈ [0,1].

    completion = с `completed_at`/всего; pass = passed/завершивших (0 завершивших → 0.0);
    repeat = с `repeat_within_30d`/всего.
    """

    model_config = ConfigDict(extra="forbid")

    completion_rate: float
    pass_rate: float
    repeat_violation_rate: float


class CoachingSummary(BaseModel):
    """Сводка по водителю (§12.3) — строка `GET /api/coaching`."""

    model_config = ConfigDict(extra="forbid")

    vehicle_plate: str
    driver_id: str
    driver_name: str
    total: int
    kpi: CoachingKpi


class CoachingCard(BaseModel):
    """Карточка водителя (§12.3) — ответ `GET /api/coaching/{plate}`.

    `synthetic` — литерал `true` (честность §12.0): датасета обучения не существует.
    """

    model_config = ConfigDict(extra="forbid")

    vehicle_plate: str
    driver_id: str
    driver_name: str
    assignments: list[CoachingAssignment]
    kpi: CoachingKpi
    synthetic: Literal[True] = True
