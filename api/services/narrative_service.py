"""Сервис нарратива + коучинга (b22, §8.3/§8.4, идеи #12/#13).

Из структурных данных отчёта (`DriverReport`/`FleetReport`) или прогноза
(`RiskForecast`) собирает читаемый текст: **резюме → анализ причин → 3 коучинг-
пункта → признание**. Для В-1/В-2 и копилота.

Две ветки (§8.0, как в `nlu_service`):
  * **Шаблон** — всегда доступен, без сети. Детерминированные правила → связный
    RU/EN текст. Числа берутся ТОЛЬКО из payload (no hallucination).
  * **LLM** (опц., Groq) — переписывает шаблон «глаже» без новых фактов. Любая
    ошибка/нет ключа → шаблон (никогда не падает).

Детерминизм шаблона: один вход → один выход (без `datetime.now`/случайности).
"""

from __future__ import annotations

from typing import Any

from api.core.config import settings
from api.domain.reports import DriverReport, FleetReport

# Категории alarm_code для коучинга (совпадают с forecast_service/enrichment).
_HARSH_CODES = {"HARSH_BRAKING", "HARSH_ACCEL", "HARSH_CORNERING"}
_FATIGUE_CODES = {"DMS_DROWSY", "DMS_YAWNING"}
_OVERSPEED_CODES = {"OVERSPEED"}
_VIDEO_SOURCES = {"DMS", "ADAS", "COMBINED"}

# ---------------------------------------------------------------------------
# Локализованные строки (RU/EN). Заголовки секций + типовые коучинг-пункты.
# ---------------------------------------------------------------------------

