# Промпт 4 — QA и интеграция Streamlit-приложения

Задача: настроить тестирование и проверку работоспособности Streamlit MVP.

Рабочая директория: `05_video_telematics_single_window/`

## Шаг 1. Создать директорию `tests/`

Создать директорию `tests/` внутри `05_video_telematics_single_window/`:

```bash
mkdir -p 05_video_telematics_single_window/tests
```

## Шаг 2. Модульные тесты загрузчика данных

Создать файл `tests/test_data_loader.py`:

```python
from pathlib import Path
from app.data_loader import load_csv_files, save_action


def test_load_csv_files():
    ds = load_csv_files(Path("data"))
    assert len(ds) >= 7, f"Expected >=7 datasets, got {len(ds)}"
    for name, df in ds.items():
        assert not df.empty, f"Dataset {name} is empty"
        assert len(df.columns) > 0, f"Dataset {name} has no columns"


def test_save_action(tmp_path):
    save_action(tmp_path, "test-1", "mark_reviewed", "ok")
    path = tmp_path / "actions.csv"
    assert path.exists()
```

## Шаг 3. Модульные тесты метрик

Создать файл `tests/test_metrics.py`:

```python
import pandas as pd
from app.metrics import build_dashboard_metrics


def test_build_dashboard_metrics():
    ds = {"test": pd.DataFrame({"risk_score": [50, 80, 90]})}
    metrics = build_dashboard_metrics(ds)
    assert len(metrics) == 4
    assert metrics[0]["label"] == "CSV файлов"
    assert metrics[2]["value"] == "2"  # 80 and 90 >= 70
```

## Шаг 4. Установить pytest

```bash
pip install pytest
```

## Шаг 5. Запустить тесты

Из корня `05_video_telematics_single_window/`:

```bash
python -m pytest tests/ -v
```

Ожидаемый результат: все тесты проходят (зеленые).

## Шаг 6. Дымовой (smoke) тест

Создать скрипт `scripts/smoke_test.sh`:

```bash
#!/bin/bash
echo "=== Smoke Test SKAI MVP ==="
python -c "from app.data_loader import load_csv_files; ds = load_csv_files('data'); print(f'OK: {len(ds)} datasets loaded')"
python -c "from app.metrics import build_dashboard_metrics; print('OK: metrics module')"
python -c "from app.charts import build_scatter_chart; print('OK: charts module')"
python -c "from app.risk_table import render_risk_table; print('OK: risk table module')"
python -c "from app.actions import render_action_form; print('OK: actions module')"
echo "=== ALL SMOKE TESTS PASSED ==="
```

Сделать скрипт исполняемым:

```bash
chmod +x scripts/smoke_test.sh
```

## Шаг 7. Запустить дымовой тест

```bash
./scripts/smoke_test.sh
```

Ожидаемый результат: каждый модуль импортируется и инициализируется без ошибок, финальная строка `=== ALL SMOKE TESTS PASSED ===`.

## Критерии приемки

- `pytest tests/ -v` проходит без ошибок
- `./scripts/smoke_test.sh` проходит без ошибок
- Оба теста документируют, что ключевые модули приложения работают корректно
