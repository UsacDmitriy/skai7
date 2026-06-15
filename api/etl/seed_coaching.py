"""
ETL: generate data/seed/training_assignments.csv — детерминированный демо-датасет
назначений обучения по реальным алармам (§12.0/§12.1).

Источники (только чтение):
  - datasets/ready/video_events/selected_video_alarms.csv  (алармы)
  - data/seed/driver_reference.csv                          (driver_id по vehicle_plate)
  - data/analysis/alarm_types.json                          (нормализация Type → code)

Загрузку в DuckDB делает существующий build_duckdb._load_seed_csvs (glob data/seed/*.csv
→ таблица training_assignments) — ETL-загрузчик НЕ редактируется.

Детерминизм (§12.0): никаких random / datetime.now() — повторный запуск даёт
байт-идентичный CSV.

Usage:
    python -m api.etl.seed_coaching
    python api/etl/seed_coaching.py
"""
from __future__ import annotations

import csv
import json
import sys
import zlib
from datetime import datetime, timedelta
from pathlib import Path

# Allow `python api/etl/seed_coaching.py` entry point (no -m flag)
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

ALARMS_CSV = Path("datasets/ready/video_events/selected_video_alarms.csv")
DRIVER_REF_CSV = Path("data/seed/driver_reference.csv")
CATALOG_JSON = Path("data/analysis/alarm_types.json")
OUT_CSV = Path("data/seed/training_assignments.csv")

_FIELDS = [
    "assignment_id", "incident_id", "vehicle_plate", "driver_id",
    "course_id", "course_title_ru", "assigned_at", "due_at",
    "test_score", "passed", "completed_at", "repeat_within_30d",
]

_TS_FMT = "%Y-%m-%dT%H:%M:%SZ"
_REPEAT_WINDOW = timedelta(days=30)
_DUE_OFFSET = timedelta(hours=72)


def _crc(s: str) -> int:
    return zlib.crc32(s.encode()) & 0xFFFFFFFF


def _course_for(code: str) -> tuple[str, str]:
    """Курс по каноническому коду аларма (§12.1)."""
    if code in ("DMS_DROWSY", "DMS_YAWNING"):
        return "C-FATIGUE", "Контроль усталости"
    if code in ("DMS_PHONE", "DMS_DISTRACTION"):
        return "C-FOCUS", "Концентрация и отвлечения"
    if code.startswith("HARSH_"):
        return "C-SMOOTH", "Плавное вождение"
    if code in ("OVERSPEED", "SpeedLimitViolation"):
        return "C-SPEED", "Скоростной режим"
    if code in ("CAMERA_TAMPER", "DRIVER_SUBSTITUTION"):
        return "C-RULES", "Регламент и оборудование"
    return "C-BASE", "Базовый курс безопасности"


def _load_type_to_code(path: Path) -> dict[str, str]:
    """raw Type → canonical code (паттерн alarm_type_catalog)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {row["raw"]: row["code"] for row in data["alarm_types"]}


def _load_driver_index(path: Path) -> dict[str, str]:
    """vehicle_plate → driver_id."""
    with open(path, newline="", encoding="utf-8") as f:
        return {r["vehicle_plate"]: r["driver_id"] for r in csv.DictReader(f)}


def _parse_ts(value: str) -> datetime:
    return datetime.strptime(value, _TS_FMT)


def _fmt_ts(dt: datetime) -> str:
    return dt.strftime(_TS_FMT)


def _build_rows(
    alarms: list[dict],
    type_to_code: dict[str, str],
    driver_index: dict[str, str],
) -> list[dict]:
    # Индекс для реального расчёта repeat_within_30d: (plate, Type) → [begin, ...]
    by_key: dict[tuple[str, str], list[datetime]] = {}
    for a in alarms:
        key = (a["UnitStateNumber"], a["Type"])
        by_key.setdefault(key, []).append(_parse_ts(a["Begin"]))

    rows: list[dict] = []
    for a in alarms:
        alarm_id = a["AlarmId"]
        plate = a["UnitStateNumber"]
        raw_type = a["Type"]
        code = type_to_code.get(raw_type, raw_type)
        course_id, course_title = _course_for(code)

        assigned = _parse_ts(a["Begin"])
        seed = _crc(str(alarm_id))
        score = seed % 21
        passed = score >= 18

        completed_at = ""
        if score >= 10:
            completed_at = _fmt_ts(assigned + timedelta(hours=seed % 48 + 1))

        # repeat_within_30d: другой аларм той же ТС + того же Type в окне ±30 дней.
        # Считаем все алармы ключа в окне (включая текущий) — если их ≥2, есть «другой».
        in_window = sum(
            1 for other in by_key[(plate, raw_type)]
            if abs(other - assigned) <= _REPEAT_WINDOW
        )
        repeat = in_window >= 2

        rows.append({
            "assignment_id": "TA-" + str(alarm_id),
            "incident_id": alarm_id,
            "vehicle_plate": plate,
            "driver_id": driver_index.get(plate, ""),
            "course_id": course_id,
            "course_title_ru": course_title,
            "assigned_at": _fmt_ts(assigned),
            "due_at": _fmt_ts(assigned + _DUE_OFFSET),
            "test_score": score,
            "passed": "true" if passed else "false",
            "completed_at": completed_at,
            "repeat_within_30d": "true" if repeat else "false",
        })

    rows.sort(key=lambda r: r["assignment_id"])
    return rows


def _write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def seed(out_csv: Path = OUT_CSV) -> None:
    """Генерирует training_assignments.csv. Детерминированно и идемпотентно."""
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    type_to_code = _load_type_to_code(CATALOG_JSON)
    driver_index = _load_driver_index(DRIVER_REF_CSV)
    with open(ALARMS_CSV, newline="", encoding="utf-8") as f:
        alarms = list(csv.DictReader(f))

    rows = _build_rows(alarms, type_to_code, driver_index)
    _write_csv(out_csv, rows)

    print(f"training_assignments : {len(rows):>3} rows  → {out_csv}")


if __name__ == "__main__":
    args = sys.argv[1:]
    seed(Path(args[0]) if args else OUT_CSV)
