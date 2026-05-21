"""Обзор датасетов и превью для Streamlit-приложения SKAI Hackathon MVP."""

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
    names = sorted(datasets.keys())
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