_L: dict[str, dict[str, str]] = {
    "ru": {
        "summary": "Резюме",
        "analysis": "Анализ причин",
        "coaching": "Рекомендации (коучинг)",
        "recognition": "Признание",
        "days": "дн.",
        "no_violations_driver": (
            "Водитель {name} ({plate}): за {days} {d} нарушений не зафиксировано."
        ),
        "no_violations_fleet": (
            "По парку из {vehicles} ТС за {days} {d} нарушений не зафиксировано."
        ),
        "clean_recognition": "Отличная дисциплина — так держать.",
        "driver_summary": (
            "Водитель {name} ({plate}, {model}). За {days} {d}: {total} "
            "нарушений (грубых: {gross}). Безопасность {safety}/100, риск {risk}/100."
        ),
        "driver_analysis": (
            "Распределение: видеоаналитика — {video}, телематика — {tele}. "
            "Пробег {mileage} км за {trips} поездок."
        ),
        "driver_warn": "Назначено дисциплинарное предупреждение (порог превышен).",
        "fleet_summary": (
            "Парк: {vehicles} ТС. За {days} {d}: {total} нарушений "
            "(грубых: {gross}). Видеоаналитика — {video}, телематика — {tele}."
        ),
        "fleet_analysis_top": (
            "Наибольший риск: {plate} ({driver}) — риск {risk}/100, "
            "грубых {gross} из {total}."
        ),
        "fleet_recognition": (
            "Лучший показатель: {plate} ({driver}) — риск {risk}/100. "
            "Отметить положительно."
        ),
        "forecast_summary": (
            "Прогноз по ТС {plate} на {horizon} {d}: ожидается ~{avg} событий/день "
            "(коридор {low}–{high})."
        ),
        "forecast_anomaly_on": "Обнаружена аномалия: {reason}.",
        "forecast_anomaly_off": "Аномалий в поведении не выявлено.",
        "forecast_recognition": (
            "При выполнении рекомендаций ожидаемый риск снижается — держите курс."
        ),
        "c_gross": "Сократить грубые нарушения — они весомее всего влияют на риск.",
        "c_overspeed": "Соблюдать скоростной режим: превышения дают наибольший прирост риска.",
        "c_fatigue": "Контролировать режим труда и отдыха — признаки усталости требуют перерывов.",
        "c_harsh": "Практиковать плавное вождение и безопасную дистанцию (меньше резких манёвров).",
        "c_video": "Исключить отвлечения за рулём (телефон/курение) — реагируют камеры ДМС/ADAS.",
        "c_general": "Поддерживать текущий уровень и проходить регулярные инструктажи.",
        "c_monitor": "Продолжать стандартный мониторинг показателей безопасности.",
    },
    "en": {
        "summary": "Summary",
        "analysis": "Root-cause analysis",
        "coaching": "Coaching",
        "recognition": "Recognition",
        "days": "d",
        "no_violations_driver": (
            "Driver {name} ({plate}): no violations recorded over {days} {d}."
        ),
        "no_violations_fleet": (
            "Fleet of {vehicles} vehicles: no violations recorded over {days} {d}."
        ),
        "clean_recognition": "Excellent discipline — keep it up.",
        "driver_summary": (
            "Driver {name} ({plate}, {model}). Over {days} {d}: {total} "
            "violations (gross: {gross}). Safety {safety}/100, risk {risk}/100."
        ),
        "driver_analysis": (
            "Breakdown: video analytics — {video}, telematics — {tele}. "
            "Mileage {mileage} km over {trips} trips."
        ),
        "driver_warn": "A disciplinary warning is assigned (threshold exceeded).",
        "fleet_summary": (
            "Fleet: {vehicles} vehicles. Over {days} {d}: {total} violations "
            "(gross: {gross}). Video analytics — {video}, telematics — {tele}."
        ),
        "fleet_analysis_top": (
            "Highest risk: {plate} ({driver}) — risk {risk}/100, "
            "gross {gross} of {total}."
        ),
        "fleet_recognition": (
            "Best performer: {plate} ({driver}) — risk {risk}/100. "
            "Recognize positively."
        ),
        "forecast_summary": (
            "Forecast for vehicle {plate} over {horizon} {d}: ~{avg} events/day "
            "expected (band {low}–{high})."
        ),
        "forecast_anomaly_on": "Anomaly detected: {reason}.",
        "forecast_anomaly_off": "No behavioural anomalies detected.",
        "forecast_recognition": (
            "Following the recommendations lowers the expected risk — stay the course."
        ),
        "c_gross": "Reduce gross violations — they weigh the most on risk.",
        "c_overspeed": "Keep to speed limits: overspeeding adds the most risk.",
        "c_fatigue": "Manage work/rest cycles — fatigue signs require breaks.",
        "c_harsh": "Practice smooth driving and safe distance (fewer harsh manoeuvres).",
        "c_video": "Avoid distractions (phone/smoking) — DMS/ADAS cameras react.",
        "c_general": "Maintain the current level and attend regular briefings.",
        "c_monitor": "Continue standard monitoring of safety indicators.",
    },
}


def _lang(lang: str | None) -> str:
    """Нормализует код языка к 'ru'/'en' ('en'* → en, иначе ru)."""
    return "en" if str(lang or "").lower().startswith("en") else "ru"


def _num(x: Any) -> str:
    """Компактное число: float без хвостовых нулей, иначе str (для текста)."""
    if isinstance(x, float):
        return f"{x:.1f}".rstrip("0").rstrip(".")
    return str(x)


def _pad3(items: list[str], fillers: list[str]) -> list[str]:
    """Ровно 3 коучинг-пункта (идея #13): дедуп, обрезать до 3, дополнить из `fillers`."""
    out: list[str] = []
    for it in [*items, *fillers]:
        if it and it not in out:
            out.append(it)
        if len(out) == 3:
            break
    return out[:3]


def _section(title: str, body: str) -> str:
    return f"{title}: {body}"


# ---------------------------------------------------------------------------
# Шаблон-ветка (детерминированная, без сети).
# ---------------------------------------------------------------------------


