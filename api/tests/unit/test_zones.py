"""Unit-покрытие geozone-risk (b19) — §8.1/§8.4, идея #14.

`zones_service.compute_zones` кластеризует incident-точки (из v_incidents)
и РЭБ-точки (navigation__track_points period_type=3) через DBSCAN без сети.
Тестируем детерминизм, оба kind, фильтры и пустой кейс.
"""

from __future__ import annotations

from api.services import zones_service


# ---------------------------------------------------------------------------
# Helpers — строители тестовой БД.
# ---------------------------------------------------------------------------


def _load_incidents(mem_db, load_rows) -> None:
    """v_incidents: два близких инцидента → кластер incident (ts=22:xx)."""
    load_rows(
        mem_db,
        "v_incidents",
        [
            {
                "lat": 55.100,
                "lon": 37.100,
                "alarm_code": "DMS_DROWSY",
                "risk_level": "high",
                "ts": "2026-06-01T22:00:00+00:00",
            },
            {
                "lat": 55.103,
                "lon": 37.103,
                "alarm_code": "DMS_DROWSY",
                "risk_level": "high",
                "ts": "2026-06-01T22:30:00+00:00",
            },
        ],
    )


def _load_reb(mem_db, load_rows) -> None:
    """navigation tables: два period_type=3 → кластер reb (ts=14:xx)."""
    load_rows(
        mem_db,
        "navigation__track_periods",
        [
            {
                "vehicle_id": "PLATE1",
                "public_unit_id": "uid1",
                "date": "2026-06-01",
                "period_index": 1,
                "period_type": 3,
                "period_duration": "00:05:00",
            },
            {
                "vehicle_id": "PLATE2",
                "public_unit_id": "uid2",
                "date": "2026-06-01",
                "period_index": 1,
                "period_type": 3,
                "period_duration": "00:05:00",
            },
        ],
    )
    load_rows(
        mem_db,
        "navigation__track_points",
        [
            {
                "public_unit_id": "uid1",
                "date": "2026-06-01",
                "period_index": 1,
                "timestamp": "2026-06-01T14:00:00+00:00",
                "latitude": 50.100,
                "longitude": 36.100,
            },
            {
                "public_unit_id": "uid2",
                "date": "2026-06-01",
                "period_index": 1,
                "timestamp": "2026-06-01T14:30:00+00:00",
                "latitude": 50.103,
                "longitude": 36.103,
            },
        ],
    )


def _setup_full(mem_db, load_rows) -> None:
    _load_incidents(mem_db, load_rows)
    _load_reb(mem_db, load_rows)


# ---------------------------------------------------------------------------
# Детерминизм.
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_zone_ids_stable(self, mem_db, load_rows) -> None:
        _setup_full(mem_db, load_rows)
        ids1 = [z.zone_id for z in zones_service.compute_zones(mem_db)]
        ids2 = [z.zone_id for z in zones_service.compute_zones(mem_db)]
        assert ids1 == ids2

    def test_centroids_stable(self, mem_db, load_rows) -> None:
        _setup_full(mem_db, load_rows)
        c1 = [z.centroid for z in zones_service.compute_zones(mem_db)]
        c2 = [z.centroid for z in zones_service.compute_zones(mem_db)]
        assert c1 == c2


# ---------------------------------------------------------------------------
# Оба kind + контрактные границы полей.
# ---------------------------------------------------------------------------


class TestBothKinds:
    def test_incident_and_reb_present(self, mem_db, load_rows) -> None:
        _setup_full(mem_db, load_rows)
        kinds = {z.kind for z in zones_service.compute_zones(mem_db)}
        assert kinds == {"incident", "reb"}

    def test_avg_risk_in_range(self, mem_db, load_rows) -> None:
        _setup_full(mem_db, load_rows)
        for z in zones_service.compute_zones(mem_db):
            assert 0 <= z.avg_risk <= 100, f"{z.zone_id}: avg_risk={z.avg_risk}"

    def test_radius_m_positive(self, mem_db, load_rows) -> None:
        _setup_full(mem_db, load_rows)
        for z in zones_service.compute_zones(mem_db):
            assert z.radius_m > 0, f"{z.zone_id}: radius_m={z.radius_m}"

    def test_peak_hour_valid(self, mem_db, load_rows) -> None:
        _setup_full(mem_db, load_rows)
        for z in zones_service.compute_zones(mem_db):
            assert 0 <= z.peak_hour <= 23, f"{z.zone_id}: peak_hour={z.peak_hour}"


# ---------------------------------------------------------------------------
# Фильтры.
# ---------------------------------------------------------------------------


class TestFilters:
    def test_kind_reb_returns_only_reb(self, mem_db, load_rows) -> None:
        _setup_full(mem_db, load_rows)
        zones = zones_service.compute_zones(mem_db, kind="reb")
        assert zones and all(z.kind == "reb" for z in zones)

    def test_kind_incident_returns_only_incident(self, mem_db, load_rows) -> None:
        _setup_full(mem_db, load_rows)
        zones = zones_service.compute_zones(mem_db, kind="incident")
        assert zones and all(z.kind == "incident" for z in zones)

    def test_hour_filters_by_peak_hour(self, mem_db, load_rows) -> None:
        # incident: ts=22:xx → peak_hour=22; reb: ts=14:xx → peak_hour=14.
        _setup_full(mem_db, load_rows)
        zones_22 = zones_service.compute_zones(mem_db, hour=22)
        assert zones_22 and all(z.peak_hour == 22 for z in zones_22)

    def test_hour_no_match_returns_empty(self, mem_db, load_rows) -> None:
        # hour=3 не встречается ни в одном кластере тестовых данных.
        _setup_full(mem_db, load_rows)
        assert zones_service.compute_zones(mem_db, hour=3) == []


# ---------------------------------------------------------------------------
# Пустой кейс — не ошибка, а [].
# ---------------------------------------------------------------------------


class TestEmpty:
    def test_no_points_returns_empty_list(self, mem_db, load_rows) -> None:
        load_rows(
            mem_db,
            "v_incidents",
            [],
            columns=["lat", "lon", "alarm_code", "risk_level", "ts"],
        )
        load_rows(
            mem_db,
            "navigation__track_periods",
            [],
            columns=["vehicle_id", "public_unit_id", "date", "period_index", "period_type", "period_duration"],
        )
        load_rows(
            mem_db,
            "navigation__track_points",
            [],
            columns=["public_unit_id", "date", "period_index", "timestamp", "latitude", "longitude"],
        )
        assert zones_service.compute_zones(mem_db) == []
