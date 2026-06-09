"""Unit-тесты цепочек усталости (b20) — §8.3/§8.4.

Тестируем чистую функцию `_build_chains` — без БД, без сети, без datetime.now().
"""

from __future__ import annotations

from datetime import datetime, timedelta

from api.services.fatigue_service import _build_chains


_BASE_TS = datetime(2024, 1, 1, 8, 0, 0)


def _ts(minutes: int) -> str:
    return (_BASE_TS + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S.%f")


def _row(plate: str, code: str, ts: str) -> dict:
    return {"vehicle_plate": plate, "alarm_code": code, "ts": ts}


# ---------------------------------------------------------------------------
# Базовый сценарий: yawning→drowsy→harsh в окне
# ---------------------------------------------------------------------------

def test_three_events_in_window_forms_one_chain():
    """yawning → drowsy → harsh_braking в окне 90 мин → 1 цепочка с 3 events."""
    rows = [
        _row("А001", "DMS_YAWNING",   "2024-01-01 08:00:00.000000"),
        _row("А001", "DMS_DROWSY",    "2024-01-01 08:30:00.000000"),
        _row("А001", "HARSH_BRAKING", "2024-01-01 09:00:00.000000"),
    ]
    result = _build_chains(rows)
    assert len(result) == 1
    chain = result[0]
    assert chain.plate == "А001"
    assert len(chain.events) == 3
    assert [e.code for e in chain.events] == ["DMS_YAWNING", "DMS_DROWSY", "HARSH_BRAKING"]


def test_chain_events_have_ts():
    """Каждое событие цепочки содержит поле ts."""
    rows = [
        _row("Р001", "DMS_YAWNING",  "2024-01-01 08:00:00.000000"),
        _row("Р001", "DMS_DROWSY",   "2024-01-01 08:20:00.000000"),
    ]
    result = _build_chains(rows)
    assert len(result) == 1
    for e in result[0].events:
        assert e.ts != ""


# ---------------------------------------------------------------------------
# Вне окна / одиночные — не цепочка
# ---------------------------------------------------------------------------

def test_single_event_no_chain():
    """Одиночный аларм → нет цепочки."""
    result = _build_chains([_row("А002", "DMS_YAWNING", "2024-01-01 08:00:00.000000")])
    assert result == []


def test_two_events_outside_window_no_chain():
    """yawning + harsh_braking с разрывом 91 мин → нет цепочки."""
    rows = [
        _row("А003", "DMS_YAWNING",   "2024-01-01 08:00:00.000000"),
        _row("А003", "HARSH_BRAKING", "2024-01-01 09:31:00.000000"),  # 91 мин
    ]
    assert _build_chains(rows) == []


def test_window_boundary_exact_90_min_included():
    """Ровно 90 минут разрыва — граница включена → цепочка существует."""
    rows = [
        _row("А006", "DMS_YAWNING", "2024-01-01 08:00:00.000000"),
        _row("А006", "DMS_DROWSY",  "2024-01-01 09:30:00.000000"),  # ровно 90 мин
    ]
    result = _build_chains(rows)
    assert len(result) == 1


def test_window_boundary_91_min_excluded():
    """91 минута — за границей окна, цепочки нет."""
    rows = [
        _row("А007", "DMS_YAWNING", "2024-01-01 08:00:00.000000"),
        _row("А007", "DMS_DROWSY",  "2024-01-01 09:31:00.000000"),  # 91 мин
    ]
    assert _build_chains(rows) == []


# ---------------------------------------------------------------------------
# Severity монотонно растёт с длиной / наличием DMS_DROWSY
# ---------------------------------------------------------------------------

def test_severity_two_events_no_drowsy_is_medium():
    rows = [_row("X", "DMS_YAWNING", _ts(0)), _row("X", "HARSH_BRAKING", _ts(10))]
    result = _build_chains(rows)
    assert result[0].severity == "medium"


def test_severity_two_events_with_drowsy_is_high():
    rows = [_row("X", "DMS_YAWNING", _ts(0)), _row("X", "DMS_DROWSY", _ts(10))]
    result = _build_chains(rows)
    assert result[0].severity == "high"


def test_severity_three_events_no_drowsy_is_high():
    rows = [
        _row("X", "DMS_YAWNING",   _ts(0)),
        _row("X", "HARSH_BRAKING", _ts(10)),
        _row("X", "HARSH_ACCEL",   _ts(20)),
    ]
    result = _build_chains(rows)
    assert result[0].severity == "high"


def test_severity_three_events_with_drowsy_is_critical():
    rows = [
        _row("X", "DMS_YAWNING",   _ts(0)),
        _row("X", "DMS_DROWSY",    _ts(10)),
        _row("X", "HARSH_BRAKING", _ts(20)),
    ]
    result = _build_chains(rows)
    assert result[0].severity == "critical"


def test_severity_four_events_is_critical():
    rows = [
        _row("X", "DMS_YAWNING",    _ts(0)),
        _row("X", "HARSH_BRAKING",  _ts(10)),
        _row("X", "HARSH_ACCEL",    _ts(20)),
        _row("X", "HARSH_CORNERING", _ts(30)),
    ]
    result = _build_chains(rows)
    assert result[0].severity == "critical"


def test_severity_monotone_2_no_drowsy_lt_3_no_drowsy():
    """medium < high: 2-без-drowsy строго слабее 3-без-drowsy."""
    ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    rows_2 = [_row("X", "DMS_YAWNING", _ts(0)), _row("X", "HARSH_BRAKING", _ts(10))]
    rows_3 = [_row("X", "DMS_YAWNING", _ts(0)), _row("X", "HARSH_BRAKING", _ts(10)), _row("X", "HARSH_ACCEL", _ts(20))]

    sev_2 = _build_chains(rows_2)[0].severity
    sev_3 = _build_chains(rows_3)[0].severity
    assert ORDER[sev_2] < ORDER[sev_3]


# ---------------------------------------------------------------------------
# ?plate= фильтрация
# ---------------------------------------------------------------------------

def test_plate_filter_returns_only_matching_plate():
    """Строки только одного ТС → цепочка только для него."""
    rows = [
        _row("А004", "DMS_YAWNING",  "2024-01-01 08:00:00.000000"),
        _row("А004", "DMS_DROWSY",   "2024-01-01 08:45:00.000000"),
        _row("А005", "HARSH_BRAKING","2024-01-01 09:00:00.000000"),
        _row("А005", "HARSH_ACCEL",  "2024-01-01 09:30:00.000000"),
    ]
    rows_a004 = [r for r in rows if r["vehicle_plate"] == "А004"]
    result = _build_chains(rows_a004)
    assert len(result) == 1
    assert result[0].plate == "А004"


def test_no_chains_returns_empty_list():
    """Нет цепочек → []."""
    rows = [
        _row("А009", "DMS_YAWNING",   "2024-01-01 08:00:00.000000"),
        _row("А009", "HARSH_BRAKING", "2024-01-01 11:00:00.000000"),  # вне окна
    ]
    assert _build_chains(rows) == []


def test_empty_input_returns_empty_list():
    """Пустой вход → []."""
    assert _build_chains([]) == []


# ---------------------------------------------------------------------------
# Детерминизм между прогонами
# ---------------------------------------------------------------------------

def test_determinism_same_result_twice():
    """Два вызова с одинаковыми данными дают идентичный результат."""
    rows = [
        _row("Д001", "DMS_YAWNING",   "2024-01-01 08:00:00.000000"),
        _row("Д001", "DMS_DROWSY",    "2024-01-01 08:30:00.000000"),
        _row("Д001", "HARSH_BRAKING", "2024-01-01 09:00:00.000000"),
    ]
    r1 = _build_chains(rows)
    r2 = _build_chains(rows)
    assert [c.model_dump() for c in r1] == [c.model_dump() for c in r2]


# ---------------------------------------------------------------------------
# window_min и trip_id
# ---------------------------------------------------------------------------

def test_chain_carries_window_min():
    """Цепочка содержит корректное window_min."""
    rows = [
        _row("А008", "DMS_YAWNING", "2024-01-01 08:00:00.000000"),
        _row("А008", "HARSH_ACCEL", "2024-01-01 08:20:00.000000"),
    ]
    result = _build_chains(rows, window_min=90)
    assert result[0].window_min == 90


def test_chain_trip_id_is_none():
    """trip_id = None (b20 не привязывается к рейсу)."""
    rows = [
        _row("А008", "DMS_YAWNING", "2024-01-01 08:00:00.000000"),
        _row("А008", "HARSH_ACCEL", "2024-01-01 08:20:00.000000"),
    ]
    result = _build_chains(rows)
    assert result[0].trip_id is None


# ---------------------------------------------------------------------------
# Два кластера → 2 цепочки
# ---------------------------------------------------------------------------

def test_two_clusters_produce_two_chains():
    """Два кластера событий с 4-часовым разрывом → 2 цепочки."""
    rows = [
        _row("P1", "DMS_YAWNING",   "2024-01-01 08:00:00.000000"),
        _row("P1", "HARSH_BRAKING", "2024-01-01 08:30:00.000000"),
        _row("P1", "DMS_DROWSY",    "2024-01-01 12:00:00.000000"),
        _row("P1", "HARSH_ACCEL",   "2024-01-01 12:20:00.000000"),
    ]
    result = _build_chains(rows)
    assert len(result) == 2
    severities = {c.severity for c in result}
    assert "medium" in severities
    assert "high" in severities
