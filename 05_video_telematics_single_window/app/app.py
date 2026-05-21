from __future__ import annotations

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from data_loader import load_csv_files, save_action
from metrics import build_dashboard_metrics, build_risk_table


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_DATA_DIR = PROJECT_ROOT / "sample_data"
OUTPUT_DIR = PROJECT_ROOT / "output"


st.set_page_config(
    page_title="SKAI Hackathon MVP",
    page_icon="SKAI",
    layout="wide",
)


def pick_dataset(datasets: dict[str, pd.DataFrame]) -> tuple[str | None, pd.DataFrame]:
    if not datasets:
        return None, pd.DataFrame()
    names = sorted(datasets)
    selected = st.sidebar.selectbox("Dataset", names)
    return selected, datasets[selected]


def render_data_tab(datasets: dict[str, pd.DataFrame]) -> None:
    st.subheader("Loaded CSV files")
    if not datasets:
        st.warning("No CSV files found. Put files into ./data or copy examples from ./sample_data.")
        return

    overview = pd.DataFrame(
        [
            {"file": name, "rows": len(df), "columns": len(df.columns)}
            for name, df in sorted(datasets.items())
        ]
    )
    st.dataframe(overview, use_container_width=True, hide_index=True)

    selected, df = pick_dataset(datasets)
    if selected:
        st.caption(f"Preview: {selected}")
        st.dataframe(df.head(100), use_container_width=True)


def render_dashboard_tab(datasets: dict[str, pd.DataFrame]) -> None:
    st.subheader("Dashboard")
    metrics = build_dashboard_metrics(datasets)
    cols = st.columns(4)
    for col, item in zip(cols, metrics, strict=False):
        col.metric(item["label"], item["value"], item.get("delta"))

    selected, df = pick_dataset(datasets)
    if not selected or df.empty:
        st.info("Add data to see charts.")
        return

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if len(numeric_cols) >= 2:
        x_col = st.selectbox("X axis", numeric_cols, index=0)
        y_col = st.selectbox("Y axis", numeric_cols, index=1)
        chart = (
            alt.Chart(df.head(5000))
            .mark_line(point=False)
            .encode(x=alt.X(x_col, title=x_col), y=alt.Y(y_col, title=y_col))
            .properties(height=320)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Need at least two numeric columns for the default chart.")


def render_details_tab(datasets: dict[str, pd.DataFrame]) -> None:
    st.subheader("Details and actions")
    risk_table = build_risk_table(datasets)
    if risk_table.empty:
        st.info("Implement build_risk_table() in app/metrics.py for your task-specific logic.")
        return

    st.dataframe(risk_table, use_container_width=True, hide_index=True)
    with st.form("action_form"):
        row_id = st.text_input("Record / vehicle / driver ID")
        action = st.selectbox("Action", ["mark_reviewed", "create_task", "export_report"])
        comment = st.text_area("Comment", height=80)
        submitted = st.form_submit_button("Save action")

    if submitted:
        save_action(OUTPUT_DIR, row_id=row_id, action=action, comment=comment)
        st.success("Action saved to ./output/actions.csv")


def main() -> None:
    st.title("SKAI Hackathon MVP")
    st.caption("Data -> Logic -> UI -> Action. Keep it small, explainable, and demo-ready.")

    data_source = DATA_DIR if any(DATA_DIR.glob("*.csv")) else SAMPLE_DATA_DIR
    datasets = load_csv_files(data_source)
    st.sidebar.caption(f"Reading CSV from: {data_source.relative_to(PROJECT_ROOT)}")

    data_tab, dashboard_tab, details_tab = st.tabs(["Data", "Dashboard", "Details"])
    with data_tab:
        render_data_tab(datasets)
    with dashboard_tab:
        render_dashboard_tab(datasets)
    with details_tab:
        render_details_tab(datasets)


if __name__ == "__main__":
    main()

