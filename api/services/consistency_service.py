"""Сервис консистентности данных (§10.0–§10.3) — `GET /api/consistency`.

Слой доверия к данным (кейсы Фомина/Маслова): 7 детерминированных кросс-датасетных
проверок целостности поверх view `v_consistency_checks` (b28). Это НЕ AI-фича —
без сети/ML, без `AiFeatureState`. Повторный вызов → байт-идентичный ответ.

Разделение ответственности (§10.2):
  - `v_consistency_checks` (SQL) отдаёт только сырьё: `check_id, affected_count, total`.
  - Статусы (`ok`/`warn`/`fail`) и `ratio` считает ЗДЕСЬ сервис, не SQL.
  - `title_ru`/`description_ru` — фиксированный словарь в коде (детерминизм, без БД).
  - `sample_ids` (≤5) — отдельные лёгкие запросы с `ORDER BY` (стабильность примеров).

Тоталы не хардкодим (§10.0) — считаются запросом; пустая таблица-источник → total=0,
ratio=0, status=ok (деградация без 5xx).
"""

from __future__ import annotations

import duckdb

from api.domain.consistency import ConsistencyCheck, ConsistencyReport
from api.repositories import rows_to_dicts

# Фиксированный словарь метаданных проверок (§10.3) — порядок = канонические 7 проверок.
# Держим title/description в коде (а не в SQL) ради детерминизма и единого места правок.
_CHECK_META: dict[str, dict[str, str]] = {
    "video_fleet_no_track": {
        "title_ru": "ТС без точек трека",
        "description_ru": "Госномера из видео-алармов без единой строки в телеметрии — слепые зоны GPS",
    },
    "incident_no_video": {
        "title_ru": "Инциденты без видео",
        "description_ru": "Алармы с VideoCount > 0, но без видеофайлов — пробел доказательной базы (кейс Фомина)",
    },
    "terminal_duplication": {
        "title_ru": "Дубли терминалов на ТС",
        "description_ru": "ТС с более чем одним TerminalId — источник дублей на карте (кейс Балтики)",
    },
    "plate_match_coverage": {
        "title_ru": "Покрытие справочника госномеров",
        "description_ru": "Строки справочника без статуса matched — несведённые ТС между источниками",
    },
    "timestamp_monotonicity": {
        "title_ru": "Порядок точек трека",
        "description_ru": "Алармы, где время убывает при росте индекса точки — битый порядок телеметрии",
    },
    "coordinate_sanity": {
        "title_ru": "Валидность координат",
        "description_ru": "Пустые / вне диапазона ±90/±180 / (0,0) координаты в алармах и точках трека",
    },
    "speed_disagreement": {
        "title_ru": "Расхождение скоростей",
        "description_ru": "Алармы с major-расхождением скорости видео↔GPS-трек (источник истины — GPS)",
    },
}

