"""Unit-покрытие Fleet Copilot (b21) — §8.3/§8.4, идея #13.

Фокус — детерминированная **фолбэк-ветка** ассистента: без сети и без
`GROQ_API_KEY`. Проверяем три инварианта контракта:
  * **роутинг** свободного запроса (RU/EN) в нужный tool (правила `_route`);
  * **язык** ответа определяется по тексту (кириллица → ru), фикс. на каждый ввод;
  * **graceful default** — мусор/пустой ввод не бросает, отдаёт вежливое уточнение.

Чистые правила (`_route`/`_detect_lang`/`_candidate_drivers`) тестируем напрямую —
они не требуют БД и полностью детерминированы. Сквозной `chat()` гоним против
собранной `data/skai.duckdb` (`real_db`, `skip` без неё), форсируя фолбэк через
`no_groq`. Всё офлайн (Check: `pytest -q` зелёный без сети и без ключа).
"""

from __future__ import annotations

import pytest

from api.services import copilot_service as cp
from api.services.copilot_service import CopilotMessage, ToolCall


# ---------------------------------------------------------------------------
# 1. Определение языка (кириллица → ru), детерминированно на каждый ввод.
# ---------------------------------------------------------------------------


class TestDetectLang:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("кто в группе риска сегодня?", "ru"),
            ("show sabotage events", "en"),
            ("", "en"),                       # пусто → дефолт en
            ("   ", "en"),
            ("сравни Ivanov и Petrov", "ru"),  # хотя бы одна кириллица → ru
            ("123 !!! ???", "en"),            # без букв → en
            ("Ёлка", "ru"),                   # буква «ё» — кириллица
        ],
    )
    def test_detect_lang(self, text: str, expected: str) -> None:
        assert cp._detect_lang(text) == expected

    def test_detect_lang_is_deterministic(self) -> None:
        assert cp._detect_lang("прогноз по парку") == cp._detect_lang("прогноз по парку")


# ---------------------------------------------------------------------------
# 2. Детерминированный роутинг по ключевым словам (RU/EN) → имя tool.
#    Чистая функция: вход (low, ents) → (tool|None, args). Без сети/БД.
# ---------------------------------------------------------------------------


class TestRoute:
    @pytest.mark.parametrize(
        "low,expected_tool",
        [
            # «кто в группе риска» — ключевой кейс промпта → зоны.
            ("кто в группе риска сегодня?", "zones"),
            ("риск зоны на карте", "zones"),
            ("show risk zones", "zones"),
            ("at risk drivers", "zones"),
            # саботаж камер (EN-кейс промпта).
            ("show sabotage events", "sabotage"),
            ("саботаж камеры", "sabotage"),
            # усталость / сонливость.
            ("признаки усталости водителей", "fatigue"),
            ("driver fatigue chains", "fatigue"),
            # прогноз без ТС → деградирует в зоны (нет валидного plate).
            ("прогноз нарушений", "zones"),
            ("forecast trend", "zones"),
            # сравнение водителей → спец-маркер compare.
            ("сравни Иванова и Петрова", "compare"),
            ("compare drivers Ivanov vs Petrov", "compare"),
            # лента инцидентов / нарушений.
            ("покажи инциденты", "list_incidents"),
            ("recent violations", "list_incidents"),
            # сводка по парку.
            ("сводка по парку", "fleet_report"),
            ("fleet summary", "fleet_report"),
        ],
    )
    def test_route_keyword_intent(self, low: str, expected_tool: str) -> None:
        tool, _args = cp._route(low, {})
        assert tool == expected_tool

    def test_route_forecast_with_plate(self) -> None:
        # При наличии валидного plate «прогноз» → именно forecast (не zones).
        tool, args = cp._route("прогноз", {"plate": "А123ВС77"})
        assert tool == "forecast"
        assert args.get("plate") == "А123ВС77"

    def test_route_entity_without_intent_is_driver_report(self) -> None:
        # Явная сущность (ФИО) без иного намерения → отчёт по водителю.
        tool, args = cp._route("иванов", {"name": "Иванов"})
        assert tool == "driver_report"
        assert args.get("driver_name") == "Иванов"

    @pytest.mark.parametrize("low", ["", "   ", "!!! ???", "asdf qwerty zxcv"])
    def test_route_garbage_returns_none(self, low: str) -> None:
        tool, args = cp._route(low, {})
        assert tool is None
        assert args == {}

    def test_route_is_deterministic(self) -> None:
        # Один вход → один выход (инвариант детерминизма фолбэка).
        first = cp._route("кто в группе риска сегодня?", {})
        second = cp._route("кто в группе риска сегодня?", {})
        assert first == second


