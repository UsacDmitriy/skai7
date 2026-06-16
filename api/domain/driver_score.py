"""Схема домена единого рейтинга водителя (контракт §13.2).

Честное сравнение водителей одним числом 0..100: бленд риска (§2, видео+телематика)
и позитива (§13.1). Прозрачность бленда — в ответе видны обе компоненты и их входы
(`avg_risk_score`/`positive_score`/`green_zone`), чтобы число можно было проверить.
Всё детерминировано (§13.0) — без AI/сети. Имена полей — дословно §13.2; общий
`entities.py` не трогаем (кросс-трек гонки).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DriverScore(BaseModel):
    """Единый рейтинг ТС/водителя (§13.2) — элемент лидерборда и ответ по plate.

    `unified_score = clamp(round(risk_component + positive_component), 0, 100)`, где
    `risk_component = 0.6·(100 − avg_risk_score)` и `positive_component = 0.4·positive_score`
    (компоненты — float без промежуточных округлений, итог округляется один раз, §13.0).
    `avg_risk_score` — средний `risk_score` инцидентов ТС (§2, не пересчёт); нет алармов → `0.0`.
    `positive_score`/`green_zone` — из сервиса позитивного скоринга (§13.1).
    """

    model_config = ConfigDict(extra="forbid")

    vehicle_plate: str
    driver_id: str
    driver_name: str
    unified_score: int
    risk_component: float
    positive_component: float
    avg_risk_score: float
    positive_score: int
    green_zone: bool
