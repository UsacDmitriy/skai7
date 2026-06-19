# РЭБ-зоны: детекция аномалий Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить детекцию аномалий телеметрии (gap/speed_spike/coord_jump) с confidence scoring, endpoint `/api/reb/anomalies` и React-компонент `RebAnomalyLayer` на карте монитора.

**Architecture:** Новый сервис `reb_anomaly_service.py` загружает три типа аномалий из DuckDB, кластеризует DBSCAN и присваивает confidence score каждой зоне. Новый endpoint возвращает `list[RebAnomalyZone]`. Новый frontend-компонент рисует круги зон, маркеры ТС и пунктиры возможного маршрута через императивный Leaflet (как RiskHeatLayer).

**Tech Stack:** Python 3.12, FastAPI, DuckDB, Pydantic v2, scikit-learn DBSCAN; React 18, TypeScript, react-leaflet 4, Leaflet 1, Vitest, Testing Library

## Global Constraints

- SQL-идентификаторы в двойных кавычках: `"column_name"` — никогда без кавычек
- `from __future__ import annotations` — первая строка каждого Python-модуля
- Не изменять: `zones_service.py`, `RiskHeatLayer.tsx`, `RebRecovery.tsx`, `NavProblemList.tsx`, `reb_service.py`
- Backend тесты запускать: `pytest api/tests/ -q` из корня проекта
- Frontend тесты запускать: `cd web && npx vitest run`
- Typecheck frontend: `cd web && npx tsc --noEmit`
- Ветка: `integration`

---

## Файловая карта

| Действие | Путь |
|----------|------|
| Create | `api/services/reb_anomaly_service.py` |
| Create | `api/tests/test_reb_anomaly_service.py` |
| Create | `api/tests/test_reb_anomaly_api.py` |
| Create | `web/src/components/reb/RebAnomalyLayer.tsx` |
| Create | `web/src/components/reb/RebAnomalyLayer.test.tsx` |
| Modify | `api/domain/entities.py` — +3 Pydantic-модели в конец файла |
| Modify | `api/routers/reb.py` — +1 endpoint |
| Modify | `web/src/api/types.ts` — +3 TypeScript-интерфейса |
| Modify | `web/src/api/client.ts` — +`getRebAnomalies()` |
| Modify | `web/src/pages/Monitor.tsx` — `LayerKey` + тоггл + слой |

---

## Task 1: Pydantic-сущности

**Files:**
- Modify: `api/domain/entities.py` — добавить в конец файла

**Interfaces:**
- Produces: `AnomalyType`, `VehicleAnomaly`, `RebAnomalyZone` — используются Task 2, Task 4

- [ ] **Step 1: Добавить модели в entities.py**

Открыть `api/domain/entities.py`, найти конец файла (последнюю строку после `FatigueChain`) и дописать:

```python
# ---------------------------------------------------------------------------
# REB Anomaly Zones (reb_anomaly_service)
# ---------------------------------------------------------------------------

from enum import Enum


class AnomalyType(str, Enum):
    gap = "gap"
    speed_spike = "speed_spike"
    coord_jump = "coord_jump"


class VehicleAnomaly(BaseModel):
    """Одно ТС в РЭБ-зоне с наиболее тяжёлой аномалией."""

    vehicle_plate: str
    anomaly_type: AnomalyType
    max_speed_kmh: float | None
    lat: float
    lon: float
    ts_start: str
    ts_end: str | None
    possible_route: list[list[float]]
    reb_link_id: str | None


class RebAnomalyZone(BaseModel):
    """Кластер аномалий телеметрии с оценкой достоверности РЭБ-подавления."""

    zone_id: str
    centroid: list[float]
    radius_m: float
    confidence: int
    confidence_label: str
    vehicles: list[VehicleAnomaly]
    event_count: int
    date_count: int
```

- [ ] **Step 2: Проверить импорт Enum**

В начале `api/domain/entities.py` уже есть `from typing import Literal`. `Enum` в стандартной библиотеке, но нет импорта `from enum import Enum`. Убедиться что строка `from enum import Enum` добавлена (она идёт внутри блока выше — в секции REB Anomaly Zones). Это корректно — импорт внутри модуля Python допускается, но чище вынести наверх. Добавить `from enum import Enum` в заголовок файла рядом с другими импортами:

```python
from enum import Enum
```

И удалить `from enum import Enum` из блока REB Anomaly Zones (оставить только `class AnomalyType`).

- [ ] **Step 3: Проверить синтаксис**

```bash
cd /Users/dimausac/projects/skai_7 && python -c "from api.domain.entities import AnomalyType, VehicleAnomaly, RebAnomalyZone; print('ok')"
```

Ожидаемый вывод: `ok`

- [ ] **Step 4: Commit**

```bash
git add api/domain/entities.py
git commit -m "feat: add AnomalyType/VehicleAnomaly/RebAnomalyZone entities"
```

---

## Task 2: Backend сервис reb_anomaly_service.py

**Files:**
- Create: `api/services/reb_anomaly_service.py`

**Interfaces:**
- Consumes: `AnomalyType`, `VehicleAnomaly`, `RebAnomalyZone` из `api.domain.entities`; `rows_to_dicts` из `api.repositories`
- Produces: `detect_anomalies(db: duckdb.DuckDBPyConnection) -> list[RebAnomalyZone]`

- [ ] **Step 1: Создать файл с заголовком и утилитами**

```python
"""Сервис детекции РЭБ-аномалий телеметрии.

Три источника аномалий:
  gap         — period_type=3 (потеря GPS-сигнала)
  speed_spike — speed_kmh > 150 (нереальная скорость при джаммировании)
  coord_jump  — implied_speed > 300 км/ч между соседними точками

Все три кластеризуются DBSCAN (eps≈5 км), каждому кластеру присваивается
confidence score. Зоны с score < 20 отбрасываются как шум.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

import duckdb
import numpy as np
from sklearn.cluster import DBSCAN

from api.domain.entities import AnomalyType, RebAnomalyZone, VehicleAnomaly
from api.repositories import rows_to_dicts

_EPS_RAD: float = 5_000 / 6_371_000  # ≈5 км в радианах
_MIN_SAMPLES: int = 2
_SPEED_SPIKE_THRESHOLD = 150.0   # км/ч — выше → speed_spike аномалия
_COORD_JUMP_THRESHOLD = 300.0    # км/ч — implied speed выше → coord_jump
_ANOMALY_PRIORITY = {
    AnomalyType.gap: 3,
    AnomalyType.coord_jump: 2,
    AnomalyType.speed_spike: 1,
}


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Расстояние в метрах между двумя точками (Haversine)."""
    r = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _parse_ts(value: str | None) -> datetime | None:
    """ISO → aware datetime. Нормализует 'Z' → '+00:00'."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
```

