"""Unit-тесты цепочек усталости (b20).

Тестируем чистую функцию `_build_chains` — без БД, детерминировано.
"""

from __future__ import annotations

import pytest

from api.services.fatigue_service import _build_chains


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _row(plate: str, code: str, ts: str) -> dict:
    return {"vehicle_plate": plate, "alarm_code": code, "ts": ts}


# ---------------------------------------------------------------------------
# Тесты
# ---------------------------------------------------------------------------

def test_three_events_with_drowsy_is_critical():
    """yawning → drowsy → harsh_braking в 90 мин → 1 цепочка, severity=critical."""
    rows = [
        _row("А001", "DMS_YAWNING",    "2024-01-01 08:00:00.000000"),
        _row("А001", "DMS_DROWSY",     "2024-01-01 08:30:00.000000"),
        _row("А001", "HARSH_BRAKING",  "2024-01-01 09:00:00.000000"),
    ]
    result = _build_chains(rows)
    assert len(result) == 1
    chain = result[0]
    assert chain.plate == "А001"
    assert len(chain.events) == 3
    assert chain.severity == "critical"
    assert chain.trip_id is None


def test_single_event_no_chain():
    """Одиночный аларм → нет цепочки."""
    rows = [
        _row("А002", "DMS_YAWNING", "2024-01-01 08:00:00.000000"),
    ]
    result = _build_chains(rows)
    assert result == []


def test_events_outside_window_no_chain():
    """yawning + harsh_braking с разрывом 3 ч → нет цепочки (вне окна 90 мин)."""
    rows = [
        _row("А003", "DMS_YAWNING",   "2024-01-01 08:00:00.000000"),
        _row("А003", "HARSH_BRAKING", "2024-01-01 11:00:00.000000"),
    ]
    result = _build_chains(rows)
    assert result == []


def test_plate_filter_two_plates():
    """Два ТС; фильтрация по plate возвращает цепочки только для него."""
    rows = [
        # ТС А004 — цепочка
        _row("А004", "DMS_YAWNING",   "2024-01-01 08:00:00.000000"),
        _row("А004", "DMS_DROWSY",    "2024-01-01 08:45:00.000000"),
        # ТС А005 — тоже цепочка
        _row("А005", "HARSH_BRAKING", "2024-01-01 09:00:00.000000"),
        _row("А005", "HARSH_ACCEL",   "2024-01-01 09:30:00.000000"),
    ]
    # Фильтруем на уровне сервиса (эмулируем: передаём только нужные строки)
    rows_a004 = [r for r in rows if r["vehicle_plate"] == "А004"]
    result = _build_chains(rows_a004)
    assert len(result) == 1
    assert result[0].plate == "А004"


def test_severity_monotonically_increasing():
    """Severity растёт с длиной цепочки и с наличием DMS_DROWSY."""
    def chain_severity(codes: list[str]) -> str:
        ts_base = "2024-01-01 08:{:02d}:00.000000"
        rows = [_row("X", code, ts_base.format(i * 10)) for i, code in enumerate(codes)]
        result = _build_chains(rows)
        assert len(result) == 1, f"Ожидали 1 цепочку, получили {len(result)}"
        return result[0].severity

    # 2 события, нет DMS_DROWSY → medium
    assert chain_severity(["DMS_YAWNING", "HARSH_BRAKING"]) == "medium"

    # 2 события, есть DMS_DROWSY → high
    assert chain_severity(["DMS_YAWNING", "DMS_DROWSY"]) == "high"

    # 3 события, нет DMS_DROWSY → high
    assert chain_severity(["DMS_YAWNING", "HARSH_BRAKING", "HARSH_ACCEL"]) == "high"

    # 4 события → critical
    assert chain_severity(["DMS_YAWNING", "HARSH_BRAKING", "HARSH_ACCEL", "HARSH_CORNERING"]) == "critical"

    # 3 события + DMS_DROWSY → critical
    assert chain_severity(["DMS_YAWNING", "DMS_DROWSY", "HARSH_BRAKING"]) == "critical"


def test_empty_input_returns_empty_list():
    """Пустой вход → пустой список."""
    assert _build_chains([]) == []


def test_window_boundary_exact():
    """События ровно на границе 90 мин включаются в цепочку."""
    rows = [
        _row("А006", "DMS_YAWNING",  "2024-01-01 08:00:00.000000"),
        _row("А006", "DMS_DROWSY",   "2024-01-01 09:30:00.000000"),  # ровно 90 мин
    ]
    result = _build_chains(rows)
    assert len(result) == 1
    assert result[0].severity == "high"


def test_window_boundary_exceeded():
    """91 минута — за окном, цепочки нет."""
    rows = [
        _row("А007", "DMS_YAWNING",  "2024-01-01 08:00:00.000000"),
        _row("А007", "DMS_DROWSY",   "2024-01-01 09:31:00.000000"),  # 91 мин
    ]
    result = _build_chains(rows)
    assert result == []


def test_chain_window_and_trip_id_none():
    """window_min и trip_id проверяем явно."""
    rows = [
        _row("А008", "DMS_YAWNING",  "2024-01-01 08:00:00.000000"),
        _row("А008", "HARSH_ACCEL",  "2024-01-01 08:20:00.000000"),
    ]
    result = _build_chains(rows, window_min=90)
    assert len(result) == 1
    assert result[0].window_min == 90
    assert result[0].trip_id is None
