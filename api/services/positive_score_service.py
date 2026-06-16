"""Сервис позитивного скоринга — green zone (§13.1).

Детерминированная агрегация существующих алармов в признание хорошего вождения
(паттерн Netradyne GreenZone, §13.0): без AI/сети, без `now()`/random. Формулы
зафиксированы контрактом §13.1 — веса НЕ изобретаются здесь.

Источники:
  * сырые алармы `video_events__selected_video_alarms` (`"Begin"`, `"UnitStateNumber"`,
    `"Speed"`, `"Type"`);
  * `alarm_type_catalog` — канонический `code` (HARSH_*) и `severity` (critical),
    тот же маппинг, что использует `v_incidents` (§1.3) — переиспользуем, не изобретаем;
  * лимит скорости — `enrichment.speed_limit_for` (ИМПОРТ, таблицу лимитов не копируем);
  * `driver_reference` (§7.1) — связь с водителем: `plate` не из справочника → None (404).
"""

from __future__ import annotations

from typing import Optional

import duckdb

from api.core.enrichment import speed_limit_for
from api.domain.positive import PositiveScore
from api.repositories import rows_to_dicts


def _is_known_plate(db: duckdb.DuckDBPyConnection, plate: str) -> bool:
    """ТС присутствует в `driver_reference` (§13.1: иначе 404)."""
    row = db.execute(
        'SELECT 1 FROM "driver_reference" WHERE "vehicle_plate" = ? LIMIT 1',
        [plate],
    ).fetchone()
    return row is not None


def _total_days(db: duckdb.DuckDBPyConnection) -> int:
    """COUNT(DISTINCT date(`"Begin"`)) по ВСЕМ алармам датасета (§13.1, не хардкод)."""
    row = db.execute(
        'SELECT COUNT(DISTINCT CAST("Begin" AS DATE)) '
        'FROM "video_events__selected_video_alarms"'
    ).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def _alarm_rows(db: duckdb.DuckDBPyConnection, plate: str) -> list[dict]:
    """Алармы ТС с каноническим `code`/`severity` (join `alarm_type_catalog`).

    `code`/`severity` берём из того же справочника, что и `v_incidents` (§1.3),
    чтобы HARSH_*-классификация и critical-severity не разошлись с инцидентами.
    """
    return rows_to_dicts(
        db.execute(
            'SELECT a."Type" AS "alarm_type", '
            'CAST(a."Speed" AS DOUBLE) AS "speed_kmh", '
            'CAST(a."Begin" AS DATE) AS "day", '
            'c."code" AS "alarm_code", c."severity" AS "severity" '
            'FROM "video_events__selected_video_alarms" a '
            'LEFT JOIN "alarm_type_catalog" c ON c."raw" = a."Type" '
            'WHERE a."UnitStateNumber" = ?',
            [plate],
        )
    )


def score(db: duckdb.DuckDBPyConnection, plate: str) -> Optional[PositiveScore]:
    """Позитивный скоринг ТС (§13.1). `plate` не из `driver_reference` → None (404).

    ТС без алармов: ratios `1.0`, `clean_days == total_days`, высокий positive,
    `green_zone` если нет critical (§13.4). Деление на ноль исключено.
    """
    if not _is_known_plate(db, plate):
        return None  # роутер → 404 (§13.1)

    total_days = _total_days(db)
    rows = _alarm_rows(db, plate)
    n = len(rows)

    # clean_days = total_days − дни, в которые у этого ТС были алармы (§13.1).
    alarm_days = {r["day"] for r in rows}
    clean_days = total_days - len(alarm_days)

    # compliant_events_ratio: доля алармов с Speed ≤ speed_limit_for(Type);
    # пустая/нечисловая Speed → аларм вне знаменателя; пустой знаменатель → 1.0 (§13.1).
    compliant_num = 0
    compliant_den = 0
    harsh = 0
    has_critical = False
    for r in rows:
        speed = r["speed_kmh"]
        if speed is not None:
            compliant_den += 1
            if speed <= speed_limit_for(r["alarm_type"] or ""):
                compliant_num += 1
        code = r["alarm_code"] or ""
        if code.startswith("HARSH_"):
            harsh += 1
        if (r["severity"] or "") == "critical":
            has_critical = True

    compliant_ratio = compliant_num / compliant_den if compliant_den else 1.0

    # harsh_free_ratio = 1 − доля HARSH_*-алармов; 0 алармов → 1.0 (§13.1).
    harsh_free_ratio = 1.0 - harsh / n if n else 1.0

    # positive_score: компоненты — float без промежуточных округлений; итог —
    # clamp(round(сумма), 0, 100) (§13.0). total_days==0 (пустой датасет) → доля 1.0.
    clean_ratio = clean_days / total_days if total_days else 1.0
    raw = 100.0 * (
        0.5 * compliant_ratio + 0.3 * clean_ratio + 0.2 * harsh_free_ratio
    )
    positive_score = max(0, min(100, round(raw)))

    # green_zone = compliant ≥ 0.95 И нет critical-алармов ТС (§13.1).
    green_zone = compliant_ratio >= 0.95 and not has_critical

    return PositiveScore(
        vehicle_plate=plate,
        period_days=total_days,
        total_days=total_days,
        clean_days=clean_days,
        compliant_events_ratio=round(compliant_ratio, 2),
        harsh_free_ratio=round(harsh_free_ratio, 2),
        positive_score=positive_score,
        green_zone=green_zone,
    )
