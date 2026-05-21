"""Парсинг NL-запросов на естественном языке для интерактивного отчёта."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Keywords & regexes
# ---------------------------------------------------------------------------

_PERIOD_RE = re.compile(
    r"(?:за\s+)?(?:последн(?:ие|их|ие)\s+)?(\d+)\s*(дн(?:я|ей)|недел(?:ю|и|ь)|месяц(?:а|ев)?|час(?:а|ов)?)",
    re.IGNORECASE,
)

_DATE_RANGE_RE = re.compile(
    r"(?:с\s+(\d{1,2}[.\/]\d{1,2}[.\/]\d{2,4}))?\s*"
    r"(?:по\s+(\d{1,2}[.\/]\d{1,2}[.\/]\d{2,4}))?",
    re.IGNORECASE,
)

# Simple Russian-to-English period unit normalisation
_PERIOD_UNIT_MAP = {
    "дня": "days",
    "дней": "days",
    "дне": "days",
    "неделю": "weeks",
    "недели": "weeks",
    "недель": "weeks",
    "месяца": "months",
    "месяцев": "months",
    "месяц": "months",
    "часа": "hours",
    "часов": "hours",
    "час": "hours",
}

_INTENT_KEYWORDS: dict[str, list[str]] = {
    "violations": ["нарушения", "нарушение", "нарушил", "нарушали", "превышение", "превысил", "критические", "критичные", "critical"],
    "compare": ["сравни", "сравнение", "сравнить", "относительно", "против"],
    "summary": ["сводка", "итог", "резюме", "summary", "обзор"],
    "video": ["видео", "видеофайл", "видеозапись", "ролик"],
    "telematics": ["телематика", "телеметрия", "gps", "трек", "координаты"],
    "alarms": ["алармы", "события", "инциденты", "events", "alarms", "тревоги"],
}

_DATA_TYPE_KEYWORDS: dict[str, list[str]] = {
    "video": ["видео", "видеофайл", "видеозапись", "ролик", "media"],
    "telematics": ["телематика", "телеметрия", "gps", "трек", "координаты", "speed", "скорость"],
    "all": ["всё", "все", "полный", "комплексный", "оба", "combined"],
}

_PRESET_KEYWORDS: dict[str, list[str]] = {
    "top5": ["топ-5", "топ 5", "top 5", "top5", "первые пять", "лидеры"],
    "critical": ["критические", "критичные", "critical", "серьёзные", "опасные"],
    "video": ["видео", "видео-дайджест", "видеодайджест", "видеообзор"],
    "all": ["всё", "все", "полный", "весь парк", "весь автопарк"],
    "drivers": ["водители", "водитель", "driver", "drivers", "по водителю"],
    "vehicles": ["тс", "машины", "автомобили", "парк", "fleet", "vehicle", "vehicles"],
}

# License-plate-like pattern: 1 letter, 3 digits, 2 letters, 2-3 digits  (Russian standard)
_PLATE_RE = re.compile(r"[АВЕКМНОРСТУХABEKMHOPCTYX]\d{3}[АВЕКМНОРСТУХABEKMHOPCTYX]{2}\d{2,3}", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalise_period_unit(unit_raw: str) -> str:
    """Convert Russian period unit to a canonical English key."""
    unit = unit_raw.lower().strip()
    return _PERIOD_UNIT_MAP.get(unit, "days")


def _parse_period(text: str) -> tuple[int | None, str | None]:
    """Extract (count, unit) from text, e.g. 'последние три дня' → (3, 'days')."""
    # Textual digits
    digit_words = {
        "один": 1, "одна": 1, "одно": 1,
        "два": 2, "две": 2,
        "три": 3, "четыре": 4, "пять": 5,
        "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10,
    }
    for word, num in digit_words.items():
        if re.search(rf"\b{word}\b", text, re.IGNORECASE):
            # Try to grab the following unit word
            tail = text[re.search(rf"\b{word}\b", text, re.IGNORECASE).end():]
            m = re.search(r"\b(дн|недел|месяц|час)\w*\b", tail, re.IGNORECASE)
            if m:
                return num, _normalise_period_unit(m.group(0))

    m = _PERIOD_RE.search(text)
    if m:
        count = int(m.group(1))
        unit = _normalise_period_unit(m.group(2))
        return count, unit
    return None, None


def _compute_date_range(count: int | None, unit: str | None) -> tuple[str | None, str | None]:
    """Return (date_from, date_to) ISO strings based on period count/unit."""
    if count is None or unit is None:
        return None, None
    date_to = datetime.now()
    if unit == "days":
        date_from = date_to - timedelta(days=count)
    elif unit == "weeks":
        date_from = date_to - timedelta(weeks=count)
    elif unit == "months":
        date_from = date_to - timedelta(days=count * 30)
    elif unit == "hours":
        date_from = date_to - timedelta(hours=count)
    else:
        date_from = date_to - timedelta(days=count)
    return date_from.date().isoformat(), date_to.date().isoformat()


def _extract_plate(text: str) -> str | None:
    """Look for a vehicle state number pattern."""
    m = _PLATE_RE.search(text)
    return m.group(0).upper() if m else None


def _extract_name(text: str) -> str | None:
    """Heuristic: capitalised Russian surname-like token after prepositions."""
    # Look for patterns like "по Иванову", "у Петрова", "Иванов А.П."
    patterns = [
        r"(?:по|у|для|водител[ьяю]\s+)\s+([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ]\.?[А-ЯЁ]?\.?)?)",
        r"([А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.?[А-ЯЁ]?\.?)",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            candidate = m.group(1).strip()
            # Exclude common false positives (short words, prepositions)
            if len(candidate) >= 3 and candidate.lower() not in {"покажи", "сводка", "все", "весь"}:
                return candidate
    return None


def _match_keywords(text: str, keyword_map: dict[str, list[str]]) -> list[str]:
    """Return keys from *keyword_map* that have at least one word present in *text*."""
    matched: list[str] = []
    lower = text.lower()
    for key, words in keyword_map.items():
        if any(w in lower for w in words):
            matched.append(key)
    return matched


def _match_vehicles(text: str, vehicles_df: pd.DataFrame | None) -> str | None:
    """Find the best-matching vehicle by state number or name."""
    if vehicles_df is None or vehicles_df.empty:
        return None
    text_upper = text.upper()
    text_lower = text.lower()

    # 1. Exact state-number match
    if "unit_state_number" in vehicles_df.columns:
        for val in vehicles_df["unit_state_number"].dropna().astype(str):
            if val.upper() in text_upper:
                return val

    # 2. Name match (substring, case-insensitive)
    if "unit_name" in vehicles_df.columns:
        for val in vehicles_df["unit_name"].dropna().astype(str):
            if val.lower() in text_lower:
                return val

    return None


def _score_confidence(
    has_driver: bool,
    has_period: bool,
    has_intents: bool,
    has_data_types: bool,
    preset_match: str | None,
) -> float:
    """Very simple heuristic: 0.0–1.0."""
    score = 0.0
    if has_driver:
        score += 0.25
    if has_period:
        score += 0.25
    if has_intents:
        score += 0.25
    if has_data_types:
        score += 0.15
    if preset_match:
        score += 0.10
    return min(score, 1.0)


# ---------------------------------------------------------------------------
# 1. parse_report_query
# ---------------------------------------------------------------------------


def parse_report_query(text: str, vehicles_df: pd.DataFrame | None = None) -> dict:
    """Parse a natural-language request and return structured parameters.

    Returns
    -------
    dict
        driver_id, period_days, date_from, date_to, data_types, intents, confidence
    """
    text = text.strip()
    if not text:
        return {
            "driver_id": None,
            "period_days": None,
            "date_from": None,
            "date_to": None,
            "data_types": [],
            "intents": [],
            "confidence": 0.0,
        }

    # Driver / vehicle identifier
    driver_id: str | None = None
    plate = _extract_plate(text)
    if plate:
        driver_id = plate
    else:
        name = _extract_name(text)
        if name:
            driver_id = name
        else:
            driver_id = _match_vehicles(text, vehicles_df)

    # Period
    count, unit = _parse_period(text)
    period_days: int | None = None
    date_from: str | None = None
    date_to: str | None = None

    if count is not None and unit is not None:
        date_from, date_to = _compute_date_range(count, unit)
        if unit == "days":
            period_days = count
        elif unit == "weeks":
            period_days = count * 7
        elif unit == "months":
            period_days = count * 30
        elif unit == "hours":
            period_days = max(1, count // 24)

    # Also try explicit date range
    dr = _DATE_RANGE_RE.search(text)
    if dr:
        raw_from, raw_to = dr.group(1), dr.group(2)
        for raw in (raw_from, raw_to):
            if raw:
                # normalise separators
                norm = raw.replace("/", ".")
                parts = norm.split(".")
                if len(parts) == 3:
                    d, m, y = parts
                    if len(y) == 2:
                        y = "20" + y
                    try:
                        iso = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
                        if raw == raw_from:
                            date_from = iso
                        else:
                            date_to = iso
                    except ValueError:
                        pass

    # Data types & intents
    data_types = _match_keywords(text, _DATA_TYPE_KEYWORDS)
    if not data_types:
        data_types = ["all"]

    intents = _match_keywords(text, _INTENT_KEYWORDS)

    # Confidence
    confidence = _score_confidence(
        has_driver=driver_id is not None,
        has_period=period_days is not None or (date_from is not None),
        has_intents=bool(intents),
        has_data_types=bool(data_types and data_types != ["all"]),
        preset_match=match_preset(text),
    )

    return {
        "driver_id": driver_id,
        "period_days": period_days,
        "date_from": date_from,
        "date_to": date_to,
        "data_types": data_types,
        "intents": intents,
        "confidence": round(confidence, 2),
    }


# ---------------------------------------------------------------------------
# 2. generate_confirmation_modal
# ---------------------------------------------------------------------------


def generate_confirmation_modal(params: dict) -> str:
    """Generate HTML for a confirmation modal (State B) displaying query parameters."""
    driver = params.get("driver_id") or "—"
    period = (
        f"{params.get('period_days')} дней"
        if params.get("period_days")
        else f"{params.get('date_from', '—')} → {params.get('date_to', '—')}"
    )
    data_types = ", ".join(params.get("data_types", ["all"]))
    intents = ", ".join(params.get("intents", [])) or "—"
    confidence = params.get("confidence", 0.0)

    bar_width = int(confidence * 100)
    bar_color = "#16A34A" if confidence >= 0.8 else "#EAB308" if confidence >= 0.5 else "#DC2626"

    html = f"""
    <div style="font-family:sans-serif;max-width:480px;border:1px solid #E2E8F0;
                border-radius:12px;padding:24px;background:#FFFFFF;box-shadow:0 4px 6px rgba(0,0,0,0.05);">
      <h3 style="margin:0 0 16px 0;color:#0F172A;font-size:18px;">Подтвердите параметры отчёта</h3>

      <div style="margin-bottom:12px;">
        <span style="color:#64748B;font-size:12px;">Водитель / ТС</span>
        <div style="font-weight:600;color:#0F172A;font-size:16px;">{driver}</div>
      </div>

      <div style="margin-bottom:12px;">
        <span style="color:#64748B;font-size:12px;">Период</span>
        <div style="font-weight:600;color:#0F172A;font-size:16px;">{period}</div>
      </div>

      <div style="margin-bottom:12px;">
        <span style="color:#64748B;font-size:12px;">Типы данных</span>
        <div style="font-weight:600;color:#0F172A;font-size:16px;">{data_types}</div>
      </div>

      <div style="margin-bottom:12px;">
        <span style="color:#64748B;font-size:12px;">Намерения</span>
        <div style="font-weight:600;color:#0F172A;font-size:16px;">{intents}</div>
      </div>

      <div style="margin-bottom:16px;">
        <span style="color:#64748B;font-size:12px;">Уверенность парсера</span>
        <div style="background:#F1F5F9;border-radius:6px;height:8px;margin-top:4px;overflow:hidden;">
          <div style="width:{bar_width}%;background:{bar_color};height:100%;"></div>
        </div>
        <div style="font-size:12px;color:#64748B;text-align:right;margin-top:2px;">{confidence:.0%}</div>
      </div>

      <div style="display:flex;gap:8px;justify-content:flex-end;">
        <button style="padding:8px 16px;border:1px solid #E2E8F0;border-radius:6px;
                       background:#FFFFFF;color:#0F172A;cursor:pointer;font-size:14px;"
                onclick="window.parent.postMessage({{type:'nl-cancel'}},'*')">
          Изменить
        </button>
        <button style="padding:8px 16px;border:none;border-radius:6px;
                       background:#1E3A8A;color:#FFFFFF;cursor:pointer;font-size:14px;"
                onclick="window.parent.postMessage({{type:'nl-confirm'}},'*')">
          Подтвердить
        </button>
      </div>
    </div>
    """
    return html


# ---------------------------------------------------------------------------
# 3. match_preset
# ---------------------------------------------------------------------------


def match_preset(text: str) -> str | None:
    """Return preset key if the query matches a known preset category.

    Presets: top5, critical, video, all, drivers, vehicles.
    """
    lower = text.lower()
    for preset, words in _PRESET_KEYWORDS.items():
        if any(w in lower for w in words):
            return preset
    return None


__all__ = [
    "parse_report_query",
    "generate_confirmation_modal",
    "match_preset",
    "_parse_period",
    "_extract_plate",
]