- [ ] **Step 2: Добавить _load_gap_periods**

```python
def _load_gap_periods(db: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """Gap-периоды (period_type=3) с позицией из предыдущего периода."""
    rows = rows_to_dicts(db.execute(
        """
        SELECT
            p."vehicle_id"    AS vehicle_plate,
            p."public_unit_id" AS unit_id,
            CAST(p."date" AS VARCHAR) AS date,
            p."period_index"  AS period_index,
            (
                CAST(list_element(string_split(p."period_duration", ':'), 1) AS BIGINT) * 3600
              + CAST(list_element(string_split(p."period_duration", ':'), 2) AS BIGINT) * 60
              + CAST(list_element(string_split(p."period_duration", ':'), 3) AS BIGINT)
            ) AS duration_sec,
            COALESCE(p."distance_odometer_km", 0.0) AS odometer_km,
            (
                SELECT CAST(tp2."latitude" AS DOUBLE)
                FROM "navigation__track_points" tp2
                WHERE tp2."public_unit_id" = p."public_unit_id"
                  AND tp2."date" = p."date"
                  AND tp2."period_index" = p."period_index" - 1
                ORDER BY tp2."timestamp" DESC LIMIT 1
            ) AS lat,
            (
                SELECT CAST(tp2."longitude" AS DOUBLE)
                FROM "navigation__track_points" tp2
                WHERE tp2."public_unit_id" = p."public_unit_id"
                  AND tp2."date" = p."date"
                  AND tp2."period_index" = p."period_index" - 1
                ORDER BY tp2."timestamp" DESC LIMIT 1
            ) AS lon,
            (
                SELECT CAST(tp2."timestamp" AS VARCHAR)
                FROM "navigation__track_points" tp2
                WHERE tp2."public_unit_id" = p."public_unit_id"
                  AND tp2."date" = p."date"
                  AND tp2."period_index" = p."period_index" - 1
                ORDER BY tp2."timestamp" DESC LIMIT 1
            ) AS ts
        FROM "navigation__track_periods" p
        WHERE p."period_type" = 3
        """
    ))
    result = []
    for r in rows:
        if r["lat"] is None or r["lon"] is None:
            continue
        lat, lon = float(r["lat"]), float(r["lon"])
        if lat == 0.0 and lon == 0.0:
            continue
        result.append({
            "vehicle_plate": str(r["vehicle_plate"]),
            "unit_id": str(r["unit_id"]),
            "date": str(r["date"]),
            "period_index": int(r["period_index"]),
            "duration_sec": int(r["duration_sec"] or 0),
            "odometer_km": float(r["odometer_km"] or 0.0),
            "lat": lat,
            "lon": lon,
            "ts": str(r["ts"] or ""),
            "anomaly_type": AnomalyType.gap,
            "speed_kmh": None,
        })
    return result
```

- [ ] **Step 3: Добавить _load_speed_spikes**

```python
def _load_speed_spikes(db: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """GPS-точки с speed_kmh > 150 (нереальная скорость при РЭБ-подавлении)."""
    rows = rows_to_dicts(db.execute(
        f"""
        SELECT
            p."vehicle_id"          AS vehicle_plate,
            CAST(tp."latitude"  AS DOUBLE) AS lat,
            CAST(tp."longitude" AS DOUBLE) AS lon,
            CAST(tp."timestamp" AS VARCHAR) AS ts,
            CAST(tp."speed_kmh" AS DOUBLE) AS speed_kmh
        FROM "navigation__track_points" tp
        JOIN "navigation__track_periods" p
          ON tp."public_unit_id" = p."public_unit_id"
         AND tp."date"           = p."date"
         AND tp."period_index"   = p."period_index"
        WHERE tp."speed_kmh" > {_SPEED_SPIKE_THRESHOLD}
          AND tp."latitude"  IS NOT NULL
          AND tp."longitude" IS NOT NULL
        """
    ))
    result = []
    for r in rows:
        lat, lon = float(r["lat"]), float(r["lon"])
        if lat == 0.0 and lon == 0.0:
            continue
        result.append({
            "vehicle_plate": str(r["vehicle_plate"]),
            "lat": lat,
            "lon": lon,
            "ts": str(r["ts"] or ""),
            "speed_kmh": float(r["speed_kmh"]),
            "anomaly_type": AnomalyType.speed_spike,
            "duration_sec": 0,
            "odometer_km": 0.0,
            "unit_id": None,
            "date": None,
            "period_index": None,
        })
    return result
```

- [ ] **Step 4: Добавить _load_coord_jumps**

```python
def _load_coord_jumps(db: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """Точки где implied_speed между соседними GPS-точками > 300 км/ч."""
    rows = rows_to_dicts(db.execute(
        """
        SELECT
            p."vehicle_id"          AS vehicle_plate,
            CAST(tp."latitude"  AS DOUBLE) AS lat,
            CAST(tp."longitude" AS DOUBLE) AS lon,
            CAST(tp."timestamp" AS VARCHAR) AS ts,
            CAST(tp."speed_kmh" AS DOUBLE) AS speed_kmh
        FROM "navigation__track_points" tp
        JOIN "navigation__track_periods" p
          ON tp."public_unit_id" = p."public_unit_id"
         AND tp."date"           = p."date"
         AND tp."period_index"   = p."period_index"
        WHERE tp."latitude"  IS NOT NULL
          AND tp."longitude" IS NOT NULL
          AND (tp."latitude" != 0 OR tp."longitude" != 0)
        ORDER BY p."vehicle_id", tp."date", tp."timestamp"
        """
    ))

    result = []
    # Группируем по ТС+дате, ищем прыжки между соседними точками.
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        key = (str(r["vehicle_plate"]), str(r["ts"])[:10])
        groups[key].append(r)

    for pts in groups.values():
        for i in range(1, len(pts)):
            prev, curr = pts[i - 1], pts[i]
            prev_ts = _parse_ts(str(prev["ts"]))
            curr_ts = _parse_ts(str(curr["ts"]))
            if prev_ts is None or curr_ts is None:
                continue
            dt_sec = (curr_ts - prev_ts).total_seconds()
            if dt_sec <= 0:
                continue
            dist_m = _haversine_m(
                float(prev["lat"]), float(prev["lon"]),
                float(curr["lat"]), float(curr["lon"]),
            )
            implied_kmh = (dist_m / dt_sec) * 3.6
            if implied_kmh > _COORD_JUMP_THRESHOLD:
                result.append({
                    "vehicle_plate": str(curr["vehicle_plate"]),
                    "lat": float(curr["lat"]),
                    "lon": float(curr["lon"]),
                    "ts": str(curr["ts"]),
                    "speed_kmh": implied_kmh,
                    "anomaly_type": AnomalyType.coord_jump,
                    "duration_sec": 0,
                    "odometer_km": 0.0,
                    "unit_id": None,
                    "date": str(curr["ts"])[:10],
                    "period_index": None,
                })
    return result
```

