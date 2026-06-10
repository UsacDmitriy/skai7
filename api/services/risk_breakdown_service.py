"""Сервис explainability — декомпозиция `risk_score` инцидента (§8.8, идея #19).

Раскладывает итоговый `risk_score` (§2) на абсолютные вклады слагаемых в очках
0..100 для waterfall-визуализации (`f20`). **Сумма вкладов == risk_score** того же
инцидента из `/api/incidents/{id}`.

Принципы:
  - **Не копируем формулу.** Веса и коэффициенты импортируются из
    `api/core/enrichment.py` (`RISK_TERM_WEIGHTS`, `risk_term_coeffs`) — дрейф ловит
    tu-riskbreakdown.
  - **Не пересчитываем входы.** Берём уже обогащённый инцидент через
    `incidents_service.get_detail` (severity / speed_kmh / speed_limit_kmh / is_night /
    events_last_7d / risk_score) → те же числа, что и в карточке → точное равенство.
  - `weather_bonus` — надбавка b17 (§8.2) в очках score: `weather_risk_bonus()` даёт
    сырой коэффициент {0, 0.1, 0.2} ДО ·100. Карточка инцидента считает risk_score без
    погодного кэша → для совместимости и инварианта суммы здесь `weather_bonus = 0.0`.
  - Детерминированно, без ML/сети.
"""

from __future__ import annotations

import duckdb
from pydantic import BaseModel, Field

from api.core import enrichment
from api.services import incidents_service


class RiskBreakdown(BaseModel):
    """Плоская декомпозиция риска (§8.8 + prep-тип `web/src/api/types.ts:738`).

    Вклады — в очках score (уже умножены на веса §2); сумма == `total_risk_score`.
    НЕ массив `components[]`.
    """

    id: str
    severity_w: float = Field(ge=0)
    speed_ratio: float = Field(ge=0)
    night: float = Field(ge=0)
    freq_w: float = Field(ge=0)
    weather_bonus: float = Field(ge=0)
    total_risk_score: int = Field(ge=0, le=100)


def breakdown(
    db: duckdb.DuckDBPyConnection, incident_id: str
) -> RiskBreakdown | None:
    """Декомпозиция `risk_score` инцидента или None, если инцидент не найден (→ 404).

    Зеркалит формулу §2/§8.2: каждый слагаемый — абсолютный вклад в очках 0..100.
    `total_risk_score = кламп(round(Σ вкладов))` и равен `risk_score` той же карточки.
    """
    detail = incidents_service.get_detail(db, incident_id)
    if detail is None:
        return None

    coeffs = enrichment.risk_term_coeffs(
        detail.severity,
        detail.speed_kmh,
        detail.speed_limit_kmh,
        detail.is_night,
        detail.events_last_7d,
    )
    weights = enrichment.RISK_TERM_WEIGHTS

    # Абсолютные вклады в очках score: 100 · вес · коэффициент.
    severity_w = 100.0 * weights["severity_w"] * coeffs["severity_w"]
    speed_ratio = 100.0 * weights["speed_ratio"] * coeffs["speed_ratio"]
    night = 100.0 * weights["night"] * coeffs["night"]
    freq_w = 100.0 * weights["freq_w"] * coeffs["freq_w"]

    # weather_bonus в очках: сырой коэффициент (§8.2) · 100. Без кэша → 0.0,
    # как и в risk_score карточки → инвариант суммы сохраняется.
    weather_bonus = 100.0 * enrichment.weather_risk_bonus(None, None)

    total = max(
        0,
        min(100, round(severity_w + speed_ratio + night + freq_w + weather_bonus)),
    )

    return RiskBreakdown(
        id=incident_id,
        severity_w=severity_w,
        speed_ratio=speed_ratio,
        night=night,
        freq_w=freq_w,
        weather_bonus=weather_bonus,
        total_risk_score=total,
    )
