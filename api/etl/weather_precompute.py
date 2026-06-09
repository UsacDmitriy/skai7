"""
ETL: оффлайн предрасчёт погоды + день/ночь (идея #11, b17 · §8.2/§8.4).

По 54 видео-алярмам из v_incidents запрашивает Open-Meteo historical API
(precipitation, visibility, weather_code → api_weather) и вычисляет
солнечную высоту → is_day. Кэш: data/ai/weather_cache.json (плоский
JSON-массив, детерминированный, сорт по id). Нет сети → solar elevation
вычисляется, api_weather='unknown'.

Поля §8.2 (incident_weather):
    id, ts, lat, lon,
    api_weather ∈ {clear,rain,snow,fog,unknown},
    api_precip_mm, api_visibility_m, is_day, solar_elevation_deg.

Usage:
    python -m api.etl.weather_precompute            # no-op если кэш есть
    python -m api.etl.weather_precompute --force    # пересобрать кэш
    python api/etl/weather_precompute.py [db_path] [--force]
"""
from __future__ import annotations

import json
import math
import sys
import urllib.error
import urllib.request
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import duckdb

DB_PATH = Path("data/skai.duckdb")
AI_DIR = Path("data/ai")
WEATHER_PATH = AI_DIR / "weather_cache.json"

_OPEN_METEO_BASE = "https://archive-api.open-meteo.com/v1/archive"


# ── WMO weather_code → api_weather ─────────────────────────────────────────────
def _wmo_to_weather(code: int | None) -> str:
    """WMO Weather Code → api_weather ∈ {clear,rain,snow,fog,unknown}."""
    if code is None:
        return "unknown"
    code = int(code)
    if code == 0 or 1 <= code <= 3:
        return "clear"
    if code in (45, 48):
        return "fog"
    if 51 <= code <= 67 or 80 <= code <= 82 or 95 <= code <= 99:
        return "rain"
    if 71 <= code <= 77 or 85 <= code <= 86:
        return "snow"
    return "clear"


# ── Солнечная высота (NOAA-simplified, без внешних библиотек) ───────────────────
def _solar_elevation(lat_deg: float, lon_deg: float, ts_str: str) -> float:
    """Солнечная высота (градусы) для заданной точки и времени.

    Алгоритм: упрощённый NOAA Solar Calculator (без аберрации).
    Результат >0 = солнце над горизонтом (день).
    Детерминировано — только math, без datetime.now.
    """
    ts = ts_str.replace("T", " ")
    # Разобрать дату/время и часовой пояс
    if "+" in ts[10:]:
        dt_part, tz_raw = ts.rsplit("+", 1)
        tz_sign = +1
    elif len(ts) > 19 and ts[19] == "-":
        dt_part = ts[:19]
        tz_raw = ts[20:]
        tz_sign = -1
    else:
        dt_part = ts
        tz_raw = "0"
        tz_sign = +1

    tz_parts = tz_raw.split(":")
    tz_h = tz_sign * (int(tz_parts[0]) + (int(tz_parts[1]) / 60 if len(tz_parts) > 1 else 0))

    date_part, time_part = dt_part.strip().split(" ", 1)
    year, month, day = (int(x) for x in date_part.split("-"))
    h, m, s = (int(x) for x in time_part.split(":"))

    # UTC часы (дробные)
    utc_frac = h - tz_h + m / 60.0 + s / 3600.0

    # Коррекция дня при переходе суток
    day_offset = 0
    if utc_frac < 0:
        utc_frac += 24.0
        day_offset = -1
    elif utc_frac >= 24:
        utc_frac -= 24.0
        day_offset = +1

    # Julian Day Number (Meeus, Ch.7)
    y, mo = year, month
    d = day + day_offset
    if mo <= 2:
        y -= 1
        mo += 12
    A = y // 100
    B = 2 - A + A // 4
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (mo + 1)) + d + B - 1524.5 + utc_frac / 24.0

    # Юлианские века от J2000.0
    T = (jd - 2451545.0) / 36525.0

    # Средняя долгота и аномалия Солнца
    L0 = (280.46646 + 36000.76983 * T) % 360
    M_rad = math.radians((357.52911 + 35999.05029 * T - 0.0001537 * T * T) % 360)

    # Уравнение центра
    C = ((1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M_rad)
         + (0.019993 - 0.000101 * T) * math.sin(2 * M_rad)
         + 0.000289 * math.sin(3 * M_rad))

    # Истинная и видимая долгота Солнца
    sun_lon = L0 + C
    omega_rad = math.radians(125.04 - 1934.136 * T)
    apparent_lon_rad = math.radians(sun_lon - 0.00569 - 0.00478 * math.sin(omega_rad))

    # Наклон эклиптики и склонение
    eps_rad = math.radians(23.439291 - 0.013004 * T + 0.00256 * math.cos(omega_rad))
    dec_rad = math.asin(math.sin(eps_rad) * math.sin(apparent_lon_rad))

    # Прямое восхождение
    ra_rad = math.atan2(math.cos(eps_rad) * math.sin(apparent_lon_rad),
                        math.cos(apparent_lon_rad))

    # Звёздное время Гринвича (градусы)
    gmst = (280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * T * T) % 360

    # Часовой угол
    ha_rad = math.radians((gmst + lon_deg - math.degrees(ra_rad)) % 360)

    lat_rad = math.radians(lat_deg)
    elev_rad = math.asin(math.sin(lat_rad) * math.sin(dec_rad)
                         + math.cos(lat_rad) * math.cos(dec_rad) * math.cos(ha_rad))
    return round(math.degrees(elev_rad), 3)