- [ ] **Step 5: Добавить _build_possible_route**

```python
def _build_possible_route(
    db: duckdb.DuckDBPyConnection,
    unit_id: str,
    date: str,
    period_index: int,
) -> list[list[float]]:
    """Пунктир возможного маршрута: до 10 точек из period-1 + до 10 из period+1."""
    prev_rows = rows_to_dicts(db.execute(
        """
        SELECT CAST("latitude" AS DOUBLE) AS lat, CAST("longitude" AS DOUBLE) AS lon
        FROM "navigation__track_points"
        WHERE "public_unit_id" = ?
          AND "date" = ?
          AND "period_index" = ?
          AND "latitude" IS NOT NULL AND "longitude" IS NOT NULL
        ORDER BY "timestamp" DESC LIMIT 10
        """,
        [unit_id, date, period_index - 1],
    ))
    next_rows = rows_to_dicts(db.execute(
        """
        SELECT CAST("latitude" AS DOUBLE) AS lat, CAST("longitude" AS DOUBLE) AS lon
        FROM "navigation__track_points"
        WHERE "public_unit_id" = ?
          AND "date" = ?
          AND "period_index" = ?
          AND "latitude" IS NOT NULL AND "longitude" IS NOT NULL
        ORDER BY "timestamp" ASC LIMIT 10
        """,
        [unit_id, date, period_index + 1],
    ))
    # prev — в обратном порядке → хронологический
    route = (
        [[float(r["lat"]), float(r["lon"])] for r in reversed(prev_rows)]
        + [[float(r["lat"]), float(r["lon"])] for r in next_rows]
    )
    return [p for p in route if p[0] != 0.0 or p[1] != 0.0]
```

- [ ] **Step 6: Добавить _score_zone и detect_anomalies**

```python
def _score_zone(cluster_pts: list[dict[str, Any]]) -> int:
    """Confidence score кластера аномалий. Выше = больше похоже на РЭБ."""
    score = 0
    plates = {p["vehicle_plate"] for p in cluster_pts}
    types = {p["anomaly_type"] for p in cluster_pts}
    dates = {str(p.get("date") or p["ts"][:10]) for p in cluster_pts if p.get("ts")}
    speeds = [p["speed_kmh"] for p in cluster_pts if p.get("speed_kmh") is not None]
    durations = [p.get("duration_sec", 0) for p in cluster_pts]
    odomers = [p.get("odometer_km", 0.0) for p in cluster_pts]

    # Мультиплатформенный признак — самый сильный сигнал РЭБ.
    if len(plates) >= 2:
        # Проверяем что хотя бы 2 ТС в ±30 мин друг от друга.
        tss = sorted(
            filter(None, [_parse_ts(p["ts"]) for p in cluster_pts])
        )
        multi_time = any(
            (tss[j] - tss[i]).total_seconds() <= 1800
            for i in range(len(tss))
            for j in range(i + 1, len(tss))
            if tss[j] != tss[i]
        ) if len(tss) >= 2 else False
        if multi_time:
            score += 40

    if AnomalyType.coord_jump in types:
        score += 20

    if any(o > 0 for o in odomers):
        score += 20  # одометр растёт при gap → ТС двигалось без GPS

    if speeds and max(speeds) > 200:
        score += 15

    if len(dates) >= 2:
        score += 10  # повторяется в разные дни

    if any(d > 300 for d in durations):
        score += 10  # длинный разрыв

    # Штрафы за признаки не-РЭБ.
    if len(plates) == 1 and AnomalyType.gap not in types:
        score -= 25  # одно ТС, только скачки скорости

    gap_durations = [d for d, p in zip(durations, cluster_pts) if p["anomaly_type"] == AnomalyType.gap]
    if gap_durations and all(d < 30 for d in gap_durations):
        score -= 15  # все разрывы короткие (тоннель/здание)

    spike_only = types == {AnomalyType.speed_spike}
    if spike_only and len(cluster_pts) == 1:
        score -= 10

    return score


def detect_anomalies(db: duckdb.DuckDBPyConnection) -> list[RebAnomalyZone]:
    """Детектирует РЭБ-зоны. Возвращает только score >= 20."""
    all_pts: list[dict[str, Any]] = (
        _load_gap_periods(db)
        + _load_speed_spikes(db)
        + _load_coord_jumps(db)
    )
    if not all_pts:
        return []

    # Стабильная сортировка перед DBSCAN.
    all_pts = sorted(all_pts, key=lambda p: (float(p["lat"]), float(p["lon"])))

    coords_rad = np.array([
        [math.radians(float(p["lat"])), math.radians(float(p["lon"]))]
        for p in all_pts
    ])
    labels = DBSCAN(
        eps=_EPS_RAD, min_samples=_MIN_SAMPLES, metric="haversine", algorithm="ball_tree"
    ).fit_predict(coords_rad)

    clusters: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for pt, lbl in zip(all_pts, labels):
        if lbl != -1:
            clusters[lbl].append(pt)

    zones: list[RebAnomalyZone] = []
    for label in sorted(clusters):
        cluster_pts = clusters[label]
        confidence = _score_zone(cluster_pts)
        if confidence < 20:
            continue

        lats = [float(p["lat"]) for p in cluster_pts]
        lons = [float(p["lon"]) for p in cluster_pts]
        centroid_lat = sum(lats) / len(lats)
        centroid_lon = sum(lons) / len(lons)
        radius_m = max(
            _haversine_m(centroid_lat, centroid_lon, la, lo)
            for la, lo in zip(lats, lons)
        )
        radius_m = max(radius_m, 300.0)

        # VehicleAnomaly: одна запись на (plate) в кластере — берём наихудшую аномалию.
        by_plate: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for pt in cluster_pts:
            by_plate[pt["vehicle_plate"]].append(pt)

        vehicle_anomalies: list[VehicleAnomaly] = []
        for plate, pts in sorted(by_plate.items()):
            best = max(pts, key=lambda p: _ANOMALY_PRIORITY.get(p["anomaly_type"], 0))
            speeds = [p["speed_kmh"] for p in pts if p.get("speed_kmh") is not None]
            ts_list = sorted(filter(None, [_parse_ts(p["ts"]) for p in pts]))
            possible_route: list[list[float]] = []
            if best["anomaly_type"] == AnomalyType.gap and best.get("unit_id") and best.get("date"):
                possible_route = _build_possible_route(
                    db,
                    str(best["unit_id"]),
                    str(best["date"]),
                    int(best["period_index"]),
                )
            vehicle_anomalies.append(VehicleAnomaly(
                vehicle_plate=plate,
                anomaly_type=best["anomaly_type"],
                max_speed_kmh=max(speeds) if speeds else None,
                lat=float(best["lat"]),
                lon=float(best["lon"]),
                ts_start=str(ts_list[0].isoformat() if ts_list else best["ts"]),
                ts_end=str(ts_list[-1].isoformat()) if len(ts_list) > 1 else None,
                possible_route=possible_route,
                reb_link_id=plate,  # /api/reb/{plate} принимает vehicle_id (госномер)
            ))

        dates_in_zone = {str(p.get("date") or p["ts"][:10]) for p in cluster_pts if p.get("ts")}
        zones.append(RebAnomalyZone(
            zone_id=f"reb_anomaly_{label}",
            centroid=[round(centroid_lat, 6), round(centroid_lon, 6)],
            radius_m=round(radius_m, 1),
            confidence=confidence,
            confidence_label="reb" if confidence >= 40 else "suspicious",
            vehicles=vehicle_anomalies,
            event_count=len(cluster_pts),
            date_count=len(dates_in_zone),
        ))

    return sorted(zones, key=lambda z: z.zone_id)
```

