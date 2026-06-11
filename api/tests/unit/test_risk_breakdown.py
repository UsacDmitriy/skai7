"""Unit-покрытие explainability — декомпозиция `risk_score` (b27) — §8.8, идея #19.

`risk_breakdown_service.breakdown` раскладывает итоговый `risk_score` (§2) на
абсолютные вклады слагаемых `{severity_w, speed_ratio, night, freq_w, weather_bonus}`
в очках 0..100. Главный инвариант (Check tu-riskbreakdown):

    Σ вкладов (с тем же round/clamp) == risk_score того же инцидента.

Тестируем без сети и без сборки БД: `incidents_service.get_detail` подменяется
детерминированным `IncidentDetail`-подобным объектом — изолируем именно логику
декомпозиции от тяжёлого enrichment-стека (его покрывает test_enrichment).
Веса/коэффициенты берутся из `api.core.enrichment` (общий источник; дрейф ловит этот тест).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from api.core import enrichment
from api.services import incidents_service, risk_breakdown_service as rbs

# (severity, speed_kmh, speed_limit_kmh, is_night, events_last_7d) — разнородные кейсы:
# low/medium/high/critical, день/ночь, превышение с клампом 1.5, частота с клампом 1,
# нулевой лимит (guard div/0), нулевой риск.
_CASES = [
    ("low", 0.0, 60, False, 0),       # минимальный риск
    ("medium", 50.0, 60, False, 2),   # умеренный, день
    ("high", 90.0, 60, True, 5),      # ночь + превышение
    ("critical", 200.0, 60, True, 20),  # всё в потолок (клампы)
    ("high", 30.0, 0, False, 3),      # speed_limit=0 → speed_ratio guard
    ("unknown", 40.0, 60, False, 1),  # неизвестная severity → low-вес
]


def _patch_detail(monkeypatch, case) -> None:
    """Подменить get_detail детерминированным объектом по входному кейсу."""
    severity, speed_kmh, speed_limit_kmh, is_night, events_last_7d = case
    detail = SimpleNamespace(
        severity=severity,
        speed_kmh=speed_kmh,
        speed_limit_kmh=speed_limit_kmh,
        is_night=is_night,
        events_last_7d=events_last_7d,
    )
    monkeypatch.setattr(
        incidents_service, "get_detail", lambda db, incident_id: detail
    )


@pytest.mark.parametrize("case", _CASES)
def test_breakdown_mirrors_risk_score(monkeypatch, case) -> None:
    """Итог декомпозиции == `risk_score` (§2) тех же входов — точное зеркало."""
    _patch_detail(monkeypatch, case)

    bd = rbs.breakdown(db=None, incident_id="INC1")

    expected = enrichment.risk_score(*case)
    assert bd is not None
    assert bd.total_risk_score == expected


@pytest.mark.parametrize("case", _CASES)
def test_breakdown_sum_invariant(monkeypatch, case) -> None:
    """Сумма вкладов (с тем же round/clamp) == итог (Check: «сумма == risk_score»)."""
    _patch_detail(monkeypatch, case)

    bd = rbs.breakdown(db=None, incident_id="INC1")

    raw = (
        bd.severity_w + bd.speed_ratio + bd.night + bd.freq_w + bd.weather_bonus
    )
    assert bd.total_risk_score == max(0, min(100, round(raw)))


@pytest.mark.parametrize("case", _CASES)
def test_breakdown_contributions_non_negative(monkeypatch, case) -> None:
    """Каждый вклад ≥ 0 (схема §8.8: все слагаемые неотрицательны)."""
    _patch_detail(monkeypatch, case)

    bd = rbs.breakdown(db=None, incident_id="INC1")

    for value in (
        bd.severity_w,
        bd.speed_ratio,
        bd.night,
        bd.freq_w,
        bd.weather_bonus,
    ):
        assert value >= 0.0


@pytest.mark.parametrize("case", _CASES)
def test_breakdown_weather_bonus_zero_without_cache(monkeypatch, case) -> None:
    """`weather_bonus = 0` без кэша погоды (обратная совместимость карточки)."""
    _patch_detail(monkeypatch, case)

    bd = rbs.breakdown(db=None, incident_id="INC1")

    assert bd.weather_bonus == 0.0


def test_breakdown_total_in_score_range(monkeypatch) -> None:
    """`total_risk_score ∈ [0,100]` даже на экстремальных входах (clamp)."""
    _patch_detail(monkeypatch, ("critical", 999.0, 60, True, 999))

    bd = rbs.breakdown(db=None, incident_id="INC1")

    assert 0 <= bd.total_risk_score <= 100


def test_breakdown_deterministic(monkeypatch) -> None:
    """Один вход → один выход: повтор декомпозиции идентичен."""
    _patch_detail(monkeypatch, ("high", 90.0, 60, True, 5))

    first = rbs.breakdown(db=None, incident_id="INC1")
    second = rbs.breakdown(db=None, incident_id="INC1")

    assert first == second


def test_breakdown_unknown_incident_returns_none(monkeypatch) -> None:
    """Неизвестный `id` → None (404 поднимает роутер в t2)."""
    monkeypatch.setattr(
        incidents_service, "get_detail", lambda db, incident_id: None
    )

    assert rbs.breakdown(db=None, incident_id="NOPE") is None


def test_breakdown_id_echoed(monkeypatch) -> None:
    """В ответе возвращается запрошенный `id` (для привязки к карточке)."""
    _patch_detail(monkeypatch, ("medium", 50.0, 60, False, 2))

    bd = rbs.breakdown(db=None, incident_id="INC-42")

    assert bd.id == "INC-42"
