# 01E · app.py + requirements.txt + Streamlit-каркас
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия. Не запускать параллельно.**
# Модель: qwen/qwen3-coder:free · $0 · Волна 1
> ✅ Передать: только этот промпт (данные внутри)
> ❌ НЕ читать: AGENTS.md, hackathon/context/DESIGN.md

## Задача

Создать скелет Streamlit-приложения — `app/app.py` с тремя заглушками-вкладками.

Также создать `05_video_telematics_single_window/requirements.txt` с зависимостями.

## Файлы (все пути от корня репо)

```
app/app.py
05_video_telematics_single_window/requirements.txt
```

---

## app/app.py — каркас с тремя вкладками-заглушками

```python
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from app.data_loader import load_csv_files
from app.constants import PAGE_TITLE, PAGE_ICON, LAYOUT, DATA_DIR_NAME, SAMPLE_DATA_DIR_NAME

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / DATA_DIR_NAME
SAMPLE_DATA_DIR = PROJECT_ROOT / SAMPLE_DATA_DIR_NAME


st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT,
)


def render_data_tab(datasets: dict[str, pd.DataFrame]) -> None:
    """Заглушка — будет реализована в wave-03."""
    st.info("Вкладка «Данные» — появится в wave-03")


def render_dashboard_tab(datasets: dict[str, pd.DataFrame]) -> None:
    """Заглушка — будет реализована в wave-03."""
    st.info("Вкладка «Dashboard» — появится в wave-03")


def render_details_tab(datasets: dict[str, pd.DataFrame]) -> None:
    """Заглушка — будет реализована в wave-03."""
    st.info("Вкладка «Детали» — появится в wave-03")


def main() -> None:
    """Точка входа Streamlit-приложения SKAI Hackathon MVP."""
    st.title("SKAI Hackathon MVP")
    st.caption("Data → Logic → UI → Action. Keep it small, explainable, and demo-ready.")

    # Автоопределение источника данных
    data_source = DATA_DIR if any(DATA_DIR.glob("*.csv")) else SAMPLE_DATA_DIR
    datasets = load_csv_files(data_source)
    st.sidebar.caption(f"Чтение CSV из: {data_source.relative_to(PROJECT_ROOT)}")

    # Три вкладки
    data_tab, dashboard_tab, details_tab = st.tabs(["Данные", "Dashboard", "Детали"])
    with data_tab:
        render_data_tab(datasets)
    with dashboard_tab:
        render_dashboard_tab(datasets)
    with details_tab:
        render_details_tab(datasets)


if __name__ == "__main__":
    main()
```

---

## requirements.txt

```
streamlit==1.44.1
pandas==2.2.3
numpy==2.2.4
altair==5.5.0
```

---

## Acceptance criteria

- `streamlit run app/app.py` — запускается без ошибок
- Видны три вкладки: «Данные», «Dashboard», «Детали»
- Все три вкладки — заглушки с `st.info(...)`
- В сайдбаре отображается путь к источнику CSV
- `requirements.txt` создан, зависимости корректны
- Python 3.12, type hints с `from __future__ import annotations`
- Все docstrings на русском