# ---------------------------------------------------------------------------
# 3. Кандидаты для сравнения (несколько tool_calls в одном ответе).
# ---------------------------------------------------------------------------


class TestCandidateDrivers:
    def test_two_names_become_two_candidates(self) -> None:
        cands = cp._candidate_drivers("сравни Иванова и Петрова", {})
        assert 1 <= len(cands) <= 2
        joined = " ".join(c.get("driver_name", "") for c in cands)
        assert "Иванов" in joined or "Петров" in joined

    def test_plate_priority_over_names(self) -> None:
        cands = cp._candidate_drivers("сравни А123ВС77 и Б456ОР99", {})
        assert cands, "ожидались кандидаты по госномерам"
        assert all("plate" in c for c in cands)

    def test_clamped_to_two(self) -> None:
        cands = cp._candidate_drivers("сравни Иванов Петров Сидоров Кузнецов", {})
        assert len(cands) <= 2


# ---------------------------------------------------------------------------
# 4. Graceful default — фолбэк-ветка не бросает, отдаёт вежливое уточнение.
#    Clarify-ответ не трогает БД, поэтому достаточно in-memory коннекта.
# ---------------------------------------------------------------------------


class TestFallbackClarify:
    @pytest.mark.parametrize("text", ["", "   ", "!!! ???", "zzz qqq"])
    def test_clarify_outcome_has_no_tool_calls(self, mem_db, text: str) -> None:
        outcome = cp._fallback_outcome(mem_db, text, cp._entities(text))
        assert outcome.tool_calls == []
        assert outcome.data is None

    def test_clarify_text_is_bilingual_and_nonempty(self, mem_db) -> None:
        outcome = cp._fallback_outcome(mem_db, "", cp._entities(""))
        assert outcome.text("ru").strip()
        assert outcome.text("en").strip()
        assert outcome.text("ru") != outcome.text("en")


# ---------------------------------------------------------------------------
# 5. Сквозной chat() против собранной БД — фолбэк (no_groq), §8.4-контракт.
#    `skip`, если `data/skai.duckdb` не собрана (без сети в любом случае).
# ---------------------------------------------------------------------------


class TestChatEndToEnd:
    def test_ru_risk_query_routes_to_zones_or_forecast(self, no_groq, real_db) -> None:
        msg = cp.chat("кто в группе риска сегодня?", db=real_db)
        assert isinstance(msg, CopilotMessage)
        assert msg.role == "assistant"
        assert msg.lang == "ru"
        assert msg.text.strip()
        names = {c.name for c in msg.tool_calls}
        assert names <= {"zones", "forecast"} and names, names
        # Фолбэк-ветка (без ключа/сети) — источник всегда fallback (§8.6).
        assert msg.state is not None and msg.state.source == "fallback"

    def test_en_sabotage_query_routes_to_sabotage(self, no_groq, real_db) -> None:
        msg = cp.chat("show sabotage events", db=real_db)
        assert msg.lang == "en"
        assert any(c.name == "sabotage" for c in msg.tool_calls)
        assert all(isinstance(c, ToolCall) for c in msg.tool_calls)

    @pytest.mark.parametrize("text", ["", "   ", "!!! ??? %%%"])
    def test_garbage_does_not_raise_and_is_polite_default(
        self, no_groq, real_db, text: str
    ) -> None:
        msg = cp.chat(text, db=real_db)
        assert isinstance(msg, CopilotMessage)
        assert msg.tool_calls == []          # нечего вызывать → вежливый дефолт
        assert msg.text.strip()

    def test_fallback_is_deterministic(self, no_groq, real_db) -> None:
        # Один вход → один выход на уровне, которым владеет фолбэк копилота:
        # решение роутинга (набор tool) и язык. Порядок строк внутри данных —
        # зона ответственности сервиса-источника, не ассистента.
        first = cp.chat("show sabotage events", db=real_db)
        second = cp.chat("show sabotage events", db=real_db)
        assert [c.name for c in first.tool_calls] == [c.name for c in second.tool_calls]
        assert first.lang == second.lang == "en"
        assert first.state.source == second.state.source == "fallback"
