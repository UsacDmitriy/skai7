"""Tests for b9 — nlu_service.parse (CONTRACT §7.3/§7.5).

Все тесты — без сети и без GROQ_API_KEY (regex-ветка). Проверяют контракт
Check: импорт без groq, корректный разбор driver/fleet/период/view,
безопасный дефолт на пустом/мусорном входе, тип ReportQuery на обеих ветках.
"""

from __future__ import annotations

from api.domain.reports import ReportQuery
from api.services.nlu_service import parse


def test_import_without_groq() -> None:
    # Импорт и вызов работают без сети и без ключа.
    assert callable(parse)


def test_driver_by_name() -> None:
    q = parse("Нарушения Иванова за 3 дня")
    assert q.kind == "driver"
    assert q.driver_name is not None and "Иванов" in q.driver_name
    assert q.period_days == 3


def test_fleet_week_vehicles() -> None:
    q = parse("отчёт по парку за неделю по ТС")
    assert q.kind == "fleet"
    assert q.period_days == 7
    assert q.view == "vehicles"


def test_empty_safe_default() -> None:
    q = parse("")
    assert isinstance(q, ReportQuery)
    assert q.kind == "fleet"
    assert q.period_days == 3


def test_whitespace_and_garbage() -> None:
    for text in ("   ", "asdf 123 !!!"):
        q = parse(text)
        assert isinstance(q, ReportQuery)
        assert q.kind == "fleet"
        assert q.period_days == 3


def test_plate_ru_priority_over_name() -> None:
    q = parse("Нарушения Иванова А123ВС77 за неделю")
    assert q.kind == "driver"
    assert q.plate == "А123ВС77"
    assert q.period_days == 7


def test_plate_kk() -> None:
    q = parse("отчёт 123ABC02 за месяц")
    assert q.kind == "driver"
    assert q.plate == "123ABC02"
    assert q.period_days == 30


def test_fleet_by_drivers() -> None:
    q = parse("отчёт по парку по водителям")
    assert q.kind == "fleet"
    assert q.view == "drivers"


def test_period_clamp() -> None:
    q = parse("отчёт за 99999 дней")
    assert 1 <= q.period_days <= 365


def test_groq_failure_falls_back(monkeypatch) -> None:
    # Сбой Groq-ветки (ключ задан, но сеть/JSON/валидация падают) → молча в regex.
    import api.services.nlu_service as nlu

    def _boom(text: str):
        raise ConnectionError("network down")

    monkeypatch.setattr(nlu, "_parse_groq", _boom)
    q = nlu.parse("Нарушения Иванова за 3 дня")
    assert isinstance(q, ReportQuery)
    assert q.kind == "driver"
    assert q.driver_name is not None and "Иванов" in q.driver_name