- [ ] **Step 7: Проверить синтаксис сервиса**

```bash
cd /Users/dimausac/projects/skai_7 && python -c "from api.services import reb_anomaly_service; print('ok')"
```

Ожидаемый вывод: `ok`

- [ ] **Step 8: Commit**

```bash
git add api/services/reb_anomaly_service.py
git commit -m "feat: reb_anomaly_service — detect gap/speed_spike/coord_jump anomalies"
```

---

## Task 3: Backend unit-тесты сервиса

**Files:**
- Create: `api/tests/test_reb_anomaly_service.py`

**Interfaces:**
- Consumes: `detect_anomalies`, `_score_zone` из `api.services.reb_anomaly_service`; `AnomalyType` из `api.domain.entities`

- [ ] **Step 1: Написать тесты scoring**

```python
"""Тесты детекции РЭБ-аномалий (reb_anomaly_service).

Юнит-тесты _score_zone: не требуют DuckDB.
Интеграционный тест detect_anomalies: требует data/skai.duckdb (пропускается без файла).
"""

from __future__ import annotations

import pytest

from api.domain.entities import AnomalyType
from api.services.reb_anomaly_service import _score_zone


def _gap_pt(plate: str, ts: str, duration: int = 400, odometer: float = 5.0) -> dict:
    return {
        "vehicle_plate": plate,
        "lat": 50.0,
        "lon": 35.0,
        "ts": ts,
        "anomaly_type": AnomalyType.gap,
        "speed_kmh": None,
        "duration_sec": duration,
        "odometer_km": odometer,
        "date": ts[:10],
        "unit_id": "test-unit",
        "period_index": 5,
    }


def _spike_pt(plate: str, ts: str, speed: float = 250.0) -> dict:
    return {
        "vehicle_plate": plate,
        "lat": 50.0,
        "lon": 35.0,
        "ts": ts,
        "anomaly_type": AnomalyType.speed_spike,
        "speed_kmh": speed,
        "duration_sec": 0,
        "odometer_km": 0.0,
        "date": ts[:10],
        "unit_id": None,
        "period_index": None,
    }


def _jump_pt(plate: str, ts: str, speed: float = 450.0) -> dict:
    return {
        "vehicle_plate": plate,
        "lat": 50.0,
        "lon": 35.0,
        "ts": ts,
        "anomaly_type": AnomalyType.coord_jump,
        "speed_kmh": speed,
        "duration_sec": 0,
        "odometer_km": 0.0,
        "date": ts[:10],
        "unit_id": None,
        "period_index": None,
    }


class TestScoreZone:
    def test_multi_vehicle_gap_gets_high_score(self) -> None:
        pts = [
            _gap_pt("А001АА", "2026-05-07T10:00:00+00:00"),
            _gap_pt("Б002ББ", "2026-05-07T10:05:00+00:00"),
        ]
        score = _score_zone(pts)
        assert score >= 40, f"Ожидали score>=40 для 2 ТС с gap, получили {score}"

    def test_single_vehicle_speed_spike_only_gets_low_score(self) -> None:
        pts = [_spike_pt("А001АА", "2026-05-07T10:00:00+00:00")]
        score = _score_zone(pts)
        assert score < 20, f"Одиночный spike без gap не должен быть РЭБ-зоной, score={score}"

    def test_coord_jump_adds_score(self) -> None:
        pts = [
            _gap_pt("А001АА", "2026-05-07T10:00:00+00:00"),
            _jump_pt("А001АА", "2026-05-07T10:01:00+00:00"),
        ]
        score_with_jump = _score_zone(pts)
        score_without = _score_zone([_gap_pt("А001АА", "2026-05-07T10:00:00+00:00")])
        assert score_with_jump > score_without

    def test_short_gap_penalized(self) -> None:
        pts = [_gap_pt("А001АА", "2026-05-07T10:00:00+00:00", duration=20, odometer=0.0)]
        score = _score_zone(pts)
        # Штраф -15 за короткий gap (<30с) + -25 за одно ТС без gap типа? 
        # Нет: тип gap есть, но штраф за короткий gap применяется.
        score_long = _score_zone([_gap_pt("А001АА", "2026-05-07T10:00:00+00:00", duration=400)])
        assert score < score_long

    def test_odometer_positive_adds_score(self) -> None:
        pts_with_odo = [_gap_pt("А001АА", "2026-05-07T10:00:00+00:00", odometer=5.0)]
        pts_no_odo = [_gap_pt("А001АА", "2026-05-07T10:00:00+00:00", odometer=0.0)]
        assert _score_zone(pts_with_odo) > _score_zone(pts_no_odo)

    def test_multi_date_adds_score(self) -> None:
        pts = [
            _gap_pt("А001АА", "2026-05-06T10:00:00+00:00"),
            _gap_pt("А001АА", "2026-05-07T10:00:00+00:00"),
        ]
        score = _score_zone(pts)
        single_date = _score_zone([_gap_pt("А001АА", "2026-05-06T10:00:00+00:00")])
        assert score > single_date
```

