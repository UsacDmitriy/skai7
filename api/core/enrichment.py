"""Deterministic enrichment functions for SKAI v2 backend.

Pure module — no I/O, no global mutable state, no nondeterminism.
Same input → same output across runs (seed by vehicle plate via zlib.crc32).
No `random`, no `datetime.now`.
"""

from __future__ import annotations

import zlib
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Pools (module-level constants)
# ---------------------------------------------------------------------------

_DRIVER_NAMES: list[str] = [
    "Иванов Алексей Петрович",
    "Петров Дмитрий Сергеевич",
    "Сидоров Владимир Николаевич",
    "Козлов Иван Андреевич",
    "Новиков Александр Владимирович",
    "Морозов Сергей Иванович",
    "Волков Андрей Михайлович",
    "Лебедев Константин Юрьевич",
    "Семёнов Роман Васильевич",
    "Богданов Олег Николаевич",
    "Смирнов Павел Алексеевич",
    "Кузнецов Артём Дмитриевич",
    "Попов Виктор Анатольевич",
    "Фёдоров Максим Игоревич",
    "Орлов Евгений Сергеевич",
    "Зайцев Николай Владимирович",
    "Соколов Денис Петрович",
    "Михайлов Антон Борисович",
    "Никитин Геннадий Олегович",
    "Захаров Тимур Ринатович",
    "Яковлев Илья Степанович",
    "Гусев Вячеслав Александрович",
]  # ≥20 names

_DEPARTMENTS: list[str] = [
    "Логистика · Север",
    "Логистика · Центр",
    "Логистика · Юг",
    "Доставка · Запад",
    "Доставка · Восток",
]  # sync: incidents_service.py _DEPARTMENTS, seed_drivers.py DEPARTMENTS

_REGIONS: list[str] = [
    "Москва",
    "Московская обл.",
    "Санкт-Петербург",
    "Приморский край",
    "Татарстан",
    "Свердловская обл.",
    "Краснодарский край",
]  # ≥5 регионов; sync: incidents_service.py _REGIONS, seed_drivers.py REGIONS

_VEHICLE_MODELS: list[str] = [
    "ГАЗон NEXT",
    "КамАЗ-5490",
    "Volvo FH",
    "МАЗ-5440",
    "ГАЗель NEXT",
    "Scania R500",
    "MAN TGX",
    "Mercedes-Benz Actros",
    "КамАЗ-65115",
    "ГАЗ-3307",
    "МАЗ-6430",
    "Урал NEXT",
    "ПАЗ-3205",
    "ЛИАЗ-5292",
]

# ---------------------------------------------------------------------------
# Speed-limit table by alarm_code (event_type)
# DMS / city-type alarms → 60; highway/telematics alarms → 90
# ---------------------------------------------------------------------------

# Ключи — и канонические `code` (alarm_code в v_incidents), и `raw`-имена
# (fallback alarm_type в сервисе). Синхронизировано с `alarm_type_catalog` (b1, §1).
# Правило §2: source=DMS / городской тип → 60; шоссе/манёвры → 90 (дефолт).
_SPEED_LIMIT_TABLE: dict[str, int] = {
    # DMS — мониторинг водителя (городской тип) → 60
    "DMS_DROWSY": 60, "Drowsiness": 60,
    "DMS_YAWNING": 60, "Yawning": 60,
    "DMS_PHONE": 60, "Distraction": 60,
    "DMS_SMOKING": 60, "Smoking": 60,
    "DMS_SEATBELT": 60, "SeatBelt": 60,
    "CAMERA_TAMPER": 60, "Sabotage": 60,
    "DRIVER_SUBSTITUTION": 60, "NoDriver": 60,
    # ADAS — дистанция/столкновение/пешеход (городская близость) → 60
    "ADAS_FCW": 60, "CollisionWarning": 60,
    "ADAS_HMW": 60, "DangerousDistance": 60,
    "ADAS_PCW": 60, "PedestrianWarning": 60,
    # COMBINED / TELEMATICS — скорость и манёвры (шоссе) → 90
    "OVERSPEED": 90, "SpeedLimitViolation": 90,
    "HARSH_BRAKING": 90, "SharpBraking": 90,
    "HARSH_ACCEL": 90, "SharpAcceleration": 90,
    "HARSH_CORNERING": 90, "SharpLeftTurn": 90,
}

