"""Схема домена sabotage (контракт §7.5, идея #9).

`SabotageEvent` — строка детектора саботажа камеры: тёмный DMS / CAMERA_TAMPER
при движении ТС. Источник — view `v_sabotage` (b11) + `driver_name` из
`driver_reference` (§7.1, b7), досчитываемый сервисом.
"""

from __future__ import annotations

from pydantic import BaseModel


class SabotageEvent(BaseModel):
    """Событие саботажа камеры (§7.5). `video_url` nullable — доступного кадра может не быть.

    `verdict_confidence`/`verdict_reason` (b23, идея #16) — аддитивный «умный вердикт»:
    детерминированное усиление детекции кросс-проверкой сцены (b16/b17). Дефолты
    держат обратную совместимость: нет кэша сцены → базовая уверенность, нейтральная причина.
    """

    id: str
    vehicle_plate: str
    ts: str
    dms_dark: bool
    speed_kmh: float
    driver_name: str
    video_url: str | None = None
    verdict_confidence: float = 0.0
    verdict_reason: str = ""
