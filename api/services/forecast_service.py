"""Сервис прогноза риска по ТС (b18, §8.3/§8.4, идея #12).

`GET /api/reports/forecast/{plate}` → `RiskForecast`: тренд-прогноз нарушений на 7
дней вперёд, флаг аномалии и предписывающие рекомендации.

Архитектура двухветочная (§8.0):
  * **ML-ветка** — `ARIMA` (statsmodels) для тренда + `IsolationForest` (sklearn)
    для аномалии. Включается только при достаточном временном ряде (`_MIN_ARIMA_DAYS`
    / `_MIN_ANOMALY_DAYS`). На реальных 54 алярмах (2 дня) — **мёртвая**.
  * **Детерминированный фолбэк** — наивный базлайн (скользящее среднее дневных
    счётчиков) + статический доверительный коридор; `anomaly=False`,
    `anomaly_reason="недостаточно истории"`. Без падения при пустой истории.

Детерминизм (Check b18): опорная дата — максимум `ts` из данных (не `datetime.now()`),
фиксированный `random_state`, тяжёлые ML-импорты ленивые и обёрнуты в try/except
(их отсутствие/сбой → фолбэк, не 500). Один вход → один выход.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import duckdb
from pydantic import BaseModel

from api.core import enrichment
from api.repositories import rows_to_dicts, vehicles_repo

# --- Категории alarm_code для фич/рекомендаций (совпадают с enrichment-таблицей). ---
_HARSH_CODES = {"HARSH_BRAKING", "HARSH_ACCEL", "HARSH_CORNERING"}
_FATIGUE_CODES = {"DMS_DROWSY", "DMS_YAWNING"}
_OVERSPEED_CODES = {"OVERSPEED"}

# Пороги включения ML-веток (на реальных данных не достигаются → фолбэк, §8.0).
_MIN_ARIMA_DAYS = 8       # ARIMA имеет смысл только на ряде ≥ 8 точек.
_MIN_ANOMALY_DAYS = 8     # IsolationForest — на ≥ 8 дневных наблюдениях.
_HORIZON = 7              # Горизонт прогноза — ровно 7 дней (Check: trend длиной 7).
_RANDOM_STATE = 42        # Фиксированный seed (детерминизм IsolationForest).

# Названия фич для anomaly_reason (порядок = столбцы матрицы фич).
_FEATURES = ("daily_count", "max_speed", "night_share", "harsh_share")
_FEATURE_LABEL_RU = {
    "daily_count": "число событий за день",
    "max_speed": "максимальная скорость",
    "night_share": "доля ночных событий",
    "harsh_share": "доля резких манёвров",
}


# ---------------------------------------------------------------------------
# Схемы ответа (§8.4). Держим в сервисе — b18 владеет только своими файлами
# (не правим общий api/domain/entities.py, иначе гонка с b19/b20 в одном worktree).
# ---------------------------------------------------------------------------


class RiskForecastPoint(BaseModel):
    """Точка прогнозного тренда: дата + предсказание с доверительным коридором."""

    date: str               # YYYY-MM-DD
    predicted_events: float
    ci_low: float
    ci_high: float


class RiskForecast(BaseModel):
    """Прогноз риска по ТС (§8.4)."""

    plate: str
    trend: list[RiskForecastPoint]
    anomaly: bool
    anomaly_reason: str | None = None
    recommendations: list[str]
    narrative: str | None = None    # b22 (Волна 4.2).


# ---------------------------------------------------------------------------
# Дневной ряд из БД (детерминированно).
# ---------------------------------------------------------------------------


class _DayStat:
    """Агрегаты одного дня: счётчик, скорости, доли ночь/резкость."""

    __slots__ = ("count", "max_speed", "night", "harsh")

    def __init__(self) -> None:
        self.count = 0
        self.max_speed = 0.0
        self.night = 0
        self.harsh = 0

    @property
    def night_share(self) -> float:
        return self.night / self.count if self.count else 0.0

    @property
    def harsh_share(self) -> float:
        return self.harsh / self.count if self.count else 0.0


def _alarm_rows(db: duckdb.DuckDBPyConnection, plate: str) -> list[dict[str, Any]]:
    """Сырые алярмы ТС (alarm_code, ts, speed_kmh) в детерминированном порядке."""
    return rows_to_dicts(
        db.execute(
            'SELECT "alarm_code", "ts", "speed_kmh" FROM "v_incidents" '
            'WHERE "vehicle_plate" = ? ORDER BY "ts", "alarm_code"',
            [plate],
        )
    )


def _parse_day(ts: str) -> date | None:
    """ISO-ts → локальная дата события (без конвертации TZ, для группировки по дню)."""
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        return None


def _aggregate_days(rows: list[dict[str, Any]]) -> dict[date, _DayStat]:
    """Чистая агрегация: список алярмов → {день: _DayStat}. Без БД (юнит-тестируемо)."""
    days: dict[date, _DayStat] = {}
    for row in rows:
        day = _parse_day(row.get("ts", ""))
        if day is None:
            continue
        stat = days.setdefault(day, _DayStat())
        stat.count += 1
        stat.max_speed = max(stat.max_speed, float(row.get("speed_kmh") or 0.0))
        if enrichment.is_night(str(row["ts"])):
            stat.night += 1
        if str(row.get("alarm_code")) in _HARSH_CODES:
            stat.harsh += 1
    return days


def _dense_series(
    days: dict[date, _DayStat], anchor: date
) -> tuple[list[date], list[_DayStat]]:
    """Плотный ряд [min_day .. anchor] с нулевым заполнением пропусков."""
    if not days:
        return [], []
    start = min(days)
    span = (anchor - start).days
    out_days: list[date] = []
    out_stats: list[_DayStat] = []
    for i in range(span + 1):
        d = start + timedelta(days=i)
        out_days.append(d)
        out_stats.append(days.get(d, _DayStat()))
    return out_days, out_stats


# ---------------------------------------------------------------------------
# Тренд: ARIMA (ML) либо наивный базлайн (фолбэк).
# ---------------------------------------------------------------------------


def _trend_baseline(counts: list[int], anchor: date) -> list[RiskForecastPoint]:
    """Наивный детерминированный прогноз: скользящее среднее + статический коридор.

    `predicted` = среднее последних ≤7 дней (0 при пустой истории). Коридор —
    `± max(1, σ)`, нижняя граница клампится в 0 (Check: ci_low ≤ predicted ≤ ci_high).
    """
    if counts:
        window = counts[-7:]
        predicted = sum(window) / len(window)
        mean = sum(counts) / len(counts)
        var = sum((c - mean) ** 2 for c in counts) / len(counts)
        band = max(1.0, var ** 0.5)
    else:
        predicted = 0.0
        band = 0.0
    ci_low = max(0.0, predicted - band)
    ci_high = predicted + band
    return [
        RiskForecastPoint(
            date=(anchor + timedelta(days=i)).isoformat(),
            predicted_events=round(predicted, 2),
            ci_low=round(ci_low, 2),
            ci_high=round(ci_high, 2),
        )
        for i in range(1, _HORIZON + 1)
    ]


def _trend_arima(counts: list[int], anchor: date) -> list[RiskForecastPoint] | None:
    """ARIMA-прогноз на 7 дней. None при недостатке точек / сбое импорта (→ фолбэк)."""
    if len(counts) < _MIN_ARIMA_DAYS:
        return None
    try:
        from statsmodels.tsa.arima.model import ARIMA  # ленивый тяжёлый импорт

        model = ARIMA(counts, order=(1, 1, 1))
        fit = model.fit()
        forecast = fit.get_forecast(steps=_HORIZON)
        mean = forecast.predicted_mean
        ci = forecast.conf_int(alpha=0.05)
    except Exception:
        return None

    points: list[RiskForecastPoint] = []
    for i in range(_HORIZON):
        pred = max(0.0, float(mean[i]))
        low = max(0.0, float(ci[i][0]))
        high = float(ci[i][1])
        # Инвариант ci_low ≤ predicted ≤ ci_high (страховка от численных краёв).
        low = min(low, pred)
        high = max(high, pred)
        points.append(
            RiskForecastPoint(
                date=(anchor + timedelta(days=i + 1)).isoformat(),
                predicted_events=round(pred, 2),
                ci_low=round(low, 2),
                ci_high=round(high, 2),
            )
        )
    return points


# ---------------------------------------------------------------------------
# Аномалия: IsolationForest (ML) либо «недостаточно истории» (фолбэк).
# ---------------------------------------------------------------------------


def _detect_anomaly(stats: list[_DayStat]) -> tuple[bool, str | None]:
    """IsolationForest по фичам дней. Возвращает (anomaly, причина/фича).

    Недостаток данных / сбой импорта → (False, "недостаточно истории") (§8.0).
    """
    if len(stats) < _MIN_ANOMALY_DAYS:
        return False, "недостаточно истории"
    matrix = [
        [float(s.count), s.max_speed, s.night_share, s.harsh_share] for s in stats
    ]
    try:
        from sklearn.ensemble import IsolationForest  # ленивый тяжёлый импорт

        clf = IsolationForest(random_state=_RANDOM_STATE, n_estimators=100)
        labels = clf.fit_predict(matrix)
    except Exception:
        return False, "недостаточно истории"

    anomalous_idx = [i for i, lab in enumerate(labels) if lab == -1]
    if not anomalous_idx:
        return False, None

    # Какая фича сильнее всего «выбила» аномальные дни — по максимальному |z-score|.
    cols = list(zip(*matrix))
    reason_feature = _FEATURES[0]
    best_z = -1.0
    for col_idx, col in enumerate(cols):
        mean = sum(col) / len(col)
        var = sum((v - mean) ** 2 for v in col) / len(col)
        std = var ** 0.5
        if std == 0:
            continue
        for i in anomalous_idx:
            z = abs(col[i] - mean) / std
            if z > best_z:
                best_z = z
                reason_feature = _FEATURES[col_idx]
    return True, f"аномалия по фиче «{_FEATURE_LABEL_RU[reason_feature]}»"


# ---------------------------------------------------------------------------
# Рекомендации — детерминированные предписывающие правила.
# ---------------------------------------------------------------------------


def _recommendations(rows: list[dict[str, Any]]) -> list[str]:
    """Предписывающие правила из агрегатов алярмов ТС (детерминированно, упорядоченно)."""
    total = len(rows)
    if total == 0:
        return []

    night = sum(1 for r in rows if enrichment.is_night(str(r["ts"])))
    harsh = sum(1 for r in rows if str(r.get("alarm_code")) in _HARSH_CODES)
    fatigue = sum(1 for r in rows if str(r.get("alarm_code")) in _FATIGUE_CODES)
    overspeed = sum(1 for r in rows if str(r.get("alarm_code")) in _OVERSPEED_CODES)

    recs: list[str] = []
    if night / total >= 0.5:
        recs.append(
            "Большинство событий приходится на ночь — коучинг по ночной бдительности "
            "и контроль режима труда и отдыха."
        )
    if fatigue >= 2:
        recs.append(
            "Повторяющиеся признаки усталости (засыпание/зевота) — пересмотреть "
            "график смен и обязательные перерывы."
        )
    if harsh >= 2:
        recs.append(
            "Частые резкие торможения/манёвры — тренинг по соблюдению дистанции "
            "и плавному вождению."
        )
    if overspeed >= 1:
        recs.append(
            "Зафиксированы превышения скорости — напоминание о скоростном режиме "
            "и точечный контроль маршрутов."
        )
    if not recs:
        recs.append(
            "Выраженных факторов риска не выявлено — продолжать стандартный мониторинг."
        )
    return recs


# ---------------------------------------------------------------------------
# Валидность ТС и публичный API сервиса.
# ---------------------------------------------------------------------------


def plate_exists(db: duckdb.DuckDBPyConnection, plate: str) -> bool:
    """ТС известен, если есть в справочнике ТС ИЛИ имеет хотя бы один алярм."""
    if vehicles_repo.get_vehicle(db, plate) is not None:
        return True
    row = db.execute(
        'SELECT 1 FROM "v_incidents" WHERE "vehicle_plate" = ? LIMIT 1', [plate]
    ).fetchone()
    return row is not None


def _anchor_date(db: duckdb.DuckDBPyConnection, days: dict[date, _DayStat]) -> date:
    """Опорная дата прогноза = максимум из данных ТС; иначе — глобальный максимум ts."""
    if days:
        return max(days)
    row = db.execute('SELECT MAX("ts") FROM "v_incidents"').fetchone()
    global_day = _parse_day(str(row[0])) if row and row[0] is not None else None
    return global_day or date(2026, 1, 1)


def forecast(db: duckdb.DuckDBPyConnection, plate: str) -> RiskForecast:
    """Строит `RiskForecast` для ТС (§8.4). Предполагает, что `plate` валиден (404 — в роутере).

    Пустая история → валидный нулевой прогноз без исключения (Check b18).
    """
    rows = _alarm_rows(db, plate)
    days = _aggregate_days(rows)
    anchor = _anchor_date(db, days)

    ordered_days, ordered_stats = _dense_series(days, anchor)
    counts = [s.count for s in ordered_stats]

    trend = _trend_arima(counts, anchor) or _trend_baseline(counts, anchor)
    anomaly, reason = _detect_anomaly(ordered_stats)

    return RiskForecast(
        plate=plate,
        trend=trend,
        anomaly=anomaly,
        anomaly_reason=reason,
        recommendations=_recommendations(rows),
    )
