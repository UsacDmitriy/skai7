from __future__ import annotations

"""Мок-данные по транспортным средствам для MVP."""

VEHICLES: list[dict] = [
    {
        "id": "veh-001",
        "plate": "А777ВВ 77",
        "model": "ГАЗон NEXT",
        "driver": "Иванов Алексей Петрович",
        "division": "Логистика · Север-1",
        "alarm_count": 12,
        "alarm_types": "DMS_DROWSY|OVERSPEED|HARSH_BRAKING",
        "downloaded_video_count": 24,
        "total_track_mileage_km": 4520.5,
        "avg_speed_kmh": 68.3,
        "cameras": [
            {"id": "CAM-01", "label": "ADAS · Передняя", "status": "online"},
            {"id": "CAM-02", "label": "DMS · Салон", "status": "online"},
            {"id": "CAM-03", "label": "CH3 · Правая", "status": "offline"},
        ],
        "telematics_status": "online",
        "archive_status": "available",
        "connection_status": "online",
        "engine_hours": 12450,
        "last_maintenance": "2026-01-15",
    },
    {
        "id": "veh-002",
        "plate": "В345КМ 97",
        "model": "КамАЗ-5490",
        "driver": "Петров Дмитрий Сергеевич",
        "division": "Логистика · Центр",
        "alarm_count": 8,
        "alarm_types": "CRASH_SENSOR|HARSH_CORNERING",
        "downloaded_video_count": 16,
        "total_track_mileage_km": 8750.2,
        "avg_speed_kmh": 72.1,
        "cameras": [
            {"id": "CAM-01", "label": "ADAS · Передняя", "status": "online"},
            {"id": "CAM-02", "label": "DMS · Салон", "status": "online"},
            {"id": "CAM-03", "label": "CH3 · Задняя", "status": "offline"},
        ],
        "telematics_status": "online",
        "archive_status": "available",
        "connection_status": "online",
        "engine_hours": 8900,
        "last_maintenance": "2026-03-01",
    },
    {
        "id": "veh-003",
        "plate": "Е902СТ 150",
        "model": "ГАЗель NEXT",
        "driver": "Сидоров Владимир Николаевич",
        "division": "Доставка · Юг",
        "alarm_count": 15,
        "alarm_types": "DMS_PHONE|OVERSPEED|DMS_SEATBELT",
        "downloaded_video_count": 8,
        "total_track_mileage_km": 3200.8,
        "avg_speed_kmh": 82.4,
        "cameras": [
            {"id": "CAM-01", "label": "ADAS · Передняя", "status": "online"},
            {"id": "CAM-02", "label": "DMS · Салон", "status": "online"},
            {"id": "CAM-03", "label": "CH3 · Задняя", "status": "offline"},
        ],
        "telematics_status": "online",
        "archive_status": "warning",
        "connection_status": "online",
        "engine_hours": 5600,
        "last_maintenance": "2025-12-20",
    },
    {
        "id": "veh-004",
        "plate": "Н124УУ 199",
        "model": "МАЗ-5440",
        "driver": "Козлов Иван Андреевич",
        "division": "Логистика · Восток",
        "alarm_count": 21,
        "alarm_types": "HARSH_BRAKING|OVERSPEED|HARSH_ACCELERATION",
        "downloaded_video_count": 30,
        "total_track_mileage_km": 12100.0,
        "avg_speed_kmh": 76.8,
        "cameras": [
            {"id": "CAM-01", "label": "ADAS · Передняя", "status": "online"},
            {"id": "CAM-02", "label": "DMS · Салон", "status": "warning"},
        ],
        "telematics_status": "online",
        "archive_status": "available",
        "connection_status": "online",
        "engine_hours": 15300,
        "last_maintenance": "2026-02-10",
    },
    {
        "id": "veh-005",
        "plate": "К451МА 77",
        "model": "Volvo FH",
        "driver": "Новиков Александр Владимирович",
        "division": "Логистика · Запад",
        "alarm_count": 5,
        "alarm_types": "DRIVER_SUBSTITUTION|DMS_SMOKING",
        "downloaded_video_count": 10,
        "total_track_mileage_km": 6800.3,
        "avg_speed_kmh": 70.5,
        "cameras": [
            {"id": "CAM-01", "label": "ADAS · Передняя", "status": "online"},
            {"id": "CAM-02", "label": "DMS · Салон", "status": "online"},
        ],
        "telematics_status": "online",
        "archive_status": "available",
        "connection_status": "online",
        "engine_hours": 7200,
        "last_maintenance": "2026-04-01",
    },
]


def get_vehicle_by_plate(plate: str) -> dict | None:
    """Возвращает ТС по госномеру или None."""
    for v in VEHICLES:
        if v["plate"] == plate:
            return v
    return None