# Запросы примеров (≤5) на каждую проверку. ORDER BY обязателен — детерминизм ответа.
# speed_disagreement — заглушка до b29 (нет v_speed_check) → примеров нет.
_SAMPLE_SQL: dict[str, str] = {
    "video_fleet_no_track": """
        SELECT a.usn AS sample
        FROM (SELECT DISTINCT "UnitStateNumber" AS usn
              FROM video_events__selected_video_alarms) a
        LEFT JOIN (SELECT DISTINCT unit_state_number
                   FROM video_events__track_points) tp
          ON a.usn = tp.unit_state_number
        WHERE tp.unit_state_number IS NULL
        ORDER BY a.usn
        LIMIT 5
    """,
    "incident_no_video": """
        SELECT CAST(a."AlarmId" AS VARCHAR) AS sample
        FROM video_events__selected_video_alarms a
        LEFT JOIN (SELECT DISTINCT alarm_id FROM video_events__video_files) vf
          ON CAST(a."AlarmId" AS VARCHAR) = CAST(vf.alarm_id AS VARCHAR)
        WHERE CAST(a."VideoCount" AS INTEGER) > 0 AND vf.alarm_id IS NULL
        ORDER BY sample
        LIMIT 5
    """,
    "terminal_duplication": """
        SELECT "UnitStateNumber" AS sample
        FROM video_events__selected_video_alarms
        GROUP BY "UnitStateNumber"
        HAVING COUNT(DISTINCT "TerminalId") > 1
        ORDER BY sample
        LIMIT 5
    """,
    "plate_match_coverage": """
        SELECT DISTINCT source_vehicle AS sample
        FROM reference__vehicle_matches
        WHERE match_status <> 'matched'
        ORDER BY sample
        LIMIT 5
    """,
    "timestamp_monotonicity": """
        SELECT DISTINCT alarm_id AS sample
        FROM (SELECT alarm_id,
                     timestamp_utc < LAG(timestamp_utc)
                       OVER (PARTITION BY alarm_id ORDER BY point_index) AS is_decreasing
              FROM video_events__track_points)
        WHERE is_decreasing
        ORDER BY sample
        LIMIT 5
    """,
    "coordinate_sanity": """
        SELECT CAST("AlarmId" AS VARCHAR) AS sample
        FROM video_events__selected_video_alarms
        WHERE TRY_CAST(NULLIF("Latitude", '') AS DOUBLE) IS NULL
           OR TRY_CAST(NULLIF("Longitude", '') AS DOUBLE) IS NULL
           OR TRY_CAST(NULLIF("Latitude", '') AS DOUBLE) < -90
           OR TRY_CAST(NULLIF("Latitude", '') AS DOUBLE) > 90
           OR TRY_CAST(NULLIF("Longitude", '') AS DOUBLE) < -180
           OR TRY_CAST(NULLIF("Longitude", '') AS DOUBLE) > 180
           OR (TRY_CAST(NULLIF("Latitude", '') AS DOUBLE) = 0
               AND TRY_CAST(NULLIF("Longitude", '') AS DOUBLE) = 0)
        ORDER BY sample
        LIMIT 5
    """,
}


def _ratio(affected: int, total: int) -> float:
    """`affected/total`; при total=0 → 0.0 (§10.2)."""
    return affected / total if total > 0 else 0.0


def _status(ratio: float) -> str:
    """`fail` если ratio > 0.2, `warn` если ratio > 0, иначе `ok` (§10.2). Считает сервис."""
    if ratio > 0.2:
        return "fail"
    if ratio > 0:
        return "warn"
    return "ok"


def _sample_ids(db: duckdb.DuckDBPyConnection, check_id: str) -> list[str]:
    """До 5 примеров (id аларма / госномер) для проверки. Нет запроса → пусто."""
    sql = _SAMPLE_SQL.get(check_id)
    if sql is None:
        return []
    rows = rows_to_dicts(db.execute(sql))
    return [str(r["sample"]) for r in rows if r["sample"] is not None]


def report(db: duckdb.DuckDBPyConnection) -> ConsistencyReport:
    """Собирает `ConsistencyReport` (§10.2) из view `v_consistency_checks` + сэмплов.

    Порядок проверок фиксирован `_CHECK_META`; сырьё из view матчится по `check_id`.
    `evidence_rate`/`speed_agreement_rate` — производные от ratio двух проверок.
    """
    raw = {
        row["check_id"]: row
        for row in rows_to_dicts(
            db.execute('SELECT "check_id", "affected_count", "total" FROM v_consistency_checks')
        )
    }

    ratios: dict[str, float] = {}
    checks: list[ConsistencyCheck] = []
    for check_id, meta in _CHECK_META.items():
        row = raw.get(check_id, {"affected_count": 0, "total": 0})
        affected = int(row["affected_count"])
        total = int(row["total"])
        ratio = _ratio(affected, total)
        ratios[check_id] = ratio
        checks.append(
            ConsistencyCheck(
                check_id=check_id,
                title_ru=meta["title_ru"],
                status=_status(ratio),
                affected_count=affected,
                total=total,
                ratio=round(ratio, 4),
                sample_ids=_sample_ids(db, check_id),
                description_ru=meta["description_ru"],
            )
        )

    return ConsistencyReport(
        checks=checks,
        evidence_rate=round(1.0 - ratios["incident_no_video"], 4),
        speed_agreement_rate=round(1.0 - ratios["speed_disagreement"], 4),
        generated_at_source="duckdb",
    )
