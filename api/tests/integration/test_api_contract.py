"""Интеграционные негативы + регистрация роутеров + офлайн-детерминизм (w3-3).

Перенесено из аудита барьеров: единая негативная матрица по доменам P0/P1/P2,
анти-404 регистрации роутеров (теги в OpenAPI) и проверка, что NLU-запрос без
`GROQ_API_KEY` детерминирован. Только `TestClient` — без сети и без поднятого
uvicorn; фикстуры скипаются без собранной БД (`make db`).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app


# ---------------------------------------------------------------------------
# Негативная матрица — неизвестный id → 404 (detail-домены).
# ---------------------------------------------------------------------------


class TestUnknownIdReturns404:
    @pytest.mark.parametrize(
        "path",
        [
            "/api/incidents/no-such-id",
            "/api/alerts/no-such-id",
            "/api/trips/no-such-id",
            "/api/reb/no-such-vehicle",
        ],
    )
    def test_unknown_id_404(self, client: TestClient, path: str) -> None:
        assert client.get(path).status_code == 404


class TestReportsDegradeGracefully:
    """Отчёты по неизвестному `plate` — контракт §61/§62: мягкая деградация.

    `reports_service` не отдаёт 404 на неизвестный ТС (по дизайну «не падать»):
    возвращает валидный отчёт с нулевыми KPI / пустыми списками. Негатив здесь =
    «200 + безопасная пустая форма, НЕ 500», а не 404.
    """

    def test_driver_report_unknown_plate_is_empty_not_500(self, client: TestClient) -> None:
        r = client.get("/api/reports/driver/NOSUCHPLATE")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["kpi"]["total"] == 0
        assert body["violations"] == []

    def test_vehicle_report_unknown_plate_is_empty_not_500(self, client: TestClient) -> None:
        r = client.get("/api/reports/vehicle/NOSUCHPLATE")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["period_alarms"] == []
        assert len(body["cameras"]) == 3  # §2: всегда 3 канонических слота


# ---------------------------------------------------------------------------
# Негативная матрица — битое/неполное тело → 422.
# ---------------------------------------------------------------------------


class TestBadBodyReturns422:
    def test_query_missing_text(self, client: TestClient) -> None:
        assert client.post("/api/reports/query", json={}).status_code == 422

    def test_query_wrong_period_type(self, client: TestClient) -> None:
        assert (
            client.post(
                "/api/reports/query", json={"text": "hi", "period_days": "nope"}
            ).status_code
            == 422
        )

    def test_actions_missing_incident_id(self, client: TestClient) -> None:
        assert client.post("/api/actions", json={"action": "validate"}).status_code == 422

    def test_actions_invalid_action_enum(self, client: TestClient) -> None:
        assert (
            client.post(
                "/api/actions", json={"incident_id": "x", "action": "frobnicate"}
            ).status_code
            == 422
        )


# ---------------------------------------------------------------------------
# Пустой фильтр/набор → [] (не 500), видеоканал без файла → 404 (не 500).
# ---------------------------------------------------------------------------


class TestEmptyAndMissingNot500:
    def test_empty_filter_returns_empty_list(self, client: TestClient) -> None:
        r = client.get("/api/incidents", params={"vehicle_plate": "ZZZ-NONE"})
        assert r.status_code == 200
        assert r.json() == []

    def test_invalid_channel_404(self, client: TestClient, first_incident_id: str) -> None:
        assert client.get(f"/api/incidents/{first_incident_id}/video/99").status_code == 404

    def test_unknown_incident_video_404(self, client: TestClient) -> None:
        # Канал без файла / неизвестный инцидент → 404 (НЕ 500).
        assert client.get("/api/incidents/no-such-id/video/2").status_code == 404

    def test_real_incident_video_channel_never_500(
        self, client: TestClient, first_incident_id: str
    ) -> None:
        # Реальный инцидент, канал 2: есть файл → 200, нет → 404; никогда 500.
        assert client.get(f"/api/incidents/{first_incident_id}/video/2").status_code in (200, 404)

    @pytest.mark.parametrize("path", ["/api/fuel", "/api/sensors", "/api/navigation"])
    def test_dark_data_lists_return_200(self, client: TestClient, path: str) -> None:
        # §9 (w3-6/7/8): домены раскрыты из стаба 501 → список 200, непустой.
        r = client.get(path)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list) and r.json()

    @pytest.mark.parametrize(
        "path",
        ["/api/fuel/A123BC77", "/api/sensors/A123BC77", "/api/navigation/A123BC77"],
    )
    def test_dark_data_unknown_plate_404(self, client: TestClient, path: str) -> None:
        # Неизвестный госномер → детерминированный 404 (НЕ 501/5xx).
        assert client.get(path).status_code == 404


# ---------------------------------------------------------------------------
# Анти-404 регистрации роутеров — все ожидаемые теги в OpenAPI.
# ---------------------------------------------------------------------------


def test_all_router_tags_registered() -> None:
    """Ловит «забыли include_router»: все теги доменов присутствуют в OpenAPI.

    Не зависит от данных — отдельный клиент без skip по БД (`app.openapi()` не
    содержит top-level `tags`, поэтому собираем теги операций из `paths`).
    """
    expected = {
        "incidents",
        "reports",
        "vehicles",
        "actions",
        "tickets",
        "alerts",
        "trips",
        "sabotage",
        "reb",
        "fuel",
        "sensors",
        "navigation",
    }
    with TestClient(app) as c:
        spec = c.get("/openapi.json").json()
    tags = {
        tag
        for path in spec["paths"].values()
        for operation in path.values()
        for tag in operation.get("tags", [])
    }
    assert expected <= tags, f"отсутствуют теги (не зарегистрирован роутер): {expected - tags}"


# ---------------------------------------------------------------------------
# Офлайн-детерминизм NLU-запроса (без GROQ_API_KEY → regex-fallback).
# ---------------------------------------------------------------------------


def test_query_offline_is_deterministic(client: TestClient, no_groq) -> None:
    payload = {"text": "Сводка по парку"}
    first = client.post("/api/reports/query", json=payload)
    second = client.post("/api/reports/query", json=payload)
    assert first.status_code == 200 and second.status_code == 200
    # regex-ветка детерминирована: и разобранный запрос, и весь fleet-отчёт совпадают.
    assert first.json()["query"] == second.json()["query"]
    assert first.json() == second.json()