def _coaching_driver(report: DriverReport, t: dict[str, str]) -> list[str]:
    codes = [v.alarm_code for v in report.violations]
    gross = report.kpi.gross
    video = sum(1 for v in report.violations if v.source in _VIDEO_SOURCES)
    overspeed = sum(1 for c in codes if c in _OVERSPEED_CODES)
    fatigue = sum(1 for c in codes if c in _FATIGUE_CODES)
    harsh = sum(1 for c in codes if c in _HARSH_CODES)

    rules: list[str] = []
    if gross >= 1:
        rules.append(t["c_gross"])
    if overspeed >= 1:
        rules.append(t["c_overspeed"])
    if fatigue >= 1:
        rules.append(t["c_fatigue"])
    if harsh >= 1:
        rules.append(t["c_harsh"])
    if video >= 1:
        rules.append(t["c_video"])
    if not rules:
        rules.append(t["c_general"])
    return _pad3(rules, [t["c_general"], t["c_monitor"], t["c_video"]])


def _narrate_driver(report: DriverReport, t: dict[str, str]) -> str:
    name = report.driver.driver_name
    plate = report.vehicle_plate or "—"
    days = report.period.days

    if report.kpi.total == 0:
        summary = t["no_violations_driver"].format(
            name=name, plate=plate, days=days, d=t["days"]
        )
        return "\n".join(
            [
                _section(t["summary"], summary),
                _section(t["recognition"], t["clean_recognition"]),
            ]
        )

    summary = t["driver_summary"].format(
        name=name,
        plate=plate,
        model=report.vehicle_model,
        days=days,
        d=t["days"],
        total=report.kpi.total,
        gross=report.kpi.gross,
        safety=report.driver.safety_score,
        risk=report.driver.risk_score,
    )
    analysis = t["driver_analysis"].format(
        video=report.kpi.video_da,
        tele=report.kpi.telematics,
        mileage=_num(report.mileage_km),
        trips=report.trips,
    )
    if report.disciplinary_warning:
        analysis = f"{analysis} {t['driver_warn']}"

    coaching = "; ".join(_coaching_driver(report, t))
    recognition = t["clean_recognition"] if report.driver.safety_score >= 80 else (
        t["c_monitor"]
    )
    return "\n".join(
        [
            _section(t["summary"], summary),
            _section(t["analysis"], analysis),
            _section(t["coaching"], coaching),
            _section(t["recognition"], recognition),
        ]
    )


def _coaching_fleet(report: FleetReport, t: dict[str, str]) -> list[str]:
    rules: list[str] = []
    if report.kpi.gross >= 1:
        rules.append(t["c_gross"])
    if report.kpi.video_da >= report.kpi.telematics and report.kpi.video_da >= 1:
        rules.append(t["c_video"])
    if report.kpi.telematics >= 1:
        rules.append(t["c_harsh"])
    rules.append(t["c_monitor"])
    return _pad3(rules, [t["c_monitor"], t["c_general"], t["c_gross"]])


def _narrate_fleet(report: FleetReport, t: dict[str, str]) -> str:
    days = report.period.days
    if report.kpi.total == 0:
        summary = t["no_violations_fleet"].format(
            vehicles=report.vehicles_count, days=days, d=t["days"]
        )
        return "\n".join(
            [
                _section(t["summary"], summary),
                _section(t["recognition"], t["clean_recognition"]),
            ]
        )

    summary = t["fleet_summary"].format(
        vehicles=report.vehicles_count,
        days=days,
        d=t["days"],
        total=report.kpi.total,
        gross=report.kpi.gross,
        video=report.kpi.video_da,
        tele=report.kpi.telematics,
    )

    # Детерминированный выбор «худшего»/«лучшего» по риску (tie-break — plate).
    drivers = report.by_drivers
    analysis = ""
    recognition = t["c_monitor"]
    if drivers:
        worst = max(drivers, key=lambda r: (r.risk_score, r.gross, r.vehicle_plate))
        best = min(drivers, key=lambda r: (r.risk_score, r.gross, r.vehicle_plate))
        analysis = t["fleet_analysis_top"].format(
            plate=worst.vehicle_plate,
            driver=worst.driver.driver_name,
            risk=worst.risk_score,
            gross=worst.gross,
            total=worst.total,
        )
        recognition = t["fleet_recognition"].format(
            plate=best.vehicle_plate,
            driver=best.driver.driver_name,
            risk=best.risk_score,
        )

    coaching = "; ".join(_coaching_fleet(report, t))
    parts = [_section(t["summary"], summary)]
    if analysis:
        parts.append(_section(t["analysis"], analysis))
    parts.append(_section(t["coaching"], coaching))
    parts.append(_section(t["recognition"], recognition))
    return "\n".join(parts)


