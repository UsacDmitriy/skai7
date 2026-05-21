# 02C · data_overview.py
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 2

**Файл:** `app/data_overview.py`

Генерация файла с нуля. Никакой код не нужен для контекста — только создать файл и импортировать pandas, streamlit.

**Задача:** написать модуль с тремя функциями:

1. `build_dataset_overview(datasets)` — возвращает DataFrame с колонками: file (имя), rows (строк), columns (колонок)
2. `pick_dataset(datasets)` — Streamlit sidebar selectbox для выбора датасета, возвращает `(name, DataFrame)`
3. `render_dataset_preview(df, name)` — рендерит `st.dataframe` с `head(100)`

**Код:**

```python
from __future__ import annotations

import pandas as pd
import streamlit as st


def build_dataset_overview(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Собрать сводную таблицу: имя файла, число строк, число колонок."""
    rows = [
        {"file": name, "rows": len(df), "columns": len(df.columns)}
        for name, df in sorted(datasets.items())
    ]
    return pd.DataFrame(rows)


def pick_dataset(datasets: dict[str, pd.DataFrame]) -> tuple[str | None, pd.DataFrame]:
    """Отрисовать selectbox в сайдбаре и вернуть (имя_выбранного, выбранный_df)."""
    if not datasets:
        return None, pd.DataFrame()
    names = sorted(datasets)
    selected = st.sidebar.selectbox("Датасет", names)
    return selected, datasets[selected]


def render_dataset_preview(
    df: pd.DataFrame,
    name: str,
    max_rows: int = 100,
) -> None:
    """Отрисовать превью данных с заголовком и датафреймом."""
    if df.empty:
        st.info("Датасет пуст.")
        return
    st.caption(f"Превью: {name}")
    st.dataframe(df.head(max_rows), use_container_width=True)


__all__ = ["build_dataset_overview", "pick_dataset", "render_dataset_preview"]
```

**Требования:**
- Сохранить строго в `app/data_overview.py` (создать директорию `app/` при необходимости)
- Все функции должны корректно обрабатывать пустые датасеты
- Type hints с `from __future__ import annotations`
- Докстринги на русском языке
- Использовать двойные кавычки в коде

**Проверка:** `python -c "from app.data_overview import build_dataset_overview, pick_dataset, render_dataset_preview"`
