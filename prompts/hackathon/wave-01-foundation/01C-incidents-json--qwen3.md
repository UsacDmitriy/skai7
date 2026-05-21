# 01C · data_loader.py
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 1

**Файл:** `app/data_loader.py`
**Только этот файл.**

Создай модуль загрузки CSV и сохранения действий диспетчера. Функции:

1. `load_csv_files(data_dir: Path) -> dict[str, pd.DataFrame]` — рекурсивно обходит `data_dir`, читает все CSV в DataFrame, возвращает словарь `{относительный_путь: DataFrame}`.
2. `save_action(output_dir, row_id, action, comment="")` — дописывает одну строку в `output/actions.csv` в режиме `append`, с полями: `created_at`, `row_id`, `action`, `comment`.

Требования:
- `from __future__ import annotations`
- Аннотации типов на всех функциях
- Докстринги на русском языке
- `comment` — опциональный параметр со значением по умолчанию `""`
- `__all__` с именами экспортируемых функций
- Использовать `Path.mkdir(parents=True, exist_ok=True)` для создания директорий
- CSV создаётся с заголовком только если файла ещё нет (`header=not path.exists()`)

```python
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


def load_csv_files(data_dir: Path) -> dict[str, pd.DataFrame]:
    """Загружает все CSV-файлы из дерева директорий.

    Возвращает словарь, где ключи — относительные пути, значения — DataFrame.
    Поддерживает вложенные директории (например, work_rest_single_vehicle/).
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    datasets: dict[str, pd.DataFrame] = {}
    for path in sorted(data_dir.rglob("*.csv")):
        key = path.relative_to(data_dir).as_posix()
        datasets[key] = pd.read_csv(path)
    return datasets


def save_action(
    output_dir: Path,
    row_id: str,
    action: str,
    comment: str = "",
) -> None:
    """Добавляет запись действия в output/actions.csv."""
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


__all__ = ["load_csv_files", "save_action"]
```

**Check:** `python -c "from app.data_loader import load_csv_files, save_action"` без ошибок.
