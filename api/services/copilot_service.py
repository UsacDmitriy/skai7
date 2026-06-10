"""Fleet Copilot — разговорный ассистент автопарка (b21, §8.3/§8.4, идея #13).

`POST /api/copilot/chat` → `CopilotMessage`: свободный запрос (RU/EN) → выбор
инструмента из данных SKAI → ответ с нарративом + сырыми данными.

Архитектура двухветочная (паттерн `nlu_service`, §8.0):
  * **Groq-ветка** (`settings.groq_api_key`) — structured tool-selection
    (`temperature=0`, JSON) + нарратив ответа. Бросает при любой ошибке.
  * **Детерминированный фолбэк** — правила-роутинг по ключевым словам RU/EN →
    тот же tool → шаблонный цитирующий ответ. **Никогда не падает** (минимум —
    вежливое «уточните запрос»).

Tools — тонкие обёртки над существующими сервисами (incidents / reports /
forecast / zones / fatigue / sabotage); бизнес-логику не дублируем.

Governance (§8.6/§8.7/§8.9):
  * мета `AiFeatureState` (поле `state`) через `ai_call` (latency-budget,
    деградация без сети);
  * **цитирование фактов** — в `text` ссылаемся на id из системы (инцидент/
    отчёт/зона/ТС), числа не выдумываем;
  * **audit-trail** — каждый вызов tool best-effort пишется в `output/audit.csv`,
    событие `copilot_tool_success` отдаётся в метрики (b25), если те доступны.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

import duckdb
from pydantic import BaseModel

from api.core.ai_flags import AiFeatureState
from api.core.ai_runtime import ai_call
from api.core.config import settings
from api.core.duckdb_conn import get_connection
from api.domain.reports import ReportQuery
from api.services import (
    fatigue_service,
    forecast_service,
    incidents_service,
    nlu_service,
    reports_service,
    sabotage_service,
    zones_service,
)

# Модель Groq берём из конфига, если поле задано (config-овнер — core, не трогаем);
# иначе тот же дефолт, что у nlu_service. Без ключа ветка вообще не активируется.
_GROQ_MODEL = (
    getattr(settings, "copilot_model", None)
    or getattr(settings, "groq_model", None)
    or "llama-3.3-70b-versatile"
)

_MAX_ITEMS = 20  # клампим размеры списков в `data`, чтобы payload оставался разумным.


# ---------------------------------------------------------------------------
# Схемы ответа (§8.4). Держим в сервисе (как forecast/scene), общий
# entities.py не правим — иначе кросс-трек гонка в одном worktree.
# ---------------------------------------------------------------------------


class ToolCall(BaseModel):
    """Зафиксированный вызов инструмента (§8.4): имя сервиса + аргументы."""

    name: str
    args: dict[str, Any] = {}


class CopilotMessage(BaseModel):
    """Ответ ассистента (§8.4) + governance-мета (§8.6)."""

    role: str = "assistant"            # 'user' | 'assistant'
    text: str
    lang: str                          # 'ru' | 'en'
    tool_calls: list[ToolCall] = []
    data: Any | None = None
    state: AiFeatureState | None = None


# ---------------------------------------------------------------------------
# Язык запроса (кириллица → ru).
# ---------------------------------------------------------------------------


def _detect_lang(text: str) -> str:
    """Кириллица в тексте → 'ru', иначе 'en' (Check: ответ на языке запроса)."""
    for ch in text or "":
        if "а" <= ch.lower() <= "я" or ch.lower() == "ё":
            return "ru"
    return "en"


# ---------------------------------------------------------------------------
# Извлечение сущностей — переиспользуем детерминированные офлайн-парсеры nlu
# (без сети), чтобы не дублировать regex госномера/ФИО/периода.
# ---------------------------------------------------------------------------


def _entities(text: str) -> dict[str, Any]:
    low = (text or "").lower()
    return {
        "plate": nlu_service._detect_plate(text or ""),
        "name": nlu_service._detect_name(text or ""),
        "period": nlu_service._detect_period(low),
        "view": nlu_service._detect_view(low),
    }


# ---------------------------------------------------------------------------
# Результат одного инструмента: данные + цитируемые id + двуязычный нарратив.
# ---------------------------------------------------------------------------


@dataclass
class _TR:
    data: Any
    cites: list[str]
    ru: str
    en: str


@dataclass
class _Outcome:
    """Итог обработки запроса: вызовы tools + данные + двуязычный текст."""

    tool_calls: list[ToolCall]
    data: Any
    ru: str
    en: str

    def text(self, lang: str) -> str:
        return self.ru if lang == "ru" else self.en


def _clean_args(args: dict[str, Any]) -> dict[str, Any]:
    """Убираем None/пустые — в `tool_calls.args` остаются только заданные параметры."""
    return {k: v for k, v in args.items() if v not in (None, "", [])}


def _dump(obj: Any) -> Any:
    """Pydantic-модель / список моделей → JSON-совместимая структура."""
    if isinstance(obj, list):
        return [o.model_dump() if isinstance(o, BaseModel) else o for o in obj]
    return obj.model_dump() if isinstance(obj, BaseModel) else obj


# ---------------------------------------------------------------------------
# Tools — тонкие обёртки над сервисами. None ⇒ инструмент неприменим
# (нет ТС / нет сущности) → роутер деградирует.
# ---------------------------------------------------------------------------


def _tool_list_incidents(db: duckdb.DuckDBPyConnection, args: dict[str, Any]) -> _TR:
    filters: dict[str, Any] = {}
    if args.get("plate"):
        filters["vehicle_plate"] = args["plate"]
    if args.get("alarm_code"):
        filters["alarm_code"] = args["alarm_code"]
    if args.get("status"):
        filters["status"] = args["status"]
    items = incidents_service.list_summaries(db, filters or None)[:_MAX_ITEMS]
    cites = [i.id for i in items]
    sample = ", ".join(cites[:3])
    ru = (
        f"Найдено инцидентов: {len(items)}."
        + (f" Примеры: {sample}." if cites else " Совпадений нет.")
    )
    en = (
        f"Incidents found: {len(items)}."
        + (f" Examples: {sample}." if cites else " No matches.")
    )
    return _TR(_dump(items), cites, ru, en)


def _tool_driver_report(db: duckdb.DuckDBPyConnection, args: dict[str, Any]) -> _TR | None:
    plate = args.get("plate")
    name = args.get("driver_name")
    if not plate and not name:
        return None  # без сущности driver-отчёт бессмыслен → деградация.
    q = ReportQuery(
        kind="driver", plate=plate, driver_name=name,
        period_days=args.get("period_days") or 3,
    )
    rep = reports_service.report_for_query(db, q)
    d = rep.driver  # report_for_query при kind=driver всегда вернёт DriverReport.
    cites = [d.driver_id]
    ru = (
        f"{d.driver_name} ({rep.vehicle_plate}): риск {d.risk_score}, "
        f"безопасность {d.safety_score}, нарушений за период {len(rep.violations)}."
    )
    en = (
        f"{d.driver_name} ({rep.vehicle_plate}): risk {d.risk_score}, "
        f"safety {d.safety_score}, violations in period {len(rep.violations)}."
    )
    return _TR(_dump(rep), cites, ru, en)


def _tool_fleet_report(db: duckdb.DuckDBPyConnection, args: dict[str, Any]) -> _TR:
    rep = reports_service.fleet_report(
        db, args.get("period_days") or 3, args.get("view") or "drivers"
    )
    top = rep.by_drivers[:3]
    cites = [r.driver.driver_id for r in top]
    top_ru = "; ".join(f"{r.driver.driver_name} ({r.risk_score})" for r in top)
    ru = (
        f"Парк: {rep.vehicles_count} ТС."
        + (f" Топ по риску: {top_ru}." if top else "")
    )
    en = (
        f"Fleet: {rep.vehicles_count} vehicles."
        + (f" Top by risk: {top_ru}." if top else "")
    )
    return _TR(_dump(rep), cites, ru, en)


def _tool_forecast(db: duckdb.DuckDBPyConnection, args: dict[str, Any]) -> _TR | None:
    plate = args.get("plate")
    if not plate or not forecast_service.plate_exists(db, plate):
        return None  # нет валидного ТС → деградация (роутер уйдёт в зоны/парк).
    f = forecast_service.forecast(db, plate)
    cites = [plate]
    anomaly_ru = "обнаружена" if f.anomaly else "не обнаружена"
    anomaly_en = "detected" if f.anomaly else "not detected"
    ru = (
        f"Прогноз по {plate}: аномалия {anomaly_ru}"
        + (f" ({f.anomaly_reason})" if f.anomaly and f.anomaly_reason else "")
        + f". Рекомендаций: {len(f.recommendations)}."
    )
    en = (
        f"Forecast for {plate}: anomaly {anomaly_en}. "
        f"Recommendations: {len(f.recommendations)}."
    )
    return _TR(_dump(f), cites, ru, en)


def _tool_zones(db: duckdb.DuckDBPyConnection, args: dict[str, Any]) -> _TR:
    zones = zones_service.compute_zones(db, args.get("kind"), args.get("hour"))
    top = sorted(zones, key=lambda z: z.avg_risk, reverse=True)[:_MAX_ITEMS]
    cites = [z.zone_id for z in top]
    head = top[:3]
    head_ru = "; ".join(f"{z.zone_id} (риск {z.avg_risk:.0f})" for z in head)
    head_en = "; ".join(f"{z.zone_id} (risk {z.avg_risk:.0f})" for z in head)
    ru = (
        f"Зон риска: {len(zones)}."
        + (f" Наиболее опасные: {head_ru}." if head else " Зоны не выделены.")
    )
    en = (
        f"Risk zones: {len(zones)}."
        + (f" Most dangerous: {head_en}." if head else " No zones detected.")
    )
    return _TR(_dump(top), cites, ru, en)


def _tool_fatigue(db: duckdb.DuckDBPyConnection, args: dict[str, Any]) -> _TR:
    chains = fatigue_service.chains(db, args.get("plate"))[:_MAX_ITEMS]
    cites = [c.plate for c in chains]
    sample = ", ".join(cites[:3])
    ru = (
        f"Цепочек усталости: {len(chains)}."
        + (f" ТС: {sample}." if cites else " Признаков усталости не найдено.")
    )
    en = (
        f"Fatigue chains: {len(chains)}."
        + (f" Vehicles: {sample}." if cites else " No fatigue signs found.")
    )
    return _TR(_dump(chains), cites, ru, en)


def _tool_sabotage(db: duckdb.DuckDBPyConnection, args: dict[str, Any]) -> _TR:
    events = sabotage_service.list_sabotage(db)[:_MAX_ITEMS]
    cites = [e.id for e in events]
    sample = ", ".join(cites[:3])
    ru = (
        f"Событий саботажа: {len(events)}."
        + (f" Примеры: {sample}." if cites else " Саботаж не зафиксирован.")
    )
    en = (
        f"Sabotage events: {len(events)}."
        + (f" Examples: {sample}." if cites else " No sabotage detected.")
    )
    return _TR(_dump(events), cites, ru, en)


# Реестр инструментов (имя как в §8.4 / каталоге Groq).
_TOOLS: dict[str, Callable[[duckdb.DuckDBPyConnection, dict[str, Any]], _TR | None]] = {
    "list_incidents": _tool_list_incidents,
    "driver_report": _tool_driver_report,
    "fleet_report": _tool_fleet_report,
    "forecast": _tool_forecast,
    "zones": _tool_zones,
    "fatigue": _tool_fatigue,
    "sabotage": _tool_sabotage,
}


# ---------------------------------------------------------------------------
# Сравнение водителей (несколько tool_calls в одном ответе).
# ---------------------------------------------------------------------------

# Слова, ошибочно похожие на ФИО при сравнении (отсекаем из кандидатов).
_COMPARE_STOP = {"compare", "drivers", "driver", "who", "show", "and", "vs", "versus",
                 "сравни", "сравнить", "сравнение", "водител", "водителей", "против"}


def _candidate_drivers(text: str, ents: dict[str, Any]) -> list[dict[str, Any]]:
    """До 2 кандидатов для сравнения: госномера (приоритет) + ФИО-подобные слова."""
    out: list[dict[str, Any]] = []
    for m in nlu_service._PLATE_RU_RE.finditer(text):
        out.append({"plate": m.group(0).upper().replace(" ", "")})
    if not out:  # ФИО только если явных госномеров нет.
        for w in nlu_service._WORD_RE.findall(text):
            if w.lower() not in nlu_service._STOPWORDS and w.lower() not in _COMPARE_STOP:
                out.append({"driver_name": w})
    # уникализируем, сохраняя порядок.
    seen: set[str] = set()
    uniq: list[dict[str, Any]] = []
    for e in out:
        key = e.get("plate") or e.get("driver_name") or ""
        if key and key not in seen:
            seen.add(key)
            uniq.append(e)
    return uniq[:2]


def _compare(db: duckdb.DuckDBPyConnection, text: str, ents: dict[str, Any]) -> _Outcome:
    cands = _candidate_drivers(text, ents)
    if not cands:  # некого сравнивать → деградируем в сводку по парку.
        return _outcome_from_tool(db, "fleet_report", {"period_days": ents.get("period")})

    reports: list[dict[str, Any]] = []
    calls: list[ToolCall] = []
    cites: list[str] = []
    for e in cands:
        q = ReportQuery(
            kind="driver", plate=e.get("plate"), driver_name=e.get("driver_name"),
            period_days=ents.get("period") or 3,
        )
        rep = reports_service.report_for_query(db, q)
        reports.append(rep.model_dump())
        calls.append(ToolCall(name="driver_report", args=_clean_args(e)))
        cites.append(rep.driver.driver_id)

    def _line(r: dict[str, Any]) -> str:
        d = r["driver"]
        return f"{d['driver_name']} (риск {d['risk_score']}, безопасность {d['safety_score']})"

    def _line_en(r: dict[str, Any]) -> str:
        d = r["driver"]
        return f"{d['driver_name']} (risk {d['risk_score']}, safety {d['safety_score']})"

    ru = "Сравнение: " + " vs ".join(_line(r) for r in reports) + "."
    en = "Comparison: " + " vs ".join(_line_en(r) for r in reports) + "."
    return _Outcome(calls, reports, ru, en)


# ---------------------------------------------------------------------------
# Детерминированный роутинг по ключевым словам (RU/EN). Никогда не падает.
# ---------------------------------------------------------------------------


def _has(low: str, *subs: str) -> bool:
    return any(s in low for s in subs)


def _route(low: str, ents: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    """Текст → (имя tool | None, args). None ⇒ вежливая просьба уточнить.

    Спец-значение "compare" обрабатывается отдельно (несколько tool_calls).
    """
    plate, name = ents.get("plate"), ents.get("name")
    period, view = ents.get("period"), ents.get("view")

    if _has(low, "сравни", "сравнен", "compare", " vs ", "versus", "против"):
        return "compare", {}
    if _has(low, "усталост", "засыпа", "зевот", "сонлив", "fatigue", "drowsy",
            "tired", "asleep"):
        return "fatigue", {"plate": plate}
    if _has(low, "саботаж", "залеп", "заклеен", "закрыл камер", "sabotage", "tamper",
            "cover camera", "camera dark", "blocked camera"):
        return "sabotage", {}
    if _has(low, "прогноз", "тренд", "предсказ", "forecast", "predict", "trend"):
        if plate:
            return "forecast", {"plate": plate}
        return "zones", {}  # прогноз без ТС → карта зон риска.
    if _has(low, "зон", "группе риска", "в группе риска", "риск", "опасн", "горяч",
            "zone", "risk", "danger", "hotspot", "at risk"):
        return "zones", {}
    if plate or name:  # явная сущность без иного намерения → отчёт по водителю.
        return "driver_report", {"plate": plate, "driver_name": name, "period_days": period}
    if _has(low, "инцидент", "нарушени", "событи", "alarm", "incident", "violation",
            "event"):
        return "list_incidents", {}
    if _has(low, "парк", "сводк", "обзор", "статист", "fleet", "summary", "overview"):
        return "fleet_report", {"period_days": period, "view": view}
    return None, {}


def _outcome_from_tool(
    db: duckdb.DuckDBPyConnection, tool: str, args: dict[str, Any]
) -> _Outcome:
    """Выполнить один tool и собрать `_Outcome`. Неприменимый tool (None) → парк."""
    fn = _TOOLS.get(tool)
    tr = fn(db, args) if fn else None
    if tr is None:
        if tool == "fleet_report":  # защита от рекурсии, если парк сам вернул None.
            tr = _tool_fleet_report(db, {})
            tool, args = "fleet_report", {}
        else:
            return _outcome_from_tool(db, "fleet_report", {})
    return _Outcome([ToolCall(name=tool, args=_clean_args(args))], tr.data, tr.ru, tr.en)


def _fallback_outcome(
    db: duckdb.DuckDBPyConnection, text: str, ents: dict[str, Any]
) -> _Outcome:
    """Детерминированная ветка: правила-роутинг → tool → шаблонный ответ."""
    low = (text or "").lower()
    tool, args = _route(low, ents)
    if tool is None:
        return _Outcome(
            [], None,
            "Уточните запрос: спросите про инциденты, отчёт по водителю/парку, "
            "прогноз, зоны риска, усталость или саботаж.",
            "Please clarify: ask about incidents, a driver/fleet report, forecast, "
            "risk zones, fatigue or sabotage.",
        )
    if tool == "compare":
        return _compare(db, text, ents)
    return _outcome_from_tool(db, tool, args)


# ---------------------------------------------------------------------------
# Groq-ветка (основной путь): structured tool-selection + нарратив.
# Бросает при любой ошибке → ai_call уводит в детерминированный фолбэк.
# ---------------------------------------------------------------------------

_GROQ_CATALOG = (
    "Ты диспетчер автопарка SKAI. Выбери ОДИН инструмент для ответа и верни СТРОГО "
    "JSON-объект {\"tool\": <имя>, \"args\": {...}}. Доступные инструменты:\n"
    "  list_incidents {plate?, alarm_code?, status?} — лента инцидентов/нарушений\n"
    "  driver_report {plate?, driver_name?, period_days?} — отчёт по водителю/ТС\n"
    "  fleet_report {period_days?, view?} — сводка по парку (рейтинг риска)\n"
    "  forecast {plate} — прогноз нарушений по ТС на 7 дней + аномалия\n"
    "  zones {kind?, hour?} — карта зон риска (кто/где в группе риска)\n"
    "  fatigue {plate?} — цепочки усталости водителей\n"
    "  sabotage {} — события саботажа камер\n"
    "Только эти имена. Без пояснений вне JSON."
)

_GROQ_NARRATE = (
    "Ты ассистент автопарка SKAI. Кратко и по делу ответь на вопрос диспетчера на "
    "его языке, опираясь ТОЛЬКО на переданные данные. Ссылайся на конкретные id "
    "(инцидент/зона/ТС), не выдумывай числа. 1–3 предложения."
)


def _groq_outcome(
    db: duckdb.DuckDBPyConnection, text: str, lang: str, ents: dict[str, Any]
) -> _Outcome:
    api_key = getattr(settings, "groq_api_key", None)
    if not api_key:
        raise RuntimeError("groq_api_key не задан")

    from groq import Groq  # ленивый импорт: не требуется без ключа.

    client = Groq(api_key=api_key)

    # 1) structured tool-selection.
    sel = client.chat.completions.create(
        model=_GROQ_MODEL,
        messages=[
            {"role": "system", "content": _GROQ_CATALOG},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    choice = json.loads(sel.choices[0].message.content)
    tool = choice.get("tool")
    args = dict(choice.get("args") or {})
    # дозаполняем сущностями из текста (LLM может их опустить).
    args.setdefault("plate", ents.get("plate"))
    args.setdefault("driver_name", ents.get("name"))
    args.setdefault("period_days", ents.get("period"))
    args.setdefault("view", ents.get("view"))

    if tool == "compare":
        outcome = _compare(db, text, ents)
    elif tool in _TOOLS:
        outcome = _outcome_from_tool(db, tool, args)
    else:
        raise RuntimeError(f"неизвестный tool: {tool!r}")

    # 2) нарратив поверх данных (фактическая часть уже в outcome — это «обёртка b22»).
    try:
        narr = client.chat.completions.create(
            model=_GROQ_MODEL,
            messages=[
                {"role": "system", "content": _GROQ_NARRATE},
                {"role": "user", "content": json.dumps(
                    {"question": text, "lang": lang,
                     "facts": outcome.text(lang), "data": outcome.data},
                    ensure_ascii=False, default=str,
                )},
            ],
            temperature=0,
        )
        ntext = (narr.choices[0].message.content or "").strip()
        if ntext:
            if lang == "ru":
                outcome.ru = ntext
            else:
                outcome.en = ntext
    except Exception:
        pass  # нарратив необязателен: остаётся детерминированный шаблон.

    return outcome


# ---------------------------------------------------------------------------
# Audit-trail (b26) + метрики (b25) — best-effort, никогда не бросает.
# ---------------------------------------------------------------------------

_AUDIT_HEADER = ["ts", "event", "feature", "tool", "lang", "source", "args"]


def _audit(tool_calls: list[ToolCall], lang: str, source: str) -> None:
    """Пишем каждый вызов tool в `output/audit.csv` и шлём событие в метрики (b25).

    Полностью изолировано try/except: сбой логирования не должен ронять чат и не
    влияет на детерминизм ответа (это сайд-эффект, не часть `CopilotMessage`).
    """
    if not tool_calls:
        return
    try:
        path = settings.output_dir / "audit.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        is_new = not path.exists()
        ts = datetime.now(timezone.utc).isoformat()
        with path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            if is_new:
                writer.writerow(_AUDIT_HEADER)
            for call in tool_calls:
                writer.writerow([
                    ts, "copilot_tool_success", "copilot", call.name, lang, source,
                    json.dumps(call.args, ensure_ascii=False),
                ])
    except Exception:
        pass

    # Событие в метрики (b25) — если сервис уже существует в этой волне.
    try:
        from api.services import metrics_service  # type: ignore

        recorder = getattr(metrics_service, "record_event", None)
        if callable(recorder):
            for call in tool_calls:
                recorder("copilot_tool_success", {"tool": call.name, "source": source})
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Публичный API (§8.3).
# ---------------------------------------------------------------------------


def chat(
    text: str,
    lang: str | None = None,
    db: duckdb.DuckDBPyConnection | None = None,
) -> CopilotMessage:
    """Свободный запрос → `CopilotMessage`. Groq → except → детерминированный фолбэк.

    Никогда не падает: нет ключа/сети/БД/мусорный ввод → вежливый валидный ответ.
    `lang` определяется по тексту, если не задан явно (Check: ответ на языке запроса).
    """
    lang = lang or _detect_lang(text or "")
    ents = _entities(text or "")

    # БД: переданный курсор (роутер) или процессный коннект (прямой вызов/тесты).
    if db is None:
        try:
            db = get_connection()
        except Exception:
            return CopilotMessage(
                role="assistant", lang=lang, tool_calls=[], data=None,
                text=("База данных недоступна — соберите её командой `make db`."
                      if lang == "ru" else "Database unavailable — run `make db`."),
                state=AiFeatureState(
                    name="copilot", enabled=True, source="fallback", latency_ms=0.0
                ),
            )

    # Governance: live-ветка под latency-budget; ошибка/таймаут → фолбэк (§8.6).
    state, outcome = ai_call(
        feature="copilot",
        fn=lambda: _groq_outcome(db, text or "", lang, ents),
        fallback=None,
    )
    if outcome is None:  # Groq недоступен/упал → детерминированный фолбэк.
        outcome = _fallback_outcome(db, text or "", ents)
        state = AiFeatureState(
            name="copilot", enabled=True, source="fallback",
            latency_ms=state.latency_ms,
        )

    _audit(outcome.tool_calls, lang, state.source)

    return CopilotMessage(
        role="assistant",
        text=outcome.text(lang),
        lang=lang,
        tool_calls=outcome.tool_calls,
        data=outcome.data,
        state=state,
    )