_DEFAULT_SPEED_LIMIT = 90

# ---------------------------------------------------------------------------
# Evidence summary templates by alarm_code
# ---------------------------------------------------------------------------

_EVIDENCE_TEMPLATES: dict[str, str] = {
    "Drowsiness": "Обнаружено засыпание за рулём. Водитель демонстрировал признаки микросна. Скорость: {speed:.0f} км/ч. Уровень риска: {severity}.",
    "Yawning": "Зафиксировано многократное зевание водителя. Признаки усталости. Скорость: {speed:.0f} км/ч. Уровень риска: {severity}.",
    "Distraction": "Водитель отвлёкся от дороги. Взгляд не направлен вперёд более 3 секунд. Скорость: {speed:.0f} км/ч. Уровень риска: {severity}.",
    "Smoking": "Зафиксировано курение за рулём. Скорость: {speed:.0f} км/ч. Уровень риска: {severity}.",
    "NoDriver": "Водительское место пусто во время движения. Скорость: {speed:.0f} км/ч. Уровень риска: {severity}.",
    "Sabotage": "Обнаружена попытка закрыть или заблокировать DMS-камеру. Скорость: {speed:.0f} км/ч. Уровень риска: {severity}.",
    "SeatBelt": "Водитель двигался без пристёгнутого ремня безопасности. Скорость: {speed:.0f} км/ч. Уровень риска: {severity}.",
    "CollisionWarning": "Система ADAS зафиксировала опасное сближение с объектом. Скорость: {speed:.0f} км/ч. Уровень риска: {severity}.",
    "DangerousDistance": "Дистанция до впереди идущего ТС критически мала. Скорость: {speed:.0f} км/ч. Уровень риска: {severity}.",
    "PedestrianWarning": "Обнаружен пешеход на траектории движения. Скорость: {speed:.0f} км/ч. Уровень риска: {severity}.",
    "SpeedLimitViolation": "Превышение скорости: {speed:.0f} км/ч при допустимых 90 км/ч. Уровень риска: {severity}.",
    "SharpBraking": "Резкое торможение. Скорость в момент события: {speed:.0f} км/ч. Уровень риска: {severity}.",
    "SharpAcceleration": "Резкое ускорение. Скорость в момент события: {speed:.0f} км/ч. Уровень риска: {severity}.",
    "SharpLeftTurn": "Резкий левый поворот на скорости {speed:.0f} км/ч. Уровень риска: {severity}.",
    # Mock codes
    "DMS_DROWSY": "Обнаружено засыпание за рулём (микросон). Скорость: {speed:.0f} км/ч. Уровень риска: {severity}.",
    "DMS_PHONE": "Зафиксировано использование телефона во время движения. Скорость: {speed:.0f} км/ч. Уровень риска: {severity}.",
    "CRASH_SENSOR": "Датчик удара зафиксировал резкое изменение динамики. Скорость: {speed:.0f} км/ч. Уровень риска: {severity}.",
    "HARSH_BRAKING": "Экстренное торможение. Скорость в момент события: {speed:.0f} км/ч. Уровень риска: {severity}.",
    "DRIVER_SUBSTITUTION": "DMS зафиксировала смену водителя без авторизации. Скорость: {speed:.0f} км/ч. Уровень риска: {severity}.",
}

_DEFAULT_EVIDENCE_TEMPLATE = "Событие типа {alarm_code}. Скорость: {speed:.0f} км/ч. Уровень риска: {severity}."

# ---------------------------------------------------------------------------
# Camera slot definitions (CONTRACT §2, frozen)
# Fixed 3 canonical camera slots: ADAS (ch1), DMS (ch5), СНЗ (ch2 else ch3)
# ---------------------------------------------------------------------------

