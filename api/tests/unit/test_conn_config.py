"""Unit-покрытие конфигурации и DuckDB-коннекта (b4) — §0/§3.

`config.Settings` (env-префикс SKAI_, дефолты), `duckdb_conn` (read-only коннект,
понятная ошибка без БД) и health-эндпоинт. Без сети и без поднятого uvicorn —
TestClient или прямой вызов. Продуктовый код не правится.
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Settings (§0) — дефолты и переопределение через env (префикс SKAI_).
# ---------------------------------------------------------------------------


class TestSettings:
    def test_path_defaults(self) -> None:
        from api.core.config import settings

        assert settings.db_path.name == "skai.duckdb"
        assert settings.datasets_dir.name == "ready"
        # whisper-дефолты §7.3.
        assert settings.whisper_model == "large-v3"
        assert settings.whisper_device == "cpu"

    def test_cors_origins_default(self) -> None:
        from api.core.config import settings

        assert settings.cors_origins == ["http://localhost:5173"]

    def test_env_override_scalar(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # SKAI_-префикс читается на инстанцировании Settings.
        monkeypatch.setenv("SKAI_WHISPER_DEVICE", "cuda")
        from api.core.config import Settings

        assert Settings().whisper_device == "cuda"

    def test_env_override_list_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Список CORS читается из JSON-значения env.
        monkeypatch.setenv("SKAI_CORS_ORIGINS", '["https://app.example.com"]')
        from api.core.config import Settings

        assert Settings().cors_origins == ["https://app.example.com"]


# ---------------------------------------------------------------------------
# duckdb_conn (§3) — read-only и понятная ошибка при отсутствии БД.
# ---------------------------------------------------------------------------


class TestDuckDBConn:
    def test_connection_is_read_only(self, real_db) -> None:
        # Канон b4: коннект открыт read-only — DDL/запись отвергаются.
        import duckdb

        with pytest.raises(duckdb.Error):
            real_db.execute('CREATE TABLE "should_fail" ("x" INTEGER)')

    def test_missing_db_raises_clear_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Нет файла БД → FileNotFoundError с подсказкой `make db` (строка 35)."""
        from api.core import duckdb_conn
        from api.core.config import settings

        monkeypatch.setattr(settings, "db_path", tmp_path / "absent.duckdb")
        # Сбрасываем кеш коннекта; raise происходит ДО присваивания — глобал не портим.
        monkeypatch.setattr(duckdb_conn, "_connection", None, raising=False)

        with pytest.raises(FileNotFoundError):
            duckdb_conn.get_connection()

    def test_get_db_yields_working_cursor(self, db_path: Path) -> None:
        """`get_db` отдаёт рабочий thread-local курсор поверх собранной БД."""
        if not db_path.exists():
            pytest.skip(f"DuckDB не собран ({db_path}); запусти `make db`.")
        from api.core import duckdb_conn

        gen = duckdb_conn.get_db()
        cursor = next(gen)
        try:
            assert cursor.execute("SELECT 1").fetchone()[0] == 1
        finally:
            gen.close()


# ---------------------------------------------------------------------------
# health-эндпоинт (§3) — отдаёт ok без зависимости от БД.
# ---------------------------------------------------------------------------


def test_health_returns_ok() -> None:
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
