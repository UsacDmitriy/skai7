from __future__ import annotations

"""Константы для SKAI Hackathon — единое окно видео и телематики."""

__all__ = [
    "COLORS",
    "SEVERITY_COLORS",
    "ALARM_TYPE_LABELS",
    "ALARM_TYPE_COLORS",
    "RISK_THRESHOLD",
    "SPEED_LIMIT_KMH",
    "ACTION_TYPES",
    "ACTION_LABELS",
    "STATUS_LABELS",
    "SOURCE_LABELS",
    "PAGE_TITLE",
    "PAGE_ICON",
    "LAYOUT",
    "CHART_HEIGHT",
]

COLORS = {
    "primary": "#1E3A8A",
    "primary_dark": "#1E3070",
    "primary_50": "#EFF6FF",
    "bg": "#F8FAFC",
    "surface": "#FFFFFF",
    "text": "#0F172A",
    "muted": "#64748B",
    "border": "#E2E8F0",
    "border_focus": "#1E3A8A",
    "critical": "#DC2626",
    "critical_bg": "#FEE2E2",
    "critical_text": "#991B1B",
    "high": "#EA580C",
    "high_bg": "#FEF3C7",
    "high_text": "#B45309",
    "warning": "#EAB308",
    "warning_bg": "#FEF9C3",
    "warning_text": "#854D0E",
    "medium": "#3B82F6",
    "medium_bg": "#DBEAFE",
    "medium_text": "#1E40AF",
    "ok": "#16A34A",
    "ok_bg": "#DCFCE7",
    "ok_text": "#166534",
    "dark_bg": "#0F172A",
    "dark_surface": "#1E293B",
    "dark_border": "#334155",
    "dark_text": "#E2E8F0",
    "dark_muted": "#94A3B8",
    "chart_colors": ["#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4"],
}

SEVERITY_COLORS = {
    "critical": {"border": "#DC2626", "bg": "#FEE2E2", "text": "#991B1B", "dot": "#DC2626"},
    "high": {"border": "#EA580C", "bg": "#FEF3C7", "text": "#B45309", "dot": "#EA580C"},
    "medium": {"border": "#3B82F6", "bg": "#DBEAFE", "text": "#1E40AF", "dot": "#3B82F6"},
    "low": {"border": "#16A34A", "bg": "#DCFCE7", "text": "#166534", "dot": "#16A34A"},
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
    "DMS_DROWSY": "Засыпание за рулём (микросон)",
    "DMS_PHONE": "Использование телефона",
    "DMS_SEATBELT": "Ремень безопасности",
    "DMS_SMOKING": "Курение",
    "ADAS_FCW": "Опасное сближение",
    "ADAS_HMW": "Контроль полосы",
    "ADAS_LDW": "Выезд с полосы",
    "CRASH_SENSOR": "Подозрение на ДТП — датчик удара",
    "HARSH_BRAKING": "Резкое торможение",
    "HARSH_CORNERING": "Резкий поворот",
    "OVERSPEED": "Превышение скорости",
    "CAMERA_OFFLINE": "Камера неисправна",
    "DRIVER_SUBSTITUTION": "Подмена водителя",
}

ALARM_TYPE_COLORS = {
    "critical": {"border": "#DC2626", "bg": "#FEE2E2", "text": "#991B1B", "dot": "#DC2626"},
    "high": {"border": "#EA580C", "bg": "#FEF3C7", "text": "#B45309", "dot": "#EA580C"},
    "medium": {"border": "#3B82F6", "bg": "#DBEAFE", "text": "#1E40AF", "dot": "#3B82F6"},
    "low": {"border": "#16A34A", "bg": "#DCFCE7", "text": "#166534", "dot": "#16A34A"},
}

RISK_THRESHOLD = 70
SPEED_LIMIT_KMH = 90

ACTION_TYPES = ["mark_reviewed", "create_task", "export_report", "request_archive", "call_driver"]
ACTION_LABELS = {
    "mark_reviewed": "Пометить как проверено",
    "create_task": "Создать заявку",
    "export_report": "Сформировать отчёт",
    "request_archive": "Запросить архивное видео",
    "call_driver": "Вызов водителя",
}

STATUS_LABELS = {
    "active": "Новая",
    "in_progress": "В работе",
    "validated": "Проверена",
    "closed": "Закрыта",
}

SOURCE_LABELS = {
    "DMS": "📹 ВА",
    "ADAS": "📹 ADAS",
    "TELEMATICS": "⚡ Телематика",
    "COMBINED": "⚡📹 Оба",
}

PAGE_TITLE = "SKAI — Единое окно видео и телематики"
PAGE_ICON = "SKAI"
LAYOUT = "wide"

CHART_HEIGHT = 320