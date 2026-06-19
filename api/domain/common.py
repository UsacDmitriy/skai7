"""Базовые типы домена (контракт §3.1).

Literal-алиасы вместо Enum — отдают в JSON ровно строки контракта и
проще валидируются на входе из DuckDB/enrichment.
"""

from __future__ import annotations

from typing import Literal

# § 3.1 — фиксированные множества значений.
Severity = Literal["critical", "high", "medium", "low"]

# DIAGNOSTIC — алярмы сенсорной диагностики (камера офлайн и т.п.), бейдж «⚙ Диагностика».
Source = Literal["DMS", "ADAS", "TELEMATICS", "COMBINED", "DIAGNOSTIC"]

# Единый enum статусов (§3.1): active · in_progress · validated · false_positive · closed.
Status = Literal["active", "in_progress", "validated", "false_positive", "closed"]

# Статус камеры (§2).
CameraStatus = Literal["online", "offline", "warning"]
