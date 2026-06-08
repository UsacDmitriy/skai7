"""Unit-покрытие repositories/services incidents+actions (b5) — §3.1/§3.4.

`incidents_service.list/get/get_telemetry` против собранной БД (форма §3.1) и
`actions_service` — запись `output/actions.csv` с контрактными колонками.
Read-only коннект `real_db`, `skip` без `make db`; CSV пишется во временный каталог.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from api.domain.entities import Action
from api.domain.incidents import IncidentDetail, IncidentSummary, TelemetryPoint
from api.services import actions_service, incidents_service


# ---------------------------------------------------------------------------
# incidents_service — сборка контрактных ответов (§3.1).
# ---------------------------------------------------------------------------


class TestIncidentsService:
    def test_list_returns_incident_summaries(self, real_db) -> None:
        summaries = incidents_service.list_summaries(real_db, {})
        assert summaries and all(isinstance(s, IncidentSummary) for s in summaries)

    def test_get_detail_shape(self, real_db) -> None:
        iid = incidents_service.list_summaries(real_db, {})[0].id
        detail = incidents_service.get_detail(real_db, iid)
        assert isinstance(detail, IncidentDetail)
        assert detail.id == iid
        assert len(detail.cameras) == 3  # §2: всегда 3 канонических слота.
        assert all(isinstance(t, TelemetryPoint) for t in detail.telemetry)

    def test_get_telemetry_is_point_list(self, real_db) -> None:
        iid = incidents_service.list_summaries(real_db, {})[0].id
        telemetry = incidents_service.get_telemetry(real_db, iid)
        assert isinstance(telemetry, list)
        assert all(isinstance(t, TelemetryPoint) for t in telemetry)

    def test_unknown_id_is_graceful(self, real_db) -> None:
        # Неизвестный id: detail → None (роутер → 404), телеметрия → [].
        assert incidents_service.get_detail(real_db, "no-such-id") is None
        assert incidents_service.get_telemetry(real_db, "no-such-id") == []


# ---------------------------------------------------------------------------
# actions_service — журнал output/actions.csv (§3.4).
# ---------------------------------------------------------------------------


class TestActionsService:
    def test_writes_csv_with_contract_columns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from api.core.config import settings

        monkeypatch.setattr(settings, "output_dir", tmp_path)
        actions_service.reset_overrides()

        actions_service.record(Action(incident_id="INC-42", action="create_task", comment="hello"))

        csv_path = tmp_path / "actions.csv"
        assert csv_path.exists()
        lines = csv_path.read_text(encoding="utf-8").strip().splitlines()
        # Колонки контракта §3.4 — дословно.
        assert lines[0] == "created_at,incident_id,action,comment"
        # created_at,incident_id,action,comment — ровно 4 поля в строке данных.
        last = lines[-1].split(",")
        assert last[1:4] == ["INC-42", "create_task", "hello"]
        assert last[0]  # created_at не пуст

        actions_service.reset_overrides()

    def test_record_updates_runtime_status(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from api.core.config import settings

        monkeypatch.setattr(settings, "output_dir", tmp_path)
        actions_service.reset_overrides()

        assert actions_service.status_for("INC-7") == "active"  # дефолт
        actions_service.record(Action(incident_id="INC-7", action="validate", comment="ok"))
        assert actions_service.status_for("INC-7") == "validated"

        actions_service.reset_overrides()
