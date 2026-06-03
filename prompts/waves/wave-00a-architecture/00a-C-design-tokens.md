# Волна 00a-C — Design Tokens
> 🤖 **Модель: `qwen/qwen3-coder:free`** | создание app/constants.py
> 💰 **Контекст:** только промпт ниже (~$0)
> ⚠️ Можно запускать одновременно с 00a-B (разные сессии Cherry Studio)

## Промпт

```
Создай файл app/constants.py — design tokens и константы для Streamlit-приложения SKAI.

Требования к файлу:
- from __future__ import annotations в первой строке
- __all__ в начале модуля
- docstring вверху модуля на русском
- Только код, без объяснений

Содержимое:

```python
# Streamlit color constants (for st.markdown with custom CSS)
COLORS = {
    "primary": "#1E3A8A",       # deep blue — main headers
    "bg": "#F8FAFC",            # slate-50 — page background
    "surface": "#FFFFFF",       # white — cards/metrics backgrounds
    "text": "#0F172A",          # slate-900 — body text
    "muted": "#64748B",         # slate-500 — captions, secondary text
    "border": "#E2E8F0",        # slate-200 — separators
    "critical": "#DC2626",      # red-600 — critical risk, errors
    "high": "#EA580C",          # orange-600 — high risk
    "warning": "#F59E0B",       # amber-500 — warnings
    "medium": "#CA8A04",        # yellow-600 — medium risk
    "ok": "#16A34A",            # green-600 — success, OK status
    "low": "#2563EB",           # blue-600 — low risk
    "info": "#0891B2",          # cyan-600 — informational
    "chart_colors": ["#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4"],
}

# Alarm type labels (Russian)
ALARM_TYPE_LABELS = {
    "Drowsiness": "Засыпание",
    "Overspeeding": "Превышение скорости",
    "HarshBraking": "Резкое торможение",
    "HarshAcceleration": "Резкое ускорение",
    "HarshCornering": "Резкий поворот",
    "PhoneUsage": "Использование телефона",
    "Smoking": "Курение",
    "SeatBelt": "Ремень безопасности",
    "DriverSubstitution": "Подмена водителя",
    "LaneDeparture": "Выезд с полосы",
    "ForwardCollision": "Опасное сближение",
}

# Risk score thresholds
RISK_THRESHOLD = 70  # events with risk_score >= 70 are candidates

# Action types
ACTION_TYPES = ["mark_reviewed", "create_task", "export_report"]
ACTION_LABELS = {
    "mark_reviewed": "Пометить как проверено",
    "create_task": "Создать заявку",
    "export_report": "Сформировать отчёт",
}

# Speed limit defaults
SPEED_LIMIT_KMH = 90
DROWSY_THRESHOLD_MIN = 120  # continuous driving minutes before drowsiness risk

# Page config
PAGE_TITLE = "SKAI Hackathon MVP"
PAGE_ICON = "SKAI"
LAYOUT = "wide"
```

Не придумывай новые цвета — используй только те, что указаны выше (они соответствуют дизайну приложения).
```
