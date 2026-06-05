"""Shared pytest fixtures & row-builders for SKAI backend tests.

Owned by **t1** (track Tests, `feat/tests`). Против `00-CONTRACT.md` §2/§7.1/§7.5.
Переиспользуется:
  - `api/tests/unit/**`        — per-feature unit-промпты `tu-*` (enrichment/driver/nlu/...),
  - `api/tests/integration/**` — API-тесты `t2` (TestClient).

Принципы (Check t1): тесты быстрые, **без сети и без поднятого uvicorn**.
  * `mem_db` + `load_rows` — in-memory DuckDB на сэмпле (для view/SQL-правил без `make db`);
  * `real_db` / `client`    — против собранной `data/skai.duckdb`, со `skip`, если её нет;
  * `*_row` фикстуры        — детерминированные builder'ы строк сырых таблиц / схем.

Все SQL-идентификаторы — в двойных кавычках (CLAUDE.md / §0). Тяжёлые/опциональные
импорты (duckdb, pandas, fastapi, api.*) — ленивые, внутри фикстур: коллекция
`pytest api/tests/unit -q` собирается даже на пустом наборе и на голом окружении.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Iterator

import pytest

# api/tests/conftest.py -> api/tests -> api -> <project_root>.
# Держим корень проекта на sys.path, чтобы `import api.*` работал из любой cwd.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Row builders — детерминированные dict-фабрики под сырые таблицы / схемы.
# Дефолт = валидный «happy» кейс; точечные правки через kwargs-overrides.
# ---------------------------------------------------------------------------


@pytest.fixture
def video_file_row() -> Callable[..., dict]:
    """Строка `video_events__video_files` для `enrichment.cameras_from_videofiles` (§2).

    Дефолт — online-канал ADAS (channel=1, download_status="downloaded").
    Ключи `channel` / `download_status` / `created_at_utc` читает enrichment.
    """
    def _build(**overrides: Any) -> dict:
        row = {
            "channel": 1,
            "download_status": "downloaded",
            "media_relative_path": "datasets/media/ch1/clip.mp4",
            "created_at_utc": "2026-06-01T12:00:00Z",
        }
        row.update(overrides)
        return row

    return _build


@pytest.fixture
def track_point_row() -> Callable[..., dict]:
    """Строка `track_points` для `enrichment.telemetry_from_trackpoints` (§2).

    Ключи `timestamp_utc` / `speed_kmh` — дословно как в CSV.
    """
    def _build(**overrides: Any) -> dict:
        row = {"timestamp_utc": "2026-06-01T12:00:00Z", "speed_kmh": 60.0}
        row.update(overrides)
        return row

    return _build


@pytest.fixture
def violation_row() -> Callable[..., dict]:
    """Заготовка `ViolationRow` (§7.5) для unit-правил отчётов (`is_gross`/KPI)."""
    def _build(**overrides: Any) -> dict:
        row = {
            "id": "A1",
            "ts": "2026-06-01T12:00:00Z",
            "alarm_code": "DMS_DROWSY",
            "alarm_label_ru": "Засыпание за рулём",
            "source": "DMS",
            "severity": "high",
            "is_gross": False,
        }
        row.update(overrides)
        return row

    return _build


# ---------------------------------------------------------------------------
# In-memory DuckDB на сэмпле — для view/SQL-правил без собранной базы.
# ---------------------------------------------------------------------------


@pytest.fixture
def mem_db() -> Iterator[Any]:
    """Свежий in-memory DuckDB на каждый тест (без файла, без сети)."""
    import duckdb

    conn = duckdb.connect(":memory:")
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def load_rows() -> Callable[..., None]:
    """Создать таблицу в DuckDB из `list[dict]` (имена колонок — дословно).

    Использование::

        load_rows(mem_db, "navigation__track_periods", [{...}, {...}])
        load_rows(mem_db, "track_points", [], columns=["timestamp_utc", "speed_kmh"])

    Пустой `rows` создаёт пустую таблицу по `columns` (edge-кейс «нет данных»).
    Имя таблицы и колонки экранируются двойными кавычками (§0).
    """
    def _load(db, name: str, rows, columns=None) -> None:
        import pandas as pd

        if rows:
            frame = pd.DataFrame(list(rows))
        else:
            cols = list(columns or [])
            frame = pd.DataFrame({c: pd.Series(dtype="object") for c in cols})
        db.register("_load_rows_tmp", frame)
        try:
            db.execute(f'CREATE TABLE "{name}" AS SELECT * FROM "_load_rows_tmp"')
        finally:
            db.unregister("_load_rows_tmp")

    return _load


# ---------------------------------------------------------------------------
# Против собранной базы (`make db`) — read-only, со skip при отсутствии.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def db_path() -> Path:
    """Путь к артефакту `data/skai.duckdb` (из настроек приложения)."""
    from api.core.config import settings

    return settings.db_path


@pytest.fixture(scope="session")
def real_db(db_path: Path) -> Iterator[Any]:
    """Read-only коннект к собранной `data/skai.duckdb`; `skip`, если нет (`make db`)."""
    import duckdb

    if not db_path.exists():
        pytest.skip(f"DuckDB не собран ({db_path}); запусти `make db`.")
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture(scope="session")
def client(real_db) -> Iterator[Any]:
    """`fastapi.testclient.TestClient` над `api.main:app` (для t2).

    Зависит от `real_db` → тот же `skip`, когда база не собрана. Приложению
    нужна собранная БД, поэтому отдельной проверки не делаем.
    """
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Прочее.
# ---------------------------------------------------------------------------


@pytest.fixture
def seed_dir() -> Path:
    """Каталог детерминированных сидов `data/seed/` (для tu-driver: §7.1)."""
    from api.core.config import settings

    return settings.project_root / "data" / "seed"


@pytest.fixture
def no_groq(monkeypatch: pytest.MonkeyPatch) -> None:
    """Форсировать regex-fallback NLU (§7.3): ни env-ключа, ни `settings.groq_api_key`.

    Используется tu-nlu, чтобы тестировать именно детерминированную ветку без сети.
    """
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("SKAI_GROQ_API_KEY", raising=False)
    try:
        from api.core.config import settings

        monkeypatch.setattr(settings, "groq_api_key", None, raising=False)
    except Exception:
        # settings ещё может быть недоступен на голом окружении — не фейлим фикстуру.
        pass
