"""Схема домена позитивного скоринга (контракт §13.1).

Признание хорошего вождения Оздоева (паттерн Netradyne GreenZone): чистые дни,
соблюдение лимитов, отсутствие резких манёвров, бейдж «зелёной зоны». Всё
детерминировано из существующих алармов (§13.0) — без AI/сети. Имена полей —
дословно §13.1; общий `entities.py` не трогаем (кросс-трек гонки).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PositiveScore(BaseModel):
    """Позитивный скоринг ТС (§13.1) — ответ `GET /api/positive-score/{plate}`.

    `period_days` дублирует `total_days` — поле для UI-дисклеймера «за период N дн.»
    (честность §13.0: датасет покрывает мало дней). Доли ∈ [0,1]; `positive_score` ∈
    [0,100]; `green_zone` — `compliant_events_ratio ≥ 0.95` И нет critical-алармов.
    """

    model_config = ConfigDict(extra="forbid")

    vehicle_plate: str
    period_days: int
    total_days: int
    clean_days: int
    compliant_events_ratio: float
    harsh_free_ratio: float
    positive_score: int
    green_zone: bool