# ── Разбор ts → дата UTC и час UTC ─────────────────────────────────────────────
def _ts_to_date_hour_utc(ts_str: str) -> tuple[str, int]:
    """Разобрать 'YYYY-MM-DD HH:MM:SS+TZ' → (date_utc_str, hour_utc_int).

    Детерминировано, без datetime.now / external deps.
    """
    ts = ts_str.replace("T", " ")
    if "+" in ts[10:]:
        dt_part, tz_raw = ts.rsplit("+", 1)
        tz_sign = +1
    elif len(ts) > 19 and ts[19] == "-":
        dt_part = ts[:19]
        tz_raw = ts[20:]
        tz_sign = -1
    else:
        dt_part = ts
        tz_raw = "0"
        tz_sign = +1

    tz_parts = tz_raw.split(":")
    tz_h = tz_sign * int(tz_parts[0])

    date_part, time_part = dt_part.strip().split(" ", 1)
    year, month, day = (int(x) for x in date_part.split("-"))
    h = int(time_part.split(":")[0])

    utc_h = h - tz_h
    if utc_h < 0:
        utc_h += 24
        day -= 1
        if day < 1:
            month -= 1
            if month < 1:
                month = 12
                year -= 1
            _dom = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
            day = 29 if (month == 2 and leap) else _dom[month - 1]
    elif utc_h >= 24:
        utc_h -= 24
        day += 1
        _dom = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        max_d = 29 if (month == 2 and leap) else _dom[month - 1]
        if day > max_d:
            day = 1
            month += 1
            if month > 12:
                month = 1
                year += 1

    return f"{year:04d}-{month:02d}-{day:02d}", utc_h