- [ ] **Step 2: Написать интеграционный тест**

```python
@pytest.fixture
def real_db():
    """Реальная DuckDB — пропускается если файл не собран."""
    import os
    import duckdb

    db_path = "data/skai.duckdb"
    if not os.path.exists(db_path):
        pytest.skip("data/skai.duckdb не найдена — запустите make db")
    conn = duckdb.connect(db_path, read_only=True)
    yield conn
    conn.close()


class TestDetectAnomalies:
    def test_returns_list(self, real_db) -> None:
        from api.services.reb_anomaly_service import detect_anomalies
        zones = detect_anomalies(real_db)
        assert isinstance(zones, list)

    def test_zones_have_valid_schema(self, real_db) -> None:
        from api.services.reb_anomaly_service import detect_anomalies
        from api.domain.entities import RebAnomalyZone
        zones = detect_anomalies(real_db)
        for z in zones:
            assert isinstance(z, RebAnomalyZone)
            assert z.confidence >= 20
            assert z.confidence_label in ("reb", "suspicious")
            assert len(z.centroid) == 2
            assert z.radius_m > 0
            assert len(z.vehicles) >= 1

    def test_all_zones_above_noise_threshold(self, real_db) -> None:
        from api.services.reb_anomaly_service import detect_anomalies
        zones = detect_anomalies(real_db)
        for z in zones:
            assert z.confidence >= 20, f"Зона {z.zone_id} прошла с score {z.confidence} < 20"
```

- [ ] **Step 3: Запустить unit-тесты**

```bash
cd /Users/dimausac/projects/skai_7 && pytest api/tests/test_reb_anomaly_service.py -v
```

Ожидаемый вывод: все тесты `PASSED` (интеграционный может быть `SKIPPED` если `make db` не запускался).

- [ ] **Step 4: Commit**

```bash
git add api/tests/test_reb_anomaly_service.py
git commit -m "test: reb_anomaly_service — scoring unit tests + integration smoke"
```

---

## Task 4: API endpoint + тест

**Files:**
- Modify: `api/routers/reb.py` — добавить endpoint
- Create: `api/tests/test_reb_anomaly_api.py`

**Interfaces:**
- Consumes: `detect_anomalies` из `api.services.reb_anomaly_service`; `RebAnomalyZone` из `api.domain.entities`
- Produces: `GET /api/reb/anomalies → list[RebAnomalyZone]`

- [ ] **Step 1: Добавить endpoint в api/routers/reb.py**

Открыть `api/routers/reb.py`. Добавить импорт и endpoint ПЕРЕД существующим `get_reb`:

```python
from api.services import reb_anomaly_service
```

(добавить рядом с существующим `from api.services import reb_service`)

Затем добавить новый endpoint:

```python
@router.get("/reb/anomalies", response_model=list[RebAnomalyZone])
def get_reb_anomalies(db: DbDep) -> list[RebAnomalyZone]:
    """Детектированные РЭБ-зоны с confidence score и per-vehicle аномалиями."""
    return reb_anomaly_service.detect_anomalies(db)
```

Добавить `RebAnomalyZone` к импорту entities в том же файле:

```python
from api.domain.entities import RebAnomalyZone, RebRecovery
```

**Важно:** endpoint `/reb/anomalies` нужно зарегистрировать ПЕРЕД `/reb/{id:path}`, иначе FastAPI будет перехватывать `anomalies` как значение `id`. Убедиться что `get_reb_anomalies` объявлен выше `get_reb` в файле.

- [ ] **Step 2: Проверить что сервер стартует**

```bash
cd /Users/dimausac/projects/skai_7 && python -c "from api.routers.reb import router; print('ok')"
```

Ожидаемый вывод: `ok`

- [ ] **Step 3: Написать API-тест**

```python
"""API-тест GET /api/reb/anomalies."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.domain.entities import RebAnomalyZone


class TestRebAnomaliesEndpoint:
    def test_returns_200_with_list(self, client: TestClient) -> None:
        r = client.get("/api/reb/anomalies")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_schema_valid_when_zones_present(self, client: TestClient) -> None:
        r = client.get("/api/reb/anomalies")
        assert r.status_code == 200
        for item in r.json():
            zone = RebAnomalyZone(**item)
            assert zone.confidence >= 20
            assert zone.confidence_label in ("reb", "suspicious")
            assert len(zone.centroid) == 2
            assert zone.radius_m > 0
            assert len(zone.vehicles) >= 1
            for v in zone.vehicles:
                assert v.vehicle_plate
                assert v.anomaly_type in ("gap", "speed_spike", "coord_jump")
                assert isinstance(v.possible_route, list)

    def test_endpoint_before_reb_id(self, client: TestClient) -> None:
        # Убедиться что /anomalies не перехватывается роутом /{id:path}.
        r = client.get("/api/reb/anomalies")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
```

- [ ] **Step 4: Запустить тесты**

```bash
cd /Users/dimausac/projects/skai_7 && pytest api/tests/test_reb_anomaly_api.py -v
```

Ожидаемый вывод: `PASSED` (все тесты).

- [ ] **Step 5: Запустить полный backend test suite**

```bash
cd /Users/dimausac/projects/skai_7 && pytest api/tests/ -q
```

Ожидаемый вывод: все тесты зелёные, нет регрессий.

- [ ] **Step 6: Commit**

```bash
git add api/routers/reb.py api/tests/test_reb_anomaly_api.py
git commit -m "feat: GET /api/reb/anomalies endpoint + API tests"
```

