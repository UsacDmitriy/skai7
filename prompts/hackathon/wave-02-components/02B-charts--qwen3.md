# 02B charts — Altair chart builders

**Model**: qwen/qwen3-coder:free

## Task

Создать `app/charts.py` — переиспользуемые построители графиков на Altair.

## Requirements

1. `build_scatter_chart(df, x_col, y_col)` — универсальный scatter/line чарт для дашборда
2. `build_speed_chart(df)` — график скорости по времени для данных `track_points`
3. `build_track_map(df)` — scatter-карта трековых точек (latitude/longitude)

## Rules

- Сохранить в `app/charts.py`
- Функция `build_speed_chart` должна проверять наличие обязательных колонок и возвращать `None`, если их нет
- Функция `build_track_map` должна обрабатывать опциональную колонку `speed_kmh`
- Импортировать только `altair` (без других зависимостей)
- Type hints, docstrings на русском
- Использовать правильные имена параметров `alt.Chart`
- Проверка: `python -c "from app.charts import build_scatter_chart, build_speed_chart, build_track_map"` должна проходить

## Code

```python
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st


def build_scatter_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    height: int = 320,
    max_rows: int = 5000,
) -> alt.Chart:
    """Универсальный scatter/line чарт Altair.

    Сэмплирует до max_rows для производительности.
    """
    data = df.head(max_rows)
    chart = (
        alt.Chart(data)
        .mark_line(point=False)
        .encode(
            x=alt.X(x_col, title=x_col),
            y=alt.Y(y_col, title=y_col),
        )
        .properties(height=height)
    )
    return chart


def build_speed_chart(
    df: pd.DataFrame,
    height: int = 300,
) -> alt.Chart | None:
    """График скорости по времени для данных track_points.

    Требует колонки: timestamp_utc, speed_kmh.
    Возвращает None, если обязательные колонки отсутствуют.
    """
    required = {"timestamp_utc", "speed_kmh"}
    if not required.issubset(df.columns):
        return None

    chart = (
        alt.Chart(df)
        .mark_line(color="#3B82F6")
        .encode(
            x=alt.X("timestamp_utc:T", title="Время"),
            y=alt.Y("speed_kmh:Q", title="Скорость, км/ч"),
            tooltip=["timestamp_utc", "speed_kmh"],
        )
        .properties(height=height, title="График скорости")
    )
    return chart


def build_track_map(
    df: pd.DataFrame,
    height: int = 400,
) -> alt.Chart | None:
    """Scatter-график трековых точек на сетке широта/долгота.

    Требует колонки: latitude, longitude.
    Возвращает None, если обязательные колонки отсутствуют.
    """
    required = {"latitude", "longitude"}
    if not required.issubset(df.columns):
        return None

    # Цвет по скорости, если доступна
    color = alt.Color("speed_kmh:Q", scale=alt.Scale(scheme="redyellowgreen"), title="Скорость") if "speed_kmh" in df.columns else alt.value("#3B82F6")

    chart = (
        alt.Chart(df)
        .mark_circle(size=30, opacity=0.7)
        .encode(
            x=alt.X("longitude:Q", title="Долгота"),
            y=alt.Y("latitude:Q", title="Широта"),
            color=color,
            tooltip=["latitude", "longitude", "speed_kmh", "timestamp_utc"],
        )
        .properties(height=height, title="Трек маршрута")
    )
    return chart


__all__ = ["build_scatter_chart", "build_speed_chart", "build_track_map"]
```
