"""Сервис зон риска (b19).

Кластеризует:
  - incident-зоны: DBSCAN по lat/lon из v_incidents (kind=incident)
  - РЭБ-зоны:      DBSCAN по lat/lon из navigation__track_points
                   для периодов period_type=3 (kind=reb)

Детерминизм гарантируется:
  - фиксированные eps/min_samples (нет random)
  - точки сортируются по (lat, lon) перед кластеризацией
  - зоны сортируются по zone_id
"""

from __future__ import annotations

import math
from collections import Counter
from datetime import datetime
from typing import Any

import duckdb
import numpy as np
from sklearn.cluster import DBSCAN

from api.domain.entities import RiskZone
from api.repositories import rows_to_dicts

# DBSCAN: eps в радианах (haversine), min_samples.
# eps ≈ 5 км / 6371 км ≈ 0.000785 рад
_EPS_RAD: float = 5_000 / 6_371_000
_MIN_SAMPLES: int = 2

_SEVERITY_SCORE: dict[str, float] = {
    "critical": 100.0,
    "high": 75.0,
    "medium": 50.0,
    "low": 25.0,
}


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Расстояние между двумя точками в метрах (формула Haversine)."""
    r = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _build_zones(points: list[dict[str, Any]], kind: str) -> list[RiskZone]:
    """Кластеризует список точек (lat/lon + meta) → list[RiskZone].

    points: каждый dict должен содержать 'lat', 'lon'.
    Для kind=incident дополнительно: 'alarm_code', 'risk_level', 'ts'.
    """
    if not points:
        return []

    # Стабильная сортировка для детерминизма перед передачей в DBSCAN.
    points = sorted(points, key=lambda p: (float(p["lat"]), float(p["lon"])))

    coords_rad = np.array(
        [[math.radians(float(p["lat"])), math.radians(float(p["lon"]))] for p in points]
    )

    db = DBSCAN(eps=_EPS_RAD, min_samples=_MIN_SAMPLES, metric="haversine", algorithm="ball_tree")
    labels = db.fit_predict(coords_rad)

    unique_labels = sorted(set(labels))
    zones: list[RiskZone] = []

    for label in unique_labels:
        if label == -1:
            continue  # шум

        mask = labels == label
        cluster_pts = [p for p, m in zip(points, mask) if m]

        lats = [float(p["lat"]) for p in cluster_pts]
        lons = [float(p["lon"]) for p in cluster_pts]
        centroid_lat = sum(lats) / len(lats)
        centroid_lon = sum(lons) / len(lons)

        # Радиус: максимальное расстояние от центроида.
        radius_m = max(
            _haversine_m(centroid_lat, centroid_lon, lat, lon)
            for lat, lon in zip(lats, lons)
        )
        radius_m = max(radius_m, 1.0)  # не ноль при единственной точке в кластере

        if kind == "incident":
            codes = [str(p.get("alarm_code", "UNKNOWN")) for p in cluster_pts]
            top_alarm_code = Counter(codes).most_common(1)[0][0]

            scores = [_SEVERITY_SCORE.get(str(p.get("risk_level", "low")), 25.0) for p in cluster_pts]
            avg_risk = sum(scores) / len(scores)

            hours = []
            for p in cluster_pts:
                try:
                    hours.append(datetime.fromisoformat(str(p["ts"])).hour)
                except (ValueError, KeyError):
                    pass
            peak_hour = Counter(hours).most_common(1)[0][0] if hours else 0
        else:
            # РЭБ-зона: нет alarm_code / risk_level — ставим sentinel-значения.
            top_alarm_code = "GPS_LOSS"
            avg_risk = 50.0
            hours = []
            for p in cluster_pts:
                try:
                    hours.append(datetime.fromisoformat(str(p["ts"])).hour)
                except (ValueError, KeyError):
                    pass
            peak_hour = Counter(hours).most_common(1)[0][0] if hours else 0

        zones.append(
            RiskZone(
                zone_id=f"{kind}_{label}",
                centroid=[round(centroid_lat, 6), round(centroid_lon, 6)],
                radius_m=round(radius_m, 1),
                alarm_count=len(cluster_pts),
                avg_risk=round(avg_risk, 2),
                top_alarm_code=top_alarm_code,
                peak_hour=peak_hour,
                kind=kind,
            )
        )

    return sorted(zones, key=lambda z: z.zone_id)


def _load_incident_points(db: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    result = db.execute(
        """
        SELECT "lat", "lon", "alarm_code", "risk_level", "ts"
        FROM "v_incidents"
        WHERE "lat" IS NOT NULL
          AND "lon" IS NOT NULL
        ORDER BY "lat", "lon"
        """
    )
    return rows_to_dicts(result)


def _load_reb_points(db: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """Точки GPS-разрывов (period_type=3) из navigation__track_points.

    navigation__track_periods даёт список периодов, navigation__track_points —
    фактические координаты. Связь: public_unit_id + date + period_index.
    Поле timestamp из track_points используется как ts для peak_hour.
    """
    result = db.execute(
        """
        SELECT
            CAST(tp."latitude"  AS DOUBLE) AS "lat",
            CAST(tp."longitude" AS DOUBLE) AS "lon",
            CAST(tp."timestamp" AS VARCHAR) AS "ts"
        FROM "navigation__track_periods" p
        JOIN "navigation__track_points" tp
          ON  tp."public_unit_id" = p."public_unit_id"
          AND tp."date"           = p."date"
          AND tp."period_index"   = p."period_index"
        WHERE p."period_type" = 3
          AND tp."latitude"  IS NOT NULL
          AND tp."longitude" IS NOT NULL
        ORDER BY tp."latitude", tp."longitude"
        """
    )
    rows = rows_to_dicts(result)
    # Фильтруем нулевые координаты (артефакты GPS-потери).
    return [r for r in rows if float(r["lat"]) != 0.0 or float(r["lon"]) != 0.0]


def compute_zones(
    db: duckdb.DuckDBPyConnection,
    kind: str | None = None,
    hour: int | None = None,
) -> list[RiskZone]:
    """Вычисляет зоны риска. Фильтрация по kind и peak_hour на выходе."""
    zones: list[RiskZone] = []

    if kind is None or kind == "incident":
        pts = _load_incident_points(db)
        zones.extend(_build_zones(pts, "incident"))

    if kind is None or kind == "reb":
        pts = _load_reb_points(db)
        zones.extend(_build_zones(pts, "reb"))

    if hour is not None:
        zones = [z for z in zones if z.peak_hour == hour]

    return sorted(zones, key=lambda z: z.zone_id)