---

## Task 5: Frontend типы и клиент

**Files:**
- Modify: `web/src/api/types.ts`
- Modify: `web/src/api/client.ts`

**Interfaces:**
- Produces: `AnomalyType`, `RebVehicleAnomaly`, `RebAnomalyZone` (TS-типы); `getRebAnomalies(): Promise<RebAnomalyZone[]>`

- [ ] **Step 1: Добавить типы в types.ts**

Открыть `web/src/api/types.ts`, найти секцию с `RebRecovery` и добавить ПОСЛЕ неё:

```typescript
// ── REB Anomaly Zones ─────────────────────────────────────────────────────

export type AnomalyType = 'gap' | 'speed_spike' | 'coord_jump'

export interface RebVehicleAnomaly {
  vehicle_plate: string
  anomaly_type: AnomalyType
  max_speed_kmh: number | null
  lat: number
  lon: number
  ts_start: string
  ts_end: string | null
  possible_route: [number, number][]
  reb_link_id: string | null
}

export interface RebAnomalyZone {
  zone_id: string
  centroid: [number, number]
  radius_m: number
  confidence: number
  confidence_label: 'reb' | 'suspicious'
  vehicles: RebVehicleAnomaly[]
  event_count: number
  date_count: number
}
```

- [ ] **Step 2: Добавить getRebAnomalies в client.ts**

Найти `export function getReb(id: string)` в `web/src/api/client.ts`. Добавить ПОСЛЕ функции `getReb`:

```typescript
export function getRebAnomalies(): Promise<import('./types').RebAnomalyZone[]> {
  if (USE_FIXTURES) return Promise.resolve([])
  return request<import('./types').RebAnomalyZone[]>('/reb/anomalies')
}
```

Добавить импорт типа в начало файла (рядом с другими type-импортами):

```typescript
import type { RebAnomalyZone } from './types'
```

И переписать сигнатуру без inline-импорта:

```typescript
export function getRebAnomalies(): Promise<RebAnomalyZone[]> {
  if (USE_FIXTURES) return Promise.resolve([])
  return request<RebAnomalyZone[]>('/reb/anomalies')
}
```

- [ ] **Step 3: Typecheck**

```bash
cd /Users/dimausac/projects/skai_7/web && npx tsc --noEmit
```

Ожидаемый вывод: 0 ошибок.

- [ ] **Step 4: Commit**

```bash
git add web/src/api/types.ts web/src/api/client.ts
git commit -m "feat: RebAnomalyZone TS types + getRebAnomalies() client method"
```

---

## Task 6: RebAnomalyLayer компонент

**Files:**
- Create: `web/src/components/reb/RebAnomalyLayer.tsx`

**Interfaces:**
- Consumes: `RebAnomalyZone`, `RebVehicleAnomaly` из `@/api/types`; `useMap` из `react-leaflet`; `L` из `leaflet`
- Produces: React компонент `RebAnomalyLayer({ zones: RebAnomalyZone[] }): null`

- [ ] **Step 1: Создать файл**

```tsx
/**
 * RebAnomalyLayer — слой РЭБ-аномалий поверх MapView.
 *
 * Рисует:
 *   - Circle на каждую зону (цвет по confidence_label)
 *   - Marker на каждое ТС в зоне (иконка RadioTower SVG)
 *   - Dashed Polyline (possible_route) для gap-аномалий
 *   - Popup по клику на маркер: госномер, тип, скорость, confidence, время, кнопка РЭБ
 *
 * Использует императивный Leaflet (как RiskHeatLayer.tsx) — useEffect + useRef + L.layerGroup.
 */

import { useEffect, useRef } from 'react'
import { useMap } from 'react-leaflet'
import * as L from 'leaflet'
import type { RebAnomalyZone, RebVehicleAnomaly } from '@/api/types'

const COLORS = {
  reb: { fill: '#dc2626', stroke: '#dc2626' },
  suspicious: { fill: '#ea580c', stroke: '#ea580c' },
} as const

const ANOMALY_LABEL: Record<string, string> = {
  gap: 'Потеря GPS',
  speed_spike: 'Скачок скорости',
  coord_jump: 'Прыжок координат',
}

function formatClock(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

function markerIcon(): L.DivIcon {
  return L.divIcon({
    className: '',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    html: `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M4.9 16.1C1 12.2 1 5.8 4.9 1.9"/>
      <path d="M7.8 4.7a6.14 6.14 0 0 0-.8 7.5"/>
      <circle cx="12" cy="9" r="2"/>
      <path d="M16.2 4.8c2 2 2.26 5.11.8 7.47"/>
      <path d="M19.1 1.9a11.93 11.93 0 0 1 0 16.97"/>
      <line x1="12" y1="9" x2="12" y2="22"/>
    </svg>`,
  })
}

function popupHtml(v: RebVehicleAnomaly, zone_confidence: number, confidence_label: string): string {
  const speed = v.max_speed_kmh != null ? `${Math.round(v.max_speed_kmh)} км/ч` : '—'
  const label = confidence_label === 'reb' ? 'РЭБ-зона' : 'Подозрительная аномалия'
  const time = formatClock(v.ts_start) + (v.ts_end ? ` – ${formatClock(v.ts_end)}` : '')
  const btn = v.reb_link_id
    ? `<a href="/reb/${encodeURIComponent(v.reb_link_id)}"
         style="display:inline-block;margin-top:8px;padding:4px 10px;border-radius:6px;
                background:#1e40af;color:#fff;font-size:12px;text-decoration:none;">
         Открыть РЭБ →
       </a>`
    : `<span style="display:inline-block;margin-top:8px;padding:4px 10px;border-radius:6px;
                    background:#e5e7eb;color:#6b7280;font-size:12px;">
         Нет данных РЭБ
       </span>`
  return `
    <div style="font-size:13px;line-height:1.6;min-width:180px;">
      <div style="font-weight:600;color:#0f172a;">${v.vehicle_plate}</div>
      <div style="color:#64748b;">Тип: ${ANOMALY_LABEL[v.anomaly_type] ?? v.anomaly_type}</div>
      <div style="color:#64748b;">Макс. скорость: ${speed}</div>
      <div style="color:#64748b;">Confidence: ${zone_confidence} (${label})</div>
      <div style="color:#64748b;">Время: ${time}</div>
      ${btn}
    </div>
  `
}

export interface RebAnomalyLayerProps {
  zones: RebAnomalyZone[]
}

export function RebAnomalyLayer({ zones }: RebAnomalyLayerProps) {
  const map = useMap()
  const layerRef = useRef<L.LayerGroup | null>(null)

  useEffect(() => {
    if (!layerRef.current) {
      layerRef.current = L.layerGroup().addTo(map)
    }
    const layer = layerRef.current
    layer.clearLayers()

    for (const zone of zones) {
      const [clat, clon] = zone.centroid
      if (!Number.isFinite(clat) || !Number.isFinite(clon)) continue
      const color = COLORS[zone.confidence_label] ?? COLORS.suspicious

      // Круг зоны.
      L.circle([clat, clon], {
        radius: zone.radius_m > 0 ? zone.radius_m : 300,
        color: color.stroke,
        fillColor: color.fill,
        fillOpacity: zone.confidence_label === 'reb' ? 0.15 : 0.10,
        opacity: zone.confidence_label === 'reb' ? 0.6 : 0.5,
        weight: 1.5,
      })
        .bindTooltip(
          `РЭБ-зона · ${zone.confidence_label === 'reb' ? 'подтверждена' : 'подозрительная'} · ${zone.vehicles.length} ТС · confidence ${zone.confidence}`,
          { sticky: true, className: 'text-xs' },
        )
        .addTo(layer)

      // Маркеры и пунктиры ТС.
      for (const v of zone.vehicles) {
        if (!Number.isFinite(v.lat) || !Number.isFinite(v.lon)) continue

        L.marker([v.lat, v.lon], { icon: markerIcon() })
          .bindPopup(popupHtml(v, zone.confidence, zone.confidence_label), {
            maxWidth: 260,
            className: 'reb-popup',
          })
          .addTo(layer)

        if (v.possible_route.length >= 2) {
          const positions = v.possible_route.filter(
            ([la, lo]) => Number.isFinite(la) && Number.isFinite(lo),
          ) as [number, number][]
          if (positions.length >= 2) {
            L.polyline(positions, {
              color: '#dc2626',
              weight: 2,
              opacity: 0.7,
              dashArray: '6 8',
            }).addTo(layer)
          }
        }
      }
    }

    return () => {
      layer.clearLayers()
    }
  }, [map, zones])

  useEffect(() => {
    return () => {
      layerRef.current?.remove()
      layerRef.current = null
    }
  }, [])

  return null
}
```

