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
from collections import defaultdict
from datetime import datetime
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


def _load_speed_spikes(db: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """GPS-точки с speed_kmh > 150 (нереальная скорость при РЭБ-подавлении)."""
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
        WHERE tp."speed_kmh" > ?
          AND tp."latitude"  IS NOT NULL
          AND tp."longitude" IS NOT NULL
        """,
        [_SPEED_SPIKE_THRESHOLD],
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
