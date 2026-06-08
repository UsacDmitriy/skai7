"""
ETL: детерминированный placeholder-генератор AI-кэша (Волна 3 · w3-16).

По 54 инцидентам из v_incidents пишет два кэш-файла под §8.1 контракта:
  * data/ai/scene_labels.json   — incident_scene  (VLM-сцена, заглушка)
  * data/ai/weather_cache.json  — incident_weather (Open-Meteo, заглушка)

Это КАРКАС: реальные значения проставят b16 (VLM по кадру ch1/ch5) и b17
(Open-Meteo historical + sunrise-sunset), перезаписав эти файлы. Без кэша
рантайм деградирует в детерминированный фолбэк (§8.0/§8.2: weather="unknown",
day_night из часа ts, bonus=0) — поэтому placeholder безопасен.

Детерминизм: ни Date.now(), ни random. Все поля — функция от данных инцидента
(id, ts, lat, lon). ORDER BY id + фиксированный порядок ключей ⇒ повторный
запуск даёт байт-идентичный файл (идемпотентность).

Usage:
    python -m api.etl.ai_cache_seed
    python api/etl/ai_cache_seed.py [db_path]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow `python api/etl/ai_cache_seed.py` entry point (no -m flag)
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import duckdb

DB_PATH = Path("data/skai.duckdb")
AI_DIR = Path("data/ai")
SCENE_PATH = AI_DIR / "scene_labels.json"
WEATHER_PATH = AI_DIR / "weather_cache.json"

_SCENE_HEADER = (
    "placeholder Волны 3 (w3-16); b16 перезаписывает реальными VLM-метками сцены."
)
_WEATHER_HEADER = (
    "placeholder Волны 3 (w3-16); b17 перезаписывает значениями "
    "Open-Meteo historical + sunrise-sunset."
)


def _hour_of(ts: str) -> int:
    """Час из строки ts ('2026-05-15 03:37:22+04' или ISO с 'T'). Детерминизм,
    без datetime.now: берём литеральный час метки (час ts, §8.0)."""
    time_part = ts.replace("T", " ").split(" ", 1)[1]
    return int(time_part.split(":")[0])


def _day_night_from_hour(hour: int) -> str:
    """Час → day_night ∈ {day,twilight,night} (§8.1). Заглушка-эвристика;
    b16 уточнит сценой. day 08–17, twilight 06–07 и 18–20, иначе night."""
    if 8 <= hour < 18:
        return "day"
    if (6 <= hour < 8) or (18 <= hour < 21):
        return "twilight"
    return "night"


def _scene_record(incident_id: str, ts: str) -> dict:
    """Строка incident_scene (§8.1) — placeholder. weather/road_surface/area/
    visibility = "unknown", scene_confidence=0.0, source="placeholder";
    day_night выводится из часа ts (единственное «реальное» поле каркаса)."""
    return {
        "id": incident_id,
        "weather": "unknown",
        "day_night": _day_night_from_hour(_hour_of(ts)),
        "road_surface": "unknown",
        "area": "unknown",
        "visibility": "unknown",
        "scene_confidence": 0.0,
        "source": "placeholder",
    }


def _weather_record(incident_id: str, ts: str, lat, lon) -> dict:
    """Строка incident_weather (§8.1) — placeholder. api_weather="unknown",
    числовые метрики Open-Meteo = null (b17 проставит), discrepancy=false /
    discrepancy_kind="none" (нечего сверять), is_day из часа ts."""
    day_night = _day_night_from_hour(_hour_of(ts))
    return {
        "id": incident_id,
        "ts": ts,
        "lat": lat,
        "lon": lon,
        "api_weather": "unknown",
        "api_precip_mm": None,
        "api_visibility_m": None,
        "is_day": day_night == "day",
        "solar_elevation_deg": None,
        "discrepancy": False,
        "discrepancy_kind": "none",
    }


def _write_cache(path: Path, header: str, schema_ref: str, records: list[dict]) -> None:
    """Детерминированная запись кэша: фиксированная структура + trailing newline."""
    payload = {
        "_comment": header,
        "schema_ref": schema_ref,
        "source": "placeholder",
        "count": len(records),
        "records": records,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text + "\n", encoding="utf-8")


def seed(db_path: Path = DB_PATH, ai_dir: Path = AI_DIR) -> int:
    """Сгенерировать оба кэш-файла из v_incidents. Возвращает число строк (54)."""
    ai_dir.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(db_path), read_only=True) as conn:
        # ORDER BY id — устойчивый порядок ⇒ идемпотентный (байт-идентичный) вывод.
        rows = conn.execute(
            'SELECT "id", "ts", "lat", "lon" FROM v_incidents ORDER BY "id"'
        ).fetchall()

    scene_records = [_scene_record(r[0], r[1]) for r in rows]
    weather_records = [_weather_record(r[0], r[1], r[2], r[3]) for r in rows]

    _write_cache(
        ai_dir / "scene_labels.json", _SCENE_HEADER,
        "00-CONTRACT.md §8.1 incident_scene", scene_records,
    )
    _write_cache(
        ai_dir / "weather_cache.json", _WEATHER_HEADER,
        "00-CONTRACT.md §8.1 incident_weather", weather_records,
    )

    print(f"  [ai-cache] scene_labels.json   {len(scene_records):>4} records")
    print(f"  [ai-cache] weather_cache.json  {len(weather_records):>4} records")
    print(f"Done. AI placeholder cache written to {ai_dir.resolve()}")
    return len(rows)


if __name__ == "__main__":
    args = sys.argv[1:]
    kwargs: dict = {}
    if len(args) >= 1:
        kwargs["db_path"] = Path(args[0])
    if len(args) >= 2:
        kwargs["ai_dir"] = Path(args[1])
    seed(**kwargs)