_CAM_ADAS_ID = "CAM-01"
_CAM_DMS_ID = "CAM-05"
_CAM_SNZ_ID = "CAM-02"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def driver_for(db, plate: str) -> dict:
    """DB-first: lookup driver_reference, fallback synthetic by crc32(plate).

    Returns {"driver": str, "driver_id": str, "driver_phone": str}.
    Pass db=None to use synthetic fallback only (e.g. in tests).
    """
    if db is not None:
        try:
            row = db.execute(
                'SELECT "driver_name","driver_id","driver_phone" '
                'FROM "driver_reference" WHERE "vehicle_plate"=?',
                [plate],
            ).fetchone()
            if row:
                return {"driver": row[0], "driver_id": row[1], "driver_phone": row[2]}
        except Exception:
            pass
    seed = zlib.crc32(plate.encode()) & 0xFFFFFFFF
    part1 = seed % 100000
    part2 = (seed // 100000) % 100000
    return {
        "driver": _DRIVER_NAMES[seed % len(_DRIVER_NAMES)],
        "driver_id": "DRV-" + str(seed % 9000 + 1000),
        "driver_phone": "+7" + f"{part1:05d}{part2:05d}",
    }


def driver_id_for(plate: str) -> str:
    """'DRV-XXXX' детерминированно по plate."""
    seed = zlib.crc32(plate.encode()) & 0xFFFFFFFF
    return "DRV-" + str(seed % 9000 + 1000)


def driver_phone_for(plate: str) -> str:
    """+7XXXXXXXXXX — 10 цифр из seed по plate."""
    seed = zlib.crc32(plate.encode()) & 0xFFFFFFFF
    # Derive 10 digits from seed: split seed into two 5-digit numbers
    part1 = seed % 100000
    part2 = (seed // 100000) % 100000
    digits = f"{part1:05d}{part2:05d}"
    return "+7" + digits


def vehicle_model_for(plate: str) -> str:
    """Модель ТС из пула, детерминированно по plate."""
    seed = zlib.crc32(plate.encode()) & 0xFFFFFFFF
    return _VEHICLE_MODELS[seed % len(_VEHICLE_MODELS)]


def speed_limit_for(alarm_code: str) -> int:
    """Ограничение скорости по типу тревоги. По умолчанию 90, DMS/city → 60."""
    return _SPEED_LIMIT_TABLE.get(alarm_code, _DEFAULT_SPEED_LIMIT)


def is_night(ts_iso: str) -> bool:
    """True если час UTC ∈ [22, 06)."""
    # Parse ISO 8601; support both 'Z' and '+00:00' suffixes
    ts_iso_clean = ts_iso.replace("Z", "+00:00")
    dt = datetime.fromisoformat(ts_iso_clean)
    # Convert to UTC if timezone-aware
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    hour = dt.hour
    return hour >= 22 or hour < 6


def continuous_driving_min(movement_duration: str | None) -> int:
    """Разбирает 'HH:MM:SS' → минуты. None или невалидные → 0."""
    if not movement_duration:
        return 0
    parts = movement_duration.strip().split(":")
    if len(parts) != 3:
        return 0
    try:
        h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
        return h * 60 + m
    except (ValueError, TypeError):
        return 0


# ---------------------------------------------------------------------------
# Веса формулы risk_score (§2) — единый источник истины.
# Вынесены на уровень модуля, чтобы explainability (b27, §8.8) ИМПОРТИРОВАЛ их,
# а не копировал константы (дрейф ловит tu-riskbreakdown).
# ---------------------------------------------------------------------------

# Вес тяжести по уровню; неизвестный severity → 0.2 (как low).
SEVERITY_WEIGHTS: dict[str, float] = {
    "critical": 1.0,
    "high": 0.7,
    "medium": 0.45,
    "low": 0.2,
}

# Веса слагаемых перед суммированием (§2). Ключи зеркалят поля RiskBreakdown (§8.8).
RISK_TERM_WEIGHTS: dict[str, float] = {
    "severity_w": 0.45,
    "speed_ratio": 0.25,
    "night": 0.15,
    "freq_w": 0.15,
}


def risk_term_coeffs(
    severity: str,
    speed_kmh: float,
    speed_limit_kmh: int,
    is_night: bool,
    events_last_7d: int,
) -> dict[str, float]:
    """Сырые коэффициенты слагаемых формулы §2 (ДО умножения на веса и ·100).

    sev_w: critical=1.0, high=0.7, medium=0.45, low=0.2 (неизвестный → low).
    speed_ratio = min(speed_kmh / speed_limit_kmh, 1.5) / 1.5  (guard div/0).
    night = 1 if is_night else 0.
    freq_w = min(events_last_7d / 7, 1).
    Источник истины для risk_score и risk_breakdown (b27) — оба зовут эту функцию.
    """
    sev_w = SEVERITY_WEIGHTS.get(severity.lower(), 0.2)

    if speed_limit_kmh == 0:
        speed_ratio = 0.0
    else:
        speed_ratio = min(speed_kmh / speed_limit_kmh, 1.5) / 1.5

    night_w = 1.0 if is_night else 0.0
    freq_w = min(events_last_7d / 7, 1.0)

    return {
        "severity_w": sev_w,
        "speed_ratio": speed_ratio,
        "night": night_w,
        "freq_w": freq_w,
    }


def risk_score(
    severity: str,
    speed_kmh: float,
    speed_limit_kmh: int,
    is_night: bool,
    events_last_7d: int,
) -> int:
    """Формула риска §2, результат 0..100.

    result = round(100 * Σ(вес_слагаемого · коэффициент)), клампится в [0, 100].
    Коэффициенты и веса — из `risk_term_coeffs` / `RISK_TERM_WEIGHTS` (общий источник).
    """
    coeffs = risk_term_coeffs(
        severity, speed_kmh, speed_limit_kmh, is_night, events_last_7d
    )
    raw = 100.0 * sum(RISK_TERM_WEIGHTS[k] * coeffs[k] for k in RISK_TERM_WEIGHTS)
    return max(0, min(100, round(raw)))


def weather_risk_bonus(scene: dict | None, weather: dict | None) -> float:
    """Детерминированная надбавка к risk_score из контекста сцены/погоды (§8.2/§8.4).

    +0.1 если road_surface ∈ {wet, ice} (скользкое покрытие).
    +0.1 если visibility = 'poor' (плохая видимость).
    Ночь уже учтена в risk_score → не дублируем.
    Надбавка считается из полей СЦЕНЫ (road_surface/visibility); `weather` —
    зарезервированный кросс-чек-контекст и на величину надбавки не влияет (§8.2).
    Без сцены (нет кэша / фолбэк `unknown`) → 0.0 (обратная совместимость).
    Результат ∈ {0.0, 0.1, 0.2} — добавляется к сырому коэффициенту ДО *100.
    """
    if not scene:
        return 0.0
    bonus = 0.0
    if scene.get("road_surface") in ("wet", "ice"):
        bonus += 0.1
    if scene.get("visibility") == "poor":
        bonus += 0.1
    return round(bonus, 3)


def evidence_summary(alarm_code: str, speed_kmh: float, severity: str) -> str:
    """Текстовое описание тревоги по шаблону."""
    template = _EVIDENCE_TEMPLATES.get(alarm_code, _DEFAULT_EVIDENCE_TEMPLATE)
    return template.format(speed=speed_kmh, severity=severity, alarm_code=alarm_code)


def cameras_from_videofiles(rows: list[dict]) -> list[dict]:
    """Формирует ровно 3 канонических Camera dict из строк таблицы video_files.

    CONTRACT §2 (frozen). Всегда возвращает 3 записи в порядке:
      1. ADAS  — channel 1  — label "ADAS · Фронт"
      2. DMS   — channel 5  — label "DMS · Салон"
      3. СНЗ   — channel 2 если есть, иначе channel 3; если ни 2, ни 3 — placeholder

    Labels:
      - СНЗ из ch2 → "СНЗ · Доп."
      - СНЗ из ch3 → "СНЗ · Кузов"
      - СНЗ absent → "СНЗ · Доп." (canonical placeholder)

    Status per camera:
      - "online"  if download_status == "downloaded"
      - "warning" if download_status непустой и не "downloaded" (partial/broken/unknown)
      - "offline" if канал отсутствует в rows ИЛИ download_status пустой/None

    hasVideo: True если status in ("online", "warning") — т.е. строка файла реально существует.

    offline_from / offline_to:
      - online → None, None
      - warning/offline с известным created_at_utc → используем его как offline_from,
        offline_to = None (открытый диапазон)
      - offline без строки (канал отсутствует) → None, None
      Выбор детерминирован и не использует datetime.now/random.
    """
    # Index rows by channel (first occurrence wins for dedup)
    channel_rows: dict[int, dict] = {}
    for row in rows:
        ch_raw = row.get("channel", row.get("Channel", ""))
        try:
            ch = int(ch_raw)
        except (ValueError, TypeError):
            continue
        if ch not in channel_rows:
            channel_rows[ch] = row

    def _make_camera(cam_id: str, label: str, row: dict | None) -> dict:
        """Строит dict камеры из найденной строки (или None если канал отсутствует)."""
        if row is None:
            # Channel entirely absent
            return {
                "id": cam_id,
                "label": label,
                "status": "offline",
                "hasVideo": False,
                "offline_from": None,
                "offline_to": None,
            }

        dl_status = str(row.get("download_status", row.get("Download_status", "")) or "").strip()

        if dl_status == "downloaded":
            status = "online"
        elif dl_status:
            status = "warning"
        else:
            status = "offline"

        has_video = status in ("online", "warning")

        # offline_from: best-effort deterministic — use created_at_utc if available and status != online
        offline_from: str | None = None
        offline_to: str | None = None
        if status != "online":
            ts_raw = row.get("created_at_utc", row.get("event_begin_utc", ""))
            if ts_raw:
                offline_from = str(ts_raw)
            # offline_to remains None (open-ended window; closed window computed upstream)

        return {
            "id": cam_id,
            "label": label,
            "status": status,
            "hasVideo": has_video,
            "offline_from": offline_from,
            "offline_to": offline_to,
        }

    # Slot 1: ADAS — channel 1
    adas = _make_camera("CAM-01", "ADAS · Фронт", channel_rows.get(1))

    # Slot 2: DMS — channel 5
    dms = _make_camera("CAM-05", "DMS · Салон", channel_rows.get(5))

    # Slot 3: СНЗ — channel 2 preferred, else channel 3, else absent placeholder
    if 2 in channel_rows:
        snz = _make_camera("CAM-02", "СНЗ · Доп.", channel_rows[2])
    elif 3 in channel_rows:
        snz = _make_camera("CAM-03", "СНЗ · Кузов", channel_rows[3])
    else:
        snz = _make_camera("CAM-02", "СНЗ · Доп.", None)

    return [adas, dms, snz]


def telemetry_from_trackpoints(
    rows: list[dict], event_ts_iso: str
) -> list[dict]:
    """Формирует TelemetryPoint[] из строк track_points в диапазоне ±60 с от event_ts.

    CSV-колонки: timestamp_utc, speed_kmh, (прочие игнорируются).
    Возвращает список {ts_offset:int, speed:float, ax:float, ay:float}.
    ax = производная скорости (speed[i]-speed[i-1])/Δt в м/с².
    ay = 0.0 (реального акселерометра нет).
    Первая точка: ax=0.0 (нет предыдущей).

    # TODO: реальный акселерометр отсутствует в датасете
    """
    event_ts_clean = event_ts_iso.replace("Z", "+00:00")
    event_dt = datetime.fromisoformat(event_ts_clean)
    if event_dt.tzinfo is not None:
        event_dt = event_dt.astimezone(timezone.utc)

    # Parse and filter rows within ±60 s
    parsed: list[tuple[int, float]] = []  # (ts_offset_seconds, speed_kmh)
    for row in rows:
        ts_raw = row.get("timestamp_utc", row.get("Timestamp_utc", ""))
        spd_raw = row.get("speed_kmh", row.get("Speed_kmh", ""))
        if not ts_raw:
            continue
        try:
            ts_clean = str(ts_raw).replace("Z", "+00:00")
            pt_dt = datetime.fromisoformat(ts_clean)
            if pt_dt.tzinfo is not None:
                pt_dt = pt_dt.astimezone(timezone.utc)
            offset_s = int((pt_dt - event_dt).total_seconds())
            if abs(offset_s) > 60:
                continue
            speed = float(spd_raw) if spd_raw not in (None, "", "nan") else 0.0
            parsed.append((offset_s, speed))
        except (ValueError, TypeError):
            continue

    # Sort by ts_offset
    parsed.sort(key=lambda x: x[0])

    # Build TelemetryPoint list with ax derivative
    result: list[dict] = []
    for i, (offset, speed) in enumerate(parsed):
        if i == 0:
            ax = 0.0
        else:
            prev_offset, prev_speed = parsed[i - 1]
            dt_s = offset - prev_offset
            if dt_s == 0:
                ax = 0.0
            else:
                # Convert speed from km/h to m/s before derivative
                # TODO: реальный акселерометр отсутствует в датасете
                ax = round(
                    ((speed - prev_speed) * 1000.0 / 3600.0) / dt_s, 3
                )
        result.append(
            {
                "ts_offset": offset,
                "speed": speed,
                "ax": ax,
                "ay": 0.0,  # TODO: реальный акселерометр отсутствует в датасете
            }
        )

    return result
