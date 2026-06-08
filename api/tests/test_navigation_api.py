"""W3-14 · API-тесты домена navigation (CONTRACT §9.1/§9.2/§9.5 — список треков → РЭБ).

`/api/navigation` — список-вход к существующему `/api/reb/{id}` (§7.4). Покрываем:
схему списка, unmatched-строку (`reb_link_id=None`, не кликабельна), видеопарк-флаг
и сквозную связь list→РЭБ (matched `reb_link_id` резолвится в `/api/reb/{id}`).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.domain.fleet_health import NavProblemVehicle


@pytest.fixture
def nav_list(client: TestClient) -> list[dict]:
    """Список проблемных треков навигации (5 matched + 1 unmatched)."""
    r = client.get("/api/navigation")
    assert r.status_code == 200
    return r.json()


class TestNavigationList:
    def test_list_min_len_and_schema(self, nav_list: list[dict]) -> None:
        # §9.1: список 5–6 строк; каждая валидна по NavProblemVehicle (§9.2).
        assert len(nav_list) >= 5
        for item in nav_list:
            NavProblemVehicle(**item)

    def test_has_unmatched_row(self, nav_list: list[dict]) -> None:
        # §9.5: unmatched ТС → reb_link_id=None (не кликабелен), но problem_description жив.
        unmatched = [n for n in nav_list if n["reb_link_id"] is None]
        assert len(unmatched) >= 1
        for n in unmatched:
            assert n["match_status"] == "unmatched"
            assert n["problem_description"]

    def test_exactly_two_in_video_fleet(self, nav_list: list[dict]) -> None:
        # §9.0/§9.2: ровно 2 навигационных ТС пересекаются с видеопарком.
        in_vf = [n for n in nav_list if n["in_video_fleet"] is True]
        assert len(in_vf) == 2


class TestNavigationCrossLink:
    def test_matched_reb_link_resolves(self, client: TestClient, nav_list: list[dict]) -> None:
        # Сквозная связь list→РЭБ: reb_link_id matched-строки → GET /api/reb/{id} = 200.
        matched = [n for n in nav_list if n["reb_link_id"]]
        assert matched, "ожидаем хотя бы одну matched-строку с reb_link_id"
        rid = matched[0]["reb_link_id"]
        assert client.get(f"/api/reb/{rid}").status_code == 200

    def test_unknown_404(self, client: TestClient) -> None:
        # §9.5: неизвестный госномер → 404.
        assert client.get("/api/navigation/UNKNOWN999").status_code == 404
