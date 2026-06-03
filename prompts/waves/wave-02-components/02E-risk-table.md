# 02E · risk_table.py
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать `app/constants.py` (~90 строк) · не читать `./data`, `.venv`, `node_modules`
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 2

**Файл:** `app/risk_table.py`

Генерация файла с нуля. Для контекста прочитать `app/constants.py` (ALARM_TYPE_LABELS, COLORS, RISK_THRESHOLD).

**Задача:** написать модуль `render_risk_table(datasets)` — enhanced risk table с цветными бейджами для уровней риска и типов алармов.

**Код:**

```python
from __future__ import annotations

import pandas as pd
import streamlit as st

from app.constants import ALARM_TYPE_LABELS, COLORS, RISK_THRESHOLD

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


def _risk_color(score: float) -> str:
    """Вернуть CSS-цвет для уровня риска."""
    if score >= 90:
        return COLORS["critical"]
    if score >= 70:
        return COLORS["high"]
    if score >= 40:
        return COLORS["warning"]
    return COLORS["low"]


def _label_event(event_type: str) -> str:
    """Перевести тип аларма в русскую метку."""
    return ALARM_TYPE_LABELS.get(event_type, event_type)


def _build_enhanced_risk_df(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Собрать расширенную таблицу рисков с маппингом меток и цветов.

    Ищет колонку risk_score, Speed/Type или severity во всех датасетах.
    Возвращает DataFrame, готовый к отображению.
    """
    for name, df in datasets.items():
        if "risk_score" in df.columns:
            result = df.sort_values("risk_score", ascending=False).head(20).copy()

            if "event_type" in result.columns:
                result["Тип события"] = result["event_type"].apply(_label_event)

            result["Уровень риска"] = result["risk_score"].apply(
                lambda s: (
                    "🔴 Критический" if s >= 90
                    else "🟠 Высокий" if s >= 70
                    else "🟡 Средний" if s >= 40
                    else "🔵 Низкий"
                )
            )

            cols = [
                col
                for col in ["id", "vehicle_id", "driver_id", "Тип события", "risk_score", "Уровень риска", "reason"]
                if col in result.columns
            ]
            return result[cols] if cols else result.head(20)

        if "Speed" in df.columns or "Type" in df.columns:
            result = df.copy()
            result["risk_score"] = _derive_risk_series(result)
            result = result.sort_values("risk_score", ascending=False).head(20)

            event_col = "Type" if "Type" in result.columns else None
            if event_col:
                result["Тип события"] = result[event_col].apply(_label_event)

            result["Уровень риска"] = result["risk_score"].apply(
                lambda s: (
                    "🔴 Критический" if s >= 90
                    else "🟠 Высокий" if s >= 70
                    else "🟡 Средний" if s >= 40
                    else "🔵 Низкий"
                )
            )

            col_rename = {}
            if "AlarmId" in result.columns:
                col_rename["AlarmId"] = "id"
            if "dataset_vehicle_code" in result.columns:
                col_rename["dataset_vehicle_code"] = "vehicle_id"
            result = result.rename(columns=col_rename)

            cols = [
                col
                for col in ["id", "vehicle_id", "driver_id", "Тип события", "risk_score", "Уровень риска", "reason"]
                if col in result.columns
            ]
            return result[cols] if cols else result.head(20)

        if "severity" in df.columns:
            result = df.head(20).copy()
            if "event_type" in result.columns:
                result["Тип события"] = result["event_type"].apply(_label_event)
            cols = [
                col for col in ["id", "vehicle_id", "driver_id", "Тип события", "severity", "reason"]
                if col in result.columns
            ]
            return result[cols] if cols else result.head(20)

    return pd.DataFrame()


def render_risk_table(datasets: dict[str, pd.DataFrame]) -> None:
    """Отрисовать расширенную таблицу рисков с русскими метками."""
    risk_df = _build_enhanced_risk_df(datasets)

    if risk_df.empty:
        st.info(
            "Нет данных с колонками risk_score, Speed, Type или severity. "
            "Добавьте events.csv с рисками или selected_video_alarms.csv."
        )
        return

    st.subheader("Таблица рисков")
    st.caption(f"Топ-{len(risk_df)} событий по уровню риска")

    st.dataframe(
        risk_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "risk_score": st.column_config.NumberColumn("Risk Score", format="%d"),
        },
    )


__all__ = ["render_risk_table"]
```

**Требования:**
- Сохранить строго в `app/risk_table.py`
- Импортировать константы из `app/constants.py`
- Использовать `st.dataframe` с `column_config` для лучшего рендеринга
- Использовать `ALARM_TYPE_LABELS` для русских названий типов событий
- Корректно обрабатывать отсутствующие колонки (пустой DataFrame + `st.info`)
- Поддерживать fallback на Speed/Type для selected_video_alarms.csv
- Type hints с `from __future__ import annotations`
- Докстринги на русском языке
- Двойные кавычки в коде

**Проверка:** `python -c "from app.risk_table import render_risk_table"`