- [ ] **Step 2: Typecheck**

```bash
cd /Users/dimausac/projects/skai_7/web && npx tsc --noEmit
```

Ожидаемый вывод: 0 ошибок.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/reb/RebAnomalyLayer.tsx
git commit -m "feat: RebAnomalyLayer — circles, markers, dashed routes, popup"
```

---

## Task 7: Frontend тест RebAnomalyLayer

**Files:**
- Create: `web/src/components/reb/RebAnomalyLayer.test.tsx`

**Interfaces:**
- Consumes: `RebAnomalyLayer` из `./RebAnomalyLayer`; `RebAnomalyZone` из `@/api/types`

- [ ] **Step 1: Написать тест**

Паттерн мока — тот же что в `RiskHeatLayer.test.tsx` (vi.mock для leaflet и react-leaflet):

```tsx
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import { RebAnomalyLayer } from './RebAnomalyLayer'
import type { RebAnomalyZone } from '@/api/types'

// ── Моки Leaflet ──────────────────────────────────────────────────────────
const popupHandle = { on: vi.fn() }
const markerHandle = { bindPopup: vi.fn(() => markerHandle), addTo: vi.fn(() => markerHandle) }
const polylineHandle = { addTo: vi.fn() }
const circleHandle = { bindTooltip: vi.fn(() => circleHandle), addTo: vi.fn() }
const layerGroupHandle = { addTo: vi.fn(() => layerGroupHandle), clearLayers: vi.fn(), remove: vi.fn() }

const circle = vi.fn(() => circleHandle)
const marker = vi.fn(() => markerHandle)
const polyline = vi.fn(() => polylineHandle)
const layerGroup = vi.fn(() => layerGroupHandle)
const divIcon = vi.fn(() => ({}))

vi.mock('leaflet', () => ({
  default: { circle, marker, polyline, layerGroup, divIcon },
  circle, marker, polyline, layerGroup, divIcon,
}))

vi.mock('react-leaflet', () => ({
  useMap: () => ({ on: vi.fn(), off: vi.fn() }),
}))

// ── Фикстуры ──────────────────────────────────────────────────────────────
const ZONE_REB: RebAnomalyZone = {
  zone_id: 'reb_anomaly_0',
  centroid: [50.0, 35.0],
  radius_m: 5000,
  confidence: 75,
  confidence_label: 'reb',
  vehicles: [
    {
      vehicle_plate: 'А001АА777',
      anomaly_type: 'gap',
      max_speed_kmh: null,
      lat: 50.01,
      lon: 35.01,
      ts_start: '2026-05-07T10:00:00+00:00',
      ts_end: '2026-05-07T10:15:00+00:00',
      possible_route: [[50.0, 35.0], [50.01, 35.01]],
      reb_link_id: 'А001АА777',
    },
    {
      vehicle_plate: 'Б002ББ777',
      anomaly_type: 'speed_spike',
      max_speed_kmh: 247,
      lat: 50.02,
      lon: 35.02,
      ts_start: '2026-05-07T10:05:00+00:00',
      ts_end: null,
      possible_route: [],
      reb_link_id: 'Б002ББ777',
    },
  ],
  event_count: 5,
  date_count: 2,
}

const ZONE_SUSPICIOUS: RebAnomalyZone = {
  ...ZONE_REB,
  zone_id: 'reb_anomaly_1',
  confidence: 30,
  confidence_label: 'suspicious',
}

