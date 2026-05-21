from __future__ import annotations

"""Design-токены и константы Streamlit-приложения SKAI Unified Incident Window."""

__all__ = [
    "COLORS",
    "ALARM_TYPE_LABELS",
    "RISK_THRESHOLD",
    "ACTION_TYPES",
    "ACTION_LABELS",
    "SPEED_LIMIT_KMH",
    "PAGE_TITLE",
    "PAGE_ICON",
    "LAYOUT",
]

COLORS = {
    "primary": "#1E3A8A",
    "bg": "#F8FAFC",
    "surface": "#FFFFFF",
    "text": "#0F172A",
    "muted": "#64748B",
    "border": "#E2E8F0",
    "critical": "#DC2626",
    "high": "#EA580C",
    "warning": "#F59E0B",
    "medium": "#CA8A04",
    "ok": "#16A34A",
    "low": "#2563EB",
    "info": "#0891B2",
    "chart_colors": ["#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4"],
}

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
    "Distraction": "Отвлечение",
    "DangerousDistance": "Опасная дистанция",
    "SharpAcceleration": "Резкое ускорение",
    "Sabotage": "Саботаж камеры",
    "Yawning": "Зевание",
}

RISK_THRESHOLD = 70

ACTION_TYPES = ["mark_reviewed", "create_task", "export_report"]
ACTION_LABELS = {
    "mark_reviewed": "Пометить как проверено",
    "create_task": "Создать заявку",
    "export_report": "Сформировать отчёт",
}

SPEED_LIMIT_KMH = 90

PAGE_TITLE = "SKAI — Единое окно видео и телематики"
PAGE_ICON = "SKAI"
LAYOUT = "wide"
