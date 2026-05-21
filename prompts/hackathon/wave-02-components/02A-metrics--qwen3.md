# 02A metrics — метрики дашборда и таблица рисков

**Model**: qwen/qwen3-coder:free

## Task

Создать/обновить `app/metrics.py` — функции KPI-метрик дашборда и построения top-20 таблицы рисков.

## Requirements

1. `build_dashboard_metrics(datasets)` — рассчитывает 4 KPI-метрики:
   - Количество CSV-файлов
   - Общее число строк
   - Количество событий-кандидатов (по `risk_score >= RISK_THRESHOLD`, Speed/Type или `severity` в `high`/`critical`)
   - Статус MVP
2. `build_risk_table(datasets)` — строит top-20 таблицу рисков, отсортированную по убыванию `risk_score`, либо берёт первые 20 строк по `severity`. Возвращает `pd.DataFrame`.
3. Возвращаемый список метрик совместим с `st.metric()` — словари с ключами `label` и `value`.

## Rules

- Сохранить в `app/metrics.py`
- Импортировать `RISK_THRESHOLD` из `app.constants`
- Docstrings на русском
- Type hints с `from __future__ import annotations`
- Проверка: `python -c "from app.metrics import build_dashboard_metrics, build_risk_table"` должна проходить
- Аргумент `datasets: dict[str, pd.DataFrame]` — словарь имя_датасета → DataFrame

## Risk derivation logic

Приоритет поиска колонок:
1. `risk_score` — использовать напрямую (sample_data/events.csv)
2. `Speed` — производный risk: >= 90 → 90, >= 70 → 70, >= 50 → 50, иначе → 30
3. `Type` — маппинг: Drowsiness → 90, DriverSubstitution → 90, SeatBelt → 80, Overspeeding → 80, ForwardCollision → 80, HarshBraking → 70, HarshAcceleration → 70, PhoneUsage → 70, LaneDeparture → 70, HarshCornering → 60, Smoking → 60, остальные → 50
4. `severity` — строковый fallback, high/critical

## Context

Файл `app/constants.py` содержит:
```python
RISK_THRESHOLD: int = 70
```

Структура датасетов предполагает наличие одной из колонок:
- `risk_score` (числовая) — приоритетный критерий
- `Speed` (числовая) — колонка из selected_video_alarms.csv
- `Type` (строковая) — тип аларма из selected_video_alarms.csv
- `severity` (строковая) — fallback-критерий, значения `high`/`critical`/`medium`/`low`

Дополнительные колонки (опциональные): `id`, `vehicle_id`, `driver_id`, `event_type`, `reason`, `AlarmId`, `dataset_vehicle_code`.

## Code

```python
from __future__ import annotations

import pandas as pd

from app.constants import RISK_THRESHOLD

_TYPE_RISK_MAP: dict[str, int] = {
    "Drowsiness": 90,
    "DriverSubstitution": 90,
    "SeatBelt": 80,
    "Overspeeding": 80,
    "ForwardCollision": 80,
    "HarshBraking": 70,
    "HarshAcceleration": 70,
    "PhoneUsage": 70,
    "LaneDeparture": 70,
    "HarshCornering": 60,
    "Smoking": 60,
}


def _derive_risk_series(df: pd.DataFrame) -> pd.Series:
    """Вычислить производный risk_score из колонок Speed или Type."""
    if "Speed" in df.columns:
        return df["Speed"].apply(
            lambda s: 90 if s >= 90 else (70 if s >= 70 else (50 if s >= 50 else 30))
        )
    if "Type" in df.columns:
        return df["Type"].map(_TYPE_RISK_MAP).fillna(50).astype(int)
    return pd.Series(dtype=int)


def build_dashboard_metrics(datasets: dict[str, pd.DataFrame]) -> list[dict[str, str]]:
    """Рассчитывает 4 KPI-метрики для дашборда.

    Возвращает список словарей с ключами 'label' и 'value',
    совместимый с st.metric().
    """
    total_rows = sum(len(df) for df in datasets.values())
    total_files = len(datasets)

    candidate_events = 0
    for df in datasets.values():
        if "risk_score" in df.columns:
            candidate_events += int((df["risk_score"] >= RISK_THRESHOLD).sum())
        elif "Speed" in df.columns or "Type" in df.columns:
            risk = _derive_risk_series(df)
            candidate_events += int((risk >= RISK_THRESHOLD).sum())
        elif "severity" in df.columns:
            candidate_events += int(
                df["severity"].astype(str).str.lower().isin(["high", "critical"]).sum()
            )

    return [
        {"label": "CSV файлов", "value": str(total_files)},
        {"label": "Строк загружено", "value": f"{total_rows:,}".replace(",", " ")},
        {"label": "Событий-кандидатов", "value": str(candidate_events)},
        {"label": "Статус MVP", "value": "Demo"},
    ]


def build_risk_table(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Строит top-20 таблицу рисков, отсортированную по убыванию risk_score.

    Ищет первый датасет с колонкой 'risk_score', Speed/Type или 'severity'.
    Для Speed/Type вычисляет производный risk_score.
    Возвращает до 20 строк с ключевыми колонками: id, vehicle_id,
    event_type, risk_score/severity и reason.
    """
    for name, df in datasets.items():
        if "risk_score" in df.columns:
            cols = [col for col in ["id", "vehicle_id", "driver_id", "event_type", "risk_score", "reason"] if col in df.columns]
            result = df.sort_values("risk_score", ascending=False).head(20)
            return result[cols] if cols else result.head(20)

        if "Speed" in df.columns or "Type" in df.columns:
            work = df.copy()
            work["_derived_risk"] = _derive_risk_series(work)
            work = work.sort_values("_derived_risk", ascending=False).head(20)

            col_rename = {}
            if "AlarmId" in work.columns:
                col_rename["AlarmId"] = "id"
            if "dataset_vehicle_code" in work.columns:
                col_rename["dataset_vehicle_code"] = "vehicle_id"
            if "Type" in work.columns:
                col_rename["Type"] = "event_type"
            col_rename["_derived_risk"] = "risk_score"

            work = work.rename(columns=col_rename)
            cols = [col for col in ["id", "vehicle_id", "driver_id", "event_type", "risk_score", "reason"] if col in work.columns]
            return work[cols] if cols else work.head(20)

        if "severity" in df.columns:
            cols = [col for col in ["id", "vehicle_id", "driver_id", "event_type", "severity", "reason"] if col in df.columns]
            return df.head(20)[cols] if cols else df.head(20)

    return pd.DataFrame()


__all__ = ["build_dashboard_metrics", "build_risk_table"]
```

## Acceptance criteria

- [ ] Файл `app/metrics.py` создан/обновлён
- [ ] Обе функции принимают `dict[str, pd.DataFrame]` и возвращают корректные типы
- [ ] `build_dashboard_metrics` возвращает список из 4 словарей с непустыми `value`
- [ ] `build_risk_table` возвращает `pd.DataFrame` (пустой, если нет подходящих колонок)
- [ ] `from app.metrics import build_dashboard_metrics, build_risk_table` выполняется без ошибок
- [ ] Импорт `RISK_THRESHOLD` из `app.constants` работает
- [ ] Speed/Type fallback работает для selected_video_alarms.csv