describe('RebAnomalyLayer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    layerGroup.mockReturnValue(layerGroupHandle)
    circle.mockReturnValue(circleHandle)
    marker.mockReturnValue(markerHandle)
    polyline.mockReturnValue(polylineHandle)
  })

  it('пустой список зон — рендерится без ошибок, clearLayers не вызывается с маркерами', () => {
    render(<RebAnomalyLayer zones={[]} />)
    expect(circle).not.toHaveBeenCalled()
    expect(marker).not.toHaveBeenCalled()
  })

  it('РЭБ-зона рисует circle + 2 marker + 1 polyline (у gap-ТС)', () => {
    render(<RebAnomalyLayer zones={[ZONE_REB]} />)
    expect(circle).toHaveBeenCalledTimes(1)
    expect(marker).toHaveBeenCalledTimes(2)
    // Только первое ТС имеет possible_route длиной 2 → 1 polyline.
    expect(polyline).toHaveBeenCalledTimes(1)
  })

  it('подозрительная зона тоже рисует circle', () => {
    render(<RebAnomalyLayer zones={[ZONE_SUSPICIOUS]} />)
    expect(circle).toHaveBeenCalledTimes(1)
  })

  it('marker.bindPopup вызывается для каждого ТС', () => {
    render(<RebAnomalyLayer zones={[ZONE_REB]} />)
    expect(markerHandle.bindPopup).toHaveBeenCalledTimes(2)
  })

  it('ТС без possible_route (пустой массив) не рисует polyline', () => {
    const zoneNoRoute: RebAnomalyZone = {
      ...ZONE_REB,
      vehicles: [{ ...ZONE_REB.vehicles[1], possible_route: [] }],
    }
    render(<RebAnomalyLayer zones={[zoneNoRoute]} />)
    expect(polyline).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Запустить тест**

```bash
cd /Users/dimausac/projects/skai_7/web && npx vitest run src/components/reb/RebAnomalyLayer.test.tsx
```

Ожидаемый вывод: все тесты `PASSED`.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/reb/RebAnomalyLayer.test.tsx
git commit -m "test: RebAnomalyLayer — render, markers, popups, polylines"
```

---

## Task 8: Интеграция в Monitor.tsx

**Files:**
- Modify: `web/src/pages/Monitor.tsx`

**Interfaces:**
- Consumes: `RebAnomalyLayer` из `@/components/reb/RebAnomalyLayer`; `getRebAnomalies` из `@/api/client`; `RebAnomalyZone` из `@/api/types`

- [ ] **Step 1: Добавить импорты в Monitor.tsx**

В начало `web/src/pages/Monitor.tsx` добавить после существующих импортов компонентов:

```typescript
import { RebAnomalyLayer } from '@/components/reb/RebAnomalyLayer'
import * as client from '@/api/client'  // уже есть, проверить
import type { RebAnomalyZone } from '@/api/types'
```

(если `import * as client` уже есть — не дублировать, только добавить `RebAnomalyLayer` и тип)

- [ ] **Step 2: Расширить LayerKey**

Найти строку:
```typescript
type LayerKey = 'heat' | 'incident' | 'reb'
```
Заменить на:
```typescript
type LayerKey = 'heat' | 'incident' | 'reb' | 'reb_anomaly'
```

- [ ] **Step 3: Добавить state для reb_anomaly**

Найти:
```typescript
const [layers, setLayers] = useState<Record<LayerKey, boolean>>({
  heat: false,
  incident: false,
  reb: false,
})
```
Заменить на:
```typescript
const [layers, setLayers] = useState<Record<LayerKey, boolean>>({
  heat: false,
  incident: false,
  reb: false,
  reb_anomaly: false,
})
```

- [ ] **Step 4: Добавить state для данных аномалий**

После строки `const [zonesError, setZonesError] = useState<string | null>(null)` добавить:

```typescript
const [rebAnomalyZones, setRebAnomalyZones] = useState<RebAnomalyZone[]>([])
const [rebAnomalyLoading, setRebAnomalyLoading] = useState(false)
```

- [ ] **Step 5: Добавить загрузку данных при включении слоя**

После существующего `useEffect` для загрузки зон (`loadZones`) добавить:

```typescript
const loadRebAnomalies = useCallback(() => {
  if (rebAnomalyZones.length > 0) return  // уже загружено
  let alive = true
  setRebAnomalyLoading(true)
  client
    .getRebAnomalies()
    .then((data) => { if (alive) setRebAnomalyZones(data) })
    .catch(() => { if (alive) setRebAnomalyZones([]) })
    .finally(() => { if (alive) setRebAnomalyLoading(false) })
  return () => { alive = false }
}, [rebAnomalyZones.length])

useEffect(() => {
  if (layers.reb_anomaly) loadRebAnomalies()
}, [layers.reb_anomaly, loadRebAnomalies])
```

- [ ] **Step 6: Добавить Chip тоггл**

Найти в JSX блок с `<Chip>` для слоёв (рядом с chips `heat`, `incident`, `reb`). Добавить после чипа `reb`:

```tsx
<Chip active={layers.reb_anomaly} onClick={() => toggleLayer('reb_anomaly')}>
  {rebAnomalyLoading ? <Loader2 className="h-3 w-3 animate-spin" aria-hidden /> : null}
  РЭБ-аномалии
</Chip>
```

- [ ] **Step 7: Добавить слой в MapView**

Найти в JSX блок с условным рендером `{layers.reb && ...}`. После него добавить:

```tsx
{layers.reb_anomaly && rebAnomalyZones.length > 0 && (
  <RebAnomalyLayer zones={rebAnomalyZones} />
)}
```

- [ ] **Step 8: Typecheck + lint**

```bash
cd /Users/dimausac/projects/skai_7/web && npx tsc --noEmit
```

Ожидаемый вывод: 0 ошибок.

- [ ] **Step 9: Запустить все frontend тесты**

```bash
cd /Users/dimausac/projects/skai_7/web && npx vitest run
```

Ожидаемый вывод: все тесты `PASSED`.

- [ ] **Step 10: Запустить все backend тесты**

```bash
cd /Users/dimausac/projects/skai_7 && pytest api/tests/ -q
```

Ожидаемый вывод: все тесты зелёные.

- [ ] **Step 11: Final commit**

```bash
git add web/src/pages/Monitor.tsx
git commit -m "feat: РЭБ-аномалии слой на карте монитора (Chip + RebAnomalyLayer)"
```

---

## Проверка интеграции вручную

После завершения всех задач:

1. Запустить backend: `uvicorn api.main:app --reload`
2. Запустить frontend: `cd web && npm run dev`
3. Открыть монитор → нажать «РЭБ-аномалии» в тулбаре
4. Ожидать: на карте появляются красные/оранжевые круги
5. Кликнуть на маркер ТС → попап с госномером, типом аномалии, скоростью, confidence, временем и кнопкой «Открыть РЭБ»
6. Кликнуть «Открыть РЭБ» → переход на `/reb/{plate}` с восстановлением трека
