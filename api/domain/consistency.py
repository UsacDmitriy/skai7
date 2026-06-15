"""Схемы домена consistency (контракт §10.2) — слой доверия к данным (Волна 4.4).

`ConsistencyCheck` — результат одной детерминированной проверки целостности;
`ConsistencyReport` — агрегат всех 7 проверок + сводные доли доверия. Это НЕ
AI-фича (§10.0): без `AiFeatureState`/`ai_flags`, без сети — чистый SQL поверх DuckDB.

b5 — владелец `api/domain/*`; b28 добавляет эти схемы аддитивно (§10.6).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ConsistencyCheck(BaseModel):
    """Одна проверка консистентности (§10.2).

    `ratio = affected_count/total ∈ [0,1]` (total=0 → 0.0); статус считает СЕРВИС
    (§10.2): `fail` если ratio > 0.2, `warn` если ratio > 0, иначе `ok`.
    `sample_ids` — до 5 примеров (id аларма или госномер) для drill-down фронта.
    """

    check_id: str
    title_ru: str
    status: Literal["ok", "warn", "fail"]
    affected_count: int = Field(ge=0)
    total: int = Field(ge=0)
    ratio: float = Field(ge=0.0, le=1.0)
    sample_ids: list[str] = Field(default_factory=list, max_length=5)
    description_ru: str


class ConsistencyReport(BaseModel):
    """Агрегат всех проверок консистентности (§10.2).

    `evidence_rate = 1 − ratio(incident_no_video)` — доля алармов с видео-доказательством;
    `speed_agreement_rate = 1 − ratio(speed_disagreement)` — согласие скоростей видео↔GPS.
    `generated_at_source` фиксирован как `'duckdb'`: источник — материализованные таблицы.
    """

    checks: list[ConsistencyCheck]
    evidence_rate: float = Field(ge=0.0, le=1.0)
    speed_agreement_rate: float = Field(ge=0.0, le=1.0)
    generated_at_source: Literal["duckdb"] = "duckdb"