# ── Open-Meteo API ──────────────────────────────────────────────────────────────
def _fetch_open_meteo(lat: float, lon: float, date_str: str) -> dict:
    """GET Open-Meteo archive API. Возвращает dict с hourly или {}."""
    url = (
        f"{_OPEN_METEO_BASE}"
        f"?latitude={lat:.6f}&longitude={lon:.6f}"
        f"&start_date={date_str}&end_date={date_str}"
        f"&hourly=precipitation,visibility,weather_code&timezone=UTC"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


def _extract_hourly_fields(
    data: dict, hour: int
) -> tuple[float | None, float | None, int | None]:
    """Извлечь (precip_mm, visibility_m, weather_code) для заданного часа UTC."""
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        return None, None, None
    idx = hour if hour < len(times) else len(times) - 1
    precip_list = hourly.get("precipitation", [])
    vis_list = hourly.get("visibility", [])
    wcode_list = hourly.get("weather_code", [])
    precip = precip_list[idx] if idx < len(precip_list) else None
    vis = vis_list[idx] if idx < len(vis_list) else None
    wcode = wcode_list[idx] if idx < len(wcode_list) else None
    return precip, vis, wcode


# ── Загрузка инцидентов из БД ──────────────────────────────────────────────────
def _load_incidents(db_path: Path) -> list[tuple]:
    """id, ts, lat, lon по 54 видео-алярмам из v_incidents (video_available=1), ORDER BY id."""
    with duckdb.connect(str(db_path), read_only=True) as conn:
        return conn.execute(
            'SELECT "id", "ts", "lat", "lon" FROM v_incidents '
            'WHERE "video_available" = 1 '
            'ORDER BY "id"'
        ).fetchall()


# ── Запись кэша ────────────────────────────────────────────────────────────────
def _write_cache(path: Path, records: list[dict]) -> None:
    """Плоский JSON-массив + trailing newline. Детерминированный порядок ключей."""
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def _is_valid_cache(path: Path) -> int:
    """Вернуть число записей если кэш валидный (плоский массив с api_weather), иначе 0."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list) and len(data) > 0 and "api_weather" in data[0]:
            return len(data)
    except Exception:
        pass
    return 0


# ── Основная функция ───────────────────────────────────────────────────────────
def precompute(
    db_path: Path = DB_PATH,
    ai_dir: Path = AI_DIR,
    force: bool = False,
) -> int:
    """Создать/обновить data/ai/weather_cache.json (54+ строки). Идемпотентно."""
    ai_dir.mkdir(parents=True, exist_ok=True)
    weather_path = ai_dir / "weather_cache.json"

    if weather_path.exists() and not force:
        n = _is_valid_cache(weather_path)
        if n > 0:
            print(f"  [weather] кэш есть ({n} записей) — no-op (--force для пересборки)")
            return n

    rows = _load_incidents(db_path)
    records: list[dict] = []
    net_ok = True  # будет False после первой сетевой ошибки

    for incident_id, ts, lat, lon in rows:
        ts_str = str(ts)
        lat_f = float(lat) if lat is not None else 55.75
        lon_f = float(lon) if lon is not None else 37.62

        # Солнечная высота (детерминированно, без сети)
        try:
            elev = _solar_elevation(lat_f, lon_f, ts_str)
        except Exception:
            elev = None
        is_day_flag = elev is not None and elev > 0

        # Open-Meteo (только если сеть доступна)
        precip, vis, wcode = None, None, None
        if net_ok:
            try:
                date_str, utc_h = _ts_to_date_hour_utc(ts_str)
                raw = _fetch_open_meteo(lat_f, lon_f, date_str)
                if raw:
                    precip, vis, wcode = _extract_hourly_fields(raw, utc_h)
                else:
                    net_ok = False
            except Exception:
                net_ok = False

        api_weather = _wmo_to_weather(wcode)

        records.append({
            "id": str(incident_id),
            "ts": ts_str,
            "lat": lat_f,
            "lon": lon_f,
            "api_weather": api_weather,
            "api_precip_mm": (round(float(precip), 2) if precip is not None else None),
            "api_visibility_m": (round(float(vis), 1) if vis is not None else None),
            "is_day": is_day_flag,
            "solar_elevation_deg": elev,
        })

    records.sort(key=lambda r: r["id"])
    _write_cache(weather_path, records)
    source = "open-meteo" if net_ok else "fallback"
    print(f"  [weather] weather_cache.json {len(records):>4} записей (source={source})")
    print(f"Done. Weather cache written to {weather_path.resolve()}")
    return len(records)


if __name__ == "__main__":
    argv = sys.argv[1:]
    force = "--force" in argv
    positional = [a for a in argv if not a.startswith("--")]
    kwargs: dict = {"force": force}
    if positional:
        kwargs["db_path"] = Path(positional[0])
    precompute(**kwargs)
