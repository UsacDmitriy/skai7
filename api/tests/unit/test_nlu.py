"""Unit-покрытие NLU regex-fallback (b9) — §7.3/§7.5.

Дополняет t1/`test_nlu_service` (там — публичный `parse`): здесь фокус на
детерминированных хелперах разбора (период/госномер/ФИО/разрез) и контракте
безопасного дефолта на мусоре. Всё в regex-ветке (`no_groq`), без сети.
"""

from __future__ import annotations

import pytest

from api.domain.reports import ReportQuery
from api.services import nlu_service as nlu


# ---------------------------------------------------------------------------
# Публичный parse (regex-ветка) — driver/fleet/безопасный дефолт.
# ---------------------------------------------------------------------------


class TestParseFallback:
    def test_driver_by_name_and_period(self, no_groq) -> None:
        q = nlu.parse("Нарушения Иванова за 3 дня")
        assert q.kind == "driver"
        assert q.driver_name is not None and "Иванов" in q.driver_name
        assert q.period_days == 3

    def test_fleet_for_park(self, no_groq) -> None:
        q = nlu.parse("отчёт по парку")
        assert q.kind == "fleet"

    @pytest.mark.parametrize("text", ["", "   ", "asdf 123 !!!", "??? %%% ###"])
    def test_garbage_is_safe_default_not_exception(self, no_groq, text: str) -> None:
        q = nlu.parse(text)
        assert isinstance(q, ReportQuery)
        assert q.kind == "fleet"
        assert q.period_days == 3


# ---------------------------------------------------------------------------
# Детерминированные хелперы regex-парсера.
# ---------------------------------------------------------------------------


class TestHelpers:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("за 5 дней", 5),
            ("за неделю", 7),
            ("за месяц", 30),
            ("без периода", 3),  # дефолт
            ("за 99999 дней", 365),  # clamp
        ],
    )
    def test_detect_period(self, text: str, expected: int) -> None:
        assert nlu._detect_period(text.lower()) == expected

    @pytest.mark.parametrize(
        "low,expected",
        [
            ("по машинам", "vehicles"),
            ("разрез по тс", "vehicles"),
            ("по водителям", "drivers"),
            ("просто текст", None),
        ],
    )
    def test_detect_view(self, low: str, expected) -> None:
        assert nlu._detect_view(low) == expected

    def test_detect_plate_ru_normalized(self) -> None:
        assert nlu._detect_plate("номер а 123 вс 77") == "А123ВС77"

    def test_detect_plate_kk(self) -> None:
        assert nlu._detect_plate("борт 123ABC02") == "123ABC02"

    def test_detect_plate_absent(self) -> None:
        assert nlu._detect_plate("нет тут номера") is None

    def test_detect_name_skips_stopwords(self) -> None:
        # «Нарушения» — служебное слово, отсекается; остаётся ФИО.
        name = nlu._detect_name("Нарушения Петрова Сергея")
        assert name is not None
        assert "Петров" in name and "Нарушения" not in name

    def test_plate_priority_over_name(self, no_groq) -> None:
        q = nlu.parse("Нарушения Иванова А123ВС77 за неделю")
        assert q.kind == "driver"
        assert q.plate == "А123ВС77"
        assert q.period_days == 7
