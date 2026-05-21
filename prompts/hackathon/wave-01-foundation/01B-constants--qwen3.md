# 01B · constants.py
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 1

**Файл:** `app/constants.py`
**Только этот файл.**

Передать: `AGENTS.md` (секция Inputs) + `hackathon/context/DESIGN.md`.
Экспортируй константы с type hints:

```python
from typing import Final

COLORS: Final[dict[str, str]] = {
    "primary": "#1E3A8A",
    "bg": "#F8FAFC",
    "text": "#0F172A",
    "muted": "#64748B",
    "border": "#E2E8F0",
    "critical": "#DC2626",
    "warning": "#EA580C",
    "ok": "#16A34A",
}

ALARM_TYPE_LABELS: Final[dict[str, str]] = {
    # все 13 типов событий VA на русском
}

RISK_THRESHOLD: Final[int] = 70

ACTION_TYPES: Final[list[str]] = ["check", "request_video", "create_report"]

ACTION_LABELS: Final[dict[str, str]] = {
    "check": "Проверено",
    "request_video": "Запросить видео",
    "create_report": "Создать отчёт",
}

SPEED_LIMIT_KMH: Final[int] = 90

PAGE_TITLE: Final[str] = "Единое окно видео и телематики"
PAGE_ICON: Final[str] = "📹"
LAYOUT: Final[str] = "wide"

DATA_DIR_NAME: Final[str] = "data"
SAMPLE_DATA_DIR_NAME: Final[str] = "data/work_rest_single_vehicle"
OUTPUT_DIR_NAME: Final[str] = "output"

KPI_LABELS: Final[dict[str, str]] = {
    "csv_files": "CSV-файлов",
    "rows_loaded": "Строк загружено",
    "candidate_events": "Событий-кандидатов",
    "mvp_status": "Статус MVP",
}
```

`ALARM_TYPE_LABELS` заполни всеми 13 типами событий из `selected_video_alarms.csv` на русском. Если прочитать CSV нельзя — используй стандартные типы VA: `Speeding`, `HarshBraking`, `HarshAcceleration`, `HarshCornering`, `Drowsiness`, `Distraction`, `Smoking`, `PhoneCall`, `Seatbelt`, `Geofence`, `Panic`, `NoSignal`, `Other`.

**Check:** `python -c "from app.constants import *"` без ошибок.
