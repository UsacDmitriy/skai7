"""Сервис единого рейтинга водителя — бленд риска и позитива (§13.2).

Честное сравнение водителей одним числом 0..100 (видео+телематика). Формулы
зафиксированы контрактом §13.2 — веса НЕ изобретаются здесь; компоненты — float
без промежуточных округлений, итог округляется ОДИН раз в конце (урок b27, §13.0).
Всё детерминировано (§13.0): без AI/сети, без `now()`/random.

Источники (ничего не пересчитываем заново):
  * `avg_risk_score` — средний `risk_score` инцидентов ТС **из готового
    `incidents_service`** (`v_incidents` + enrichment §2). Формулу §2 НЕ копируем;
  * `positive_score`/`green_zone` — **вызов сервиса b33** (`positive_score_service`),
    не дублирование расчёта §13.1;
  * `driver_reference` (§7.1) — ВСЕ ТС лидерборда и связь с водителем; `plate` не из
    справочника → None (404).
"""

from __future__ import annotations

import math
from typing import Optional

import duckdb

from api.domain.driver_score import DriverScore
from api.repositories import rows_to_dicts
from api.services import incidents_service, positive_score_service

# Бленд §13.2 — веса зафиксированы контрактом, здесь не изобретаются.
_RISK_WEIGHT = 0.6
_POSITIVE_WEIGHT = 0.4

# Все алармы одного ТС за период (датасет мал, §13.0); снимаем дефолтный LIMIT
# репозитория, чтобы средний risk_score считался по ВСЕМ инцидентам, а не по странице.
_ALL = 1_000_000


def _round_half_up(x: float) -> int:
    """Округление к ближайшему, полушаг — от нуля (как jq `round` в Check §13.2).

    Компоненты бленда неотрицательны (`avg_risk_score ≤ 100`, `positive_score ≥ 0`),
    поэтому `floor(x + 0.5)` совпадает с округлением «от нуля» и инвариант
    `round(risk_component + positive_component)` проверяется один-в-один.
    """
    return math.floor(x + 0.5)


def _clamp(value: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, value))


def _driver_lookup(db: duckdb.DuckDBPyConnection) -> dict[str, dict]:
    """`vehicle_plate -> {driver_id, driver_name}` из `driver_reference` (§7.1)."""
    rows = rows_to_dicts(
        db.execute(
            'SELECT "vehicle_plate", "driver_id", "driver_name" FROM "driver_reference"'
        )
    )
    return {r["vehicle_plate"]: r for r in rows}


def _avg_risk_score(db: duckdb.DuckDBPyConnection, plate: str) -> float:
    """Средний `risk_score` инцидентов ТС из готовых данных (§2, не пересчёт).

    Берём уже обогащённые сводки `incidents_service` (там `risk_score` уже посчитан
    формулой §2) и усредняем — формулу §2 НЕ копируем. Нет алармов → `0.0` (§13.4).
    """
    summaries = incidents_service.list_summaries(
        db, {"vehicle_plate": plate, "limit": _ALL}
    )
    if not summaries:
        return 0.0
    return sum(s.risk_score for s in summaries) / len(summaries)


def _build(db: duckdb.DuckDBPyConnection, plate: str, driver: dict) -> DriverScore:
    """Собирает `DriverScore` одного ТС (§13.2). `driver` — строка `driver_reference`."""
    avg_risk_score = _avg_risk_score(db, plate)

    # positive_score — вызов b33 (НЕ дублирование §13.1). plate из driver_reference,
    # поэтому сервис b33 не вернёт None; на всякий случай — fallback 0/нет green_zone.
    positive = positive_score_service.score(db, plate)
    positive_score = positive.positive_score if positive is not None else 0
    green_zone = positive.green_zone if positive is not None else False

    # Компоненты — float без промежуточных округлений; округляем ОДИН раз итог (§13.0).
    risk_component = _RISK_WEIGHT * (100.0 - avg_risk_score)
    positive_component = _POSITIVE_WEIGHT * positive_score
    unified_score = _clamp(_round_half_up(risk_component + positive_component))

    return DriverScore(
        vehicle_plate=plate,
        driver_id=driver.get("driver_id", ""),
        driver_name=driver.get("driver_name", ""),
        unified_score=unified_score,
        risk_component=risk_component,
        positive_component=positive_component,
        avg_risk_score=avg_risk_score,
        positive_score=positive_score,
        green_zone=green_zone,
    )


def score(db: duckdb.DuckDBPyConnection, plate: str) -> Optional[DriverScore]:
    """Единый рейтинг ТС (§13.2). `plate` не из `driver_reference` → None (404)."""
    driver = _driver_lookup(db).get(plate)
    if driver is None:
        return None  # роутер → 404 (§13.2)
    return _build(db, plate, driver)


def leaderboard(db: duckdb.DuckDBPyConnection) -> list[DriverScore]:
    """Лидерборд ВСЕХ ТС из `driver_reference` (включая без алармов, §13.2).

    Сортировка `unified_score` desc, тай-брейк `vehicle_plate` asc — стабильность
    и детерминизм (§13.4): повторные вызовы дают идентичный порядок.
    """
    drivers = _driver_lookup(db)
    scores = [_build(db, plate, driver) for plate, driver in drivers.items()]
    scores.sort(key=lambda s: (-s.unified_score, s.vehicle_plate))
    return scores
