from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


def load_csv_files(data_dir: Path) -> dict[str, pd.DataFrame]:
    data_dir.mkdir(parents=True, exist_ok=True)
    datasets: dict[str, pd.DataFrame] = {}
    for path in sorted(data_dir.rglob("*.csv")):
        datasets[path.relative_to(data_dir).as_posix()] = pd.read_csv(path)
    return datasets


def save_action(output_dir: Path, row_id: str, action: str, comment: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "actions.csv"
    record = pd.DataFrame(
        [
            {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "row_id": row_id,
                "action": action,
                "comment": comment,
            }
        ]
    )
    record.to_csv(path, mode="a", header=not path.exists(), index=False)
