"""NLU-сервис (§7.3/§7.5) — свободный текст → структурированный `ReportQuery`.

Основной путь — Groq API + LLaMA 3.3 70B (structured JSON); fallback —
локальный детерминированный regex-парсер. Обе ветки возвращают **одинаковую**
схему `ReportQuery` (импорт из домена b5, не дублируем модель).

`parse` никогда не падает: любая ошибка Groq (нет ключа, сеть, невалидный JSON,
ошибка валидации) молча уходит в regex; пустой/мусорный вход → безопасный
дефолт `ReportQuery(kind="fleet", period_days=3)`.
"""

from __future__ import annotations

import json
import re

from api.core.config import settings
from api.domain.reports import ReportQuery

# ---------------------------------------------------------------------------
# Regex-fallback: детерминированный парсер «госномер / ФИО / период / view».
# ---------------------------------------------------------------------------

# Госномер РФ: буква + 3 цифры + 2 буквы + 2–3 цифры региона (кириллица/латиница).
_PLATE_RU_RE = re.compile(
    r"[АВЕКМНОРСТУХABEKMHOPCTYX]\s?\d{3}\s?[АВЕКМНОРСТУХABEKMHOPCTYX]{2}\s?\d{2,3}",
    re.IGNORECASE,
)
# Госномер KZ: 3 цифры + 3 буквы + 2 цифры региона (напр. 123ABC02).
_PLATE_KK_RE = re.compile(r"\d{3}\s?[A-ZА-ЯЁ]{3}\s?\d{2}", re.IGNORECASE)

_PERIOD_RE = re.compile(r"за\s+(\d+)\s+(?:дн|день|дня|дней)", re.IGNORECASE)
_WEEK_RE = re.compile(r"недел", re.IGNORECASE)
_MONTH_RE = re.compile(r"месяц", re.IGNORECASE)

# Кандидаты ФИО: слова с заглавной кириллической буквы (с падежными окончаниями).
_WORD_RE = re.compile(r"[А-ЯЁ][а-яё]+")
# Служебные слова — не ФИО (отсекаем, чтобы не принять «Нарушения»/«Отчёт» за фамилию).
_STOPWORDS = {
    "нарушения", "нарушение", "отчёт", "отчет", "сводка", "сводку",
    "парк", "парку", "парка", "водитель", "водителю", "водителям",
    "машина", "машинам", "машинами", "неделю", "неделя", "месяц",
}

_PERIOD_MAX = 365  # разумный clamp: не падать на огромном N.


def _detect_view(low: str) -> str | None:
    """«по ТС/машинам» → vehicles, «по водителям» → drivers."""
    if "тс" in low or "машин" in low:
        return "vehicles"
    if "водител" in low:
        return "drivers"
    return None


def _detect_period(low: str) -> int:
    m = _PERIOD_RE.search(low)
    if m:
        return max(1, min(int(m.group(1)), _PERIOD_MAX))
    if _WEEK_RE.search(low):
        return 7
    if _MONTH_RE.search(low):
        return 30
    return 3


def _detect_plate(text: str) -> str | None:
    m = _PLATE_RU_RE.search(text) or _PLATE_KK_RE.search(text)
    return m.group(0).upper().replace(" ", "") if m else None


def _detect_name(text: str) -> str | None:
    words = [w for w in _WORD_RE.findall(text) if w.lower() not in _STOPWORDS]
    if not words:
        return None
    return " ".join(words[:3])


def _parse_regex(text: str) -> ReportQuery:
    """Детерминированный fallback-парсер. Никогда не бросает."""
    low = text.lower()
    period_days = _detect_period(low)
    view = _detect_view(low)

    plate = _detect_plate(text)
    if plate:  # plate имеет приоритет над ФИО.
        return ReportQuery(kind="driver", plate=plate, period_days=period_days)

    name = _detect_name(text)
    if name:
        return ReportQuery(kind="driver", driver_name=name, period_days=period_days)

    return ReportQuery(kind="fleet", period_days=period_days, view=view)


# ---------------------------------------------------------------------------
# Groq-ветка (основной путь). Импорт groq — ленивый, внутри функции.
# ---------------------------------------------------------------------------

_GROQ_MODEL = "llama-3.3-70b-versatile"
_GROQ_SYSTEM = (
    "Ты парсер запросов автопарка. Верни СТРОГО JSON-объект схемы ReportQuery:\n"
    '  kind: "driver" | "fleet" (driver — про конкретного водителя/ТС; fleet — про парк)\n'
    "  plate: строка госномера или null\n"
    "  driver_name: ФИО водителя или null\n"
    "  period_days: целое число дней (неделя=7, месяц=30, по умолчанию 3)\n"
    '  view: "drivers" | "vehicles" | null (для fleet: разрез по водителям/по ТС)\n'
    "Только эти поля. Не добавляй пояснений."
)


def _parse_groq(text: str) -> ReportQuery:
    """Groq + LLaMA 3.3 70B → ReportQuery. Бросает при любой ошибке."""
    api_key = getattr(settings, "groq_api_key", None)
    if not api_key:
        raise RuntimeError("groq_api_key не задан")

    from groq import Groq  # ленивый импорт: не требуется без ключа.

    client = Groq(api_key=api_key)
    completion = client.chat.completions.create(
        model=_GROQ_MODEL,
        messages=[
            {"role": "system", "content": _GROQ_SYSTEM},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    data = json.loads(completion.choices[0].message.content)
    # Pydantic нормализует/проверит enum и отсечёт лишние поля.
    return ReportQuery(**data)


# ---------------------------------------------------------------------------
# Публичный API (§7.3).
# ---------------------------------------------------------------------------


def parse(text: str) -> ReportQuery:
    """Свободный текст → ReportQuery. Groq → except → regex. Никогда не падает."""
    try:
        return _parse_groq(text)
    except Exception:  # нет ключа / сеть / невалидный JSON / ошибка валидации.
        return _parse_regex(text or "")