def _narrate_forecast(forecast: Any, t: dict[str, str]) -> str:
    """RiskForecast (duck-typed: .plate/.trend/.anomaly/.recommendations)."""
    trend = list(getattr(forecast, "trend", []) or [])
    horizon = len(trend)
    if trend:
        avg = sum(p.predicted_events for p in trend) / horizon
        low = min(p.ci_low for p in trend)
        high = max(p.ci_high for p in trend)
    else:
        avg = low = high = 0.0

    summary = t["forecast_summary"].format(
        plate=forecast.plate,
        horizon=horizon,
        d=t["days"],
        avg=_num(round(avg, 2)),
        low=_num(round(low, 2)),
        high=_num(round(high, 2)),
    )
    if getattr(forecast, "anomaly", False):
        reason = getattr(forecast, "anomaly_reason", None) or "—"
        analysis = t["forecast_anomaly_on"].format(reason=reason)
    else:
        analysis = t["forecast_anomaly_off"]

    recs = list(getattr(forecast, "recommendations", []) or [])
    coaching = "; ".join(_pad3(recs, [t["c_monitor"], t["c_general"], t["c_gross"]]))
    return "\n".join(
        [
            _section(t["summary"], summary),
            _section(t["analysis"], analysis),
            _section(t["coaching"], coaching),
            _section(t["recognition"], t["forecast_recognition"]),
        ]
    )


def _template(payload: Any, lang: str) -> str:
    """Детерминированный шаблон по типу payload. Никогда не падает."""
    t = _L[lang]
    if isinstance(payload, DriverReport):
        return _narrate_driver(payload, t)
    if isinstance(payload, FleetReport):
        return _narrate_fleet(payload, t)
    # Иначе — прогноз (duck-typing, чтобы не импортировать forecast_service: цикл).
    return _narrate_forecast(payload, t)


# ---------------------------------------------------------------------------
# LLM-ветка (опц., Groq). Переписывает шаблон без новых фактов; ошибка → шаблон.
# ---------------------------------------------------------------------------

_GROQ_MODEL = "llama-3.3-70b-versatile"
_GROQ_SYSTEM = (
    "Ты — помощник по безопасности автопарка. Перепиши переданный отчёт более "
    "связно и человечно, СОХРАНИВ структуру (резюме, анализ причин, 3 пункта "
    "коучинга, признание). СТРОГО запрещено добавлять или менять числа и факты — "
    "используй только то, что есть в тексте. Ответь на том же языке, что и вход."
)


def _narrate_llm(template_text: str, lang: str) -> str | None:
    """Groq-усиление шаблона. None при отсутствии ключа / любой ошибке."""
    api_key = getattr(settings, "groq_api_key", None)
    if not api_key:
        return None
    try:
        from groq import Groq  # ленивый импорт: не требуется без ключа.

        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model=_GROQ_MODEL,
            messages=[
                {"role": "system", "content": _GROQ_SYSTEM},
                {"role": "user", "content": template_text},
            ],
            temperature=0,
        )
        text = (completion.choices[0].message.content or "").strip()
        return text or None
    except Exception:  # нет пакета / сеть / квота / любой сбой → шаблон.
        return None


# ---------------------------------------------------------------------------
# Публичный API.
# ---------------------------------------------------------------------------


def narrate(
    payload: DriverReport | FleetReport | Any,
    lang: str | None = "ru",
    *,
    use_llm: bool = True,
) -> str:
    """Собирает нарратив из отчёта/прогноза (§8.4, идеи #12/#13).

    Всегда возвращает непустой текст. Шаблон — детерминированный фолбэк; при
    наличии ключа Groq и `use_llm` пытается «усилить» текст LLM, ошибка → шаблон.
    """
    code = _lang(lang)
    template_text = _template(payload, code)
    if use_llm:
        enhanced = _narrate_llm(template_text, code)
        if enhanced:
            return enhanced
    return template_text
