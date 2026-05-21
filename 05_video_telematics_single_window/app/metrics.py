from __future__ import annotations

import pandas as pd


def build_dashboard_metrics(datasets: dict[str, pd.DataFrame]) -> list[dict[str, str]]:
    total_rows = sum(len(df) for df in datasets.values())
    total_files = len(datasets)
    candidate_events = 0
    for df in datasets.values():
        if "risk_score" in df.columns:
            candidate_events += int((df["risk_score"] >= 70).sum())
        elif "severity" in df.columns:
            candidate_events += int(df["severity"].astype(str).str.lower().isin(["high", "critical"]).sum())

    return [
        {"label": "CSV files", "value": str(total_files)},
        {"label": "Rows loaded", "value": f"{total_rows:,}".replace(",", " ")},
        {"label": "Candidate events", "value": str(candidate_events)},
        {"label": "MVP status", "value": "Demo"},
    ]


def build_risk_table(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    for name, df in datasets.items():
        if "risk_score" in df.columns:
            cols = [col for col in ["id", "vehicle_id", "driver_id", "event_type", "risk_score", "reason"] if col in df.columns]
            result = df.sort_values("risk_score", ascending=False).head(20)
            return result[cols] if cols else result.head(20)
        if "severity" in df.columns:
            cols = [col for col in ["id", "vehicle_id", "driver_id", "event_type", "severity", "reason"] if col in df.columns]
            return df.head(20)[cols] if cols else df.head(20)
    return pd.DataFrame()

