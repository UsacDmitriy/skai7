"""Unit-покрытие view `v_incidents` (b3) — против `00-CONTRACT.md` §1.3/§3.1.

Читает собранную `data/skai.duckdb` (read-only, `skip` без `make db`). Проверяет
инвариант 55 инцидентов (54 видео-алярма + 1 seeded no-video, w3-5), наличие
обязательных полей контракта §3.1 и сохранность
джойна с `alarm_type_catalog` (нет потери строк / NULL в source/severity для
известных кодов). Сетка/uvicorn не требуются.
"""

from __future__ import annotations

# Обязательные поля строки ленты (§3.1), которые материализует view (без enrichment).
_REQUIRED_COLUMNS = {
    "id",
    "alarm_type",
    "alarm_code",
    "alarm_label_ru",
    "source",
    "severity",
    "risk_level",
    "ts",
    "vehicle_plate",
    "speed_kmh",
    "video_available",
}


def _columns(real_db) -> set[str]:
    result = real_db.execute('SELECT * FROM "v_incidents" LIMIT 0')
    return {d[0] for d in result.description}


def test_v_incidents_has_55_rows(real_db) -> None:
    # §1.3: 55 инцидентов = 54 видео-алярма + 1 seeded no-video (CAMERA_TAMPER, w3-5);
    # один на алярм, LEFT JOIN не теряет строк.
    count = real_db.execute('SELECT count(*) FROM "v_incidents"').fetchone()[0]
    assert count == 55


def test_v_incidents_carries_required_contract_fields(real_db) -> None:
    # Каждая строка несёт обязательные поля §3.1.
    assert _REQUIRED_COLUMNS <= _columns(real_db)


def test_no_null_source_or_severity_for_known_codes(real_db) -> None:
    """Джойн с `alarm_type_catalog`: для известных кодов нет NULL в source/severity."""
    bad = real_db.execute(
        'SELECT count(*) FROM "v_incidents" '
        'WHERE "alarm_code" IS NOT NULL '
        'AND ("source" IS NULL OR "severity" IS NULL)'
    ).fetchone()[0]
    assert bad == 0


def test_video_available_is_binary_without_null(real_db) -> None:
    # null-safety §1.3: video_available ∈ {0,1} без NULL.
    distinct = {
        r[0]
        for r in real_db.execute('SELECT DISTINCT "video_available" FROM "v_incidents"').fetchall()
    }
    assert distinct <= {0, 1}
    assert None not in distinct


def test_ids_are_unique(real_db) -> None:
    # Один алярм = одна строка: id уникальны (анти-размножение спайна).
    total, distinct = real_db.execute(
        'SELECT count("id"), count(DISTINCT "id") FROM "v_incidents"'
    ).fetchone()
    assert total == distinct == 55
