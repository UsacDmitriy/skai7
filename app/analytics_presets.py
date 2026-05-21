from __future__ import annotations

"""Пресеты аналитических запросов для экрана Аналитики."""

PRESETS = [
    {
        "id": "preset_driver",
        "icon": "🚗",
        "title": "Анализ по водителю",
        "description": "Нарушения + телеметрия + видео конкретного водителя",
        "query": "Покажи нарушения по ВА и телематике у {driver} за последние три дня",
        "params": {
            "mode": "driver",
            "driver": "Иванов А.П.",
            "period": "3 дня",
            "sources": "ВА + телематика",
        },
    },
    {
        "id": "preset_fleet",
        "icon": "📊",
        "title": "Отчёт по парку",
        "description": "Сводка по всем ТС с рейтингом риска",
        "query": "Сводка по всем ТС с рейтингом риска за неделю",
        "params": {
            "mode": "fleet",
            "period": "7 дней",
            "sort_by": "risk_score",
        },
    },
    {
        "id": "preset_critical",
        "icon": "⚠",
        "title": "Критические события за неделю",
        "description": "Все критические инциденты за 7 дней",
        "query": "Покажи все критические инциденты за последнюю неделю",
        "params": {
            "mode": "fleet",
            "risk_level": "critical",
            "period": "7 дней",
        },
    },
    {
        "id": "preset_video_digest",
        "icon": "📹",
        "title": "Видео-дайджест",
        "description": "Подборка видео по выбранному типу нарушений",
        "query": "Собери видео по превышениям скорости за сегодня",
        "params": {
            "mode": "video",
            "event_type": "Overspeeding",
            "period": "1 день",
        },
    },
]