"""Unit-покрытие ETL `api/etl/build_duckdb.py` (b1) — против `00-CONTRACT.md` §1.

Дополняет t1 (b2/b7/b10 уже покрыты). Тесты собирают БД во **временный файл**
из `datasets/ready/**` (детерминированно, без сети и без поднятого uvicorn) и
проверяют: число загруженных таблиц, идемпотентность пересборки и непустоту
ключевых таблиц. Если входных артефактов нет — чистый `skip` (переносимость).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from api.core.config import settings
from api.etl import build_duckdb as etl


# ---------------------------------------------------------------------------
# Локальные пути к источникам ETL (как в `make db`).
# ---------------------------------------------------------------------------

_READY = settings.datasets_dir
_JSON = settings.project_root / "data" / "analysis" / "alarm_types.json"
_SQL = settings.project_root / "api" / "sql"
_SEED = settings.project_root / "data" / "seed"


def _sources_present() -> bool:
    return _READY.exists() and _JSON.exists()


pytestmark = pytest.mark.skipif(
    not _sources_present(),
    reason=f"Нет источников ETL ({_READY} / {_JSON}); запусти из корня репозитория.",
)


def _expected_csv_tables() -> set[str]:
    """Имена таблиц, которые ETL обязан создать из `datasets/ready/**`.

    Используем сами функции модуля (`_resolve_prefix`/`_table_name`) — так
    ожидание не «магическое число», а пересчитывается из файловой системы.
    """
    names: set[str] = set()
    for csv_path in sorted(_READY.rglob("*.csv")):
        prefix = etl._resolve_prefix(csv_path, _READY)
        if prefix is not None:
            names.add(etl._table_name(prefix, csv_path))
    return names


def _base_tables(db_path: Path) -> set[str]:
    import duckdb

    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE'"
        ).fetchall()
        return {r[0] for r in rows}
    finally:
        conn.close()


def _count(db_path: Path, table: str) -> int:
    import duckdb

    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        return int(conn.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0])
    finally:
        conn.close()


@pytest.fixture
def built_db(tmp_path: Path) -> Path:
    """Собрать свежую БД во временный файл (один build на тест-функцию)."""
    db_path = tmp_path / "etl.duckdb"
    etl.build(
        db_path=db_path,
        ready_dir=_READY,
        json_path=_JSON,
        sql_dir=_SQL,
        seed_dir=_SEED,
    )
    return db_path


class TestTablesLoaded:
    def test_all_ready_csvs_mapped_to_tables(self, built_db: Path) -> None:
        """Все CSV из `datasets/ready/**` (≥6 папок, ~41 таблица) загружены."""
        expected = _expected_csv_tables()
        assert expected, "не нашли ни одного CSV с префиксом — проверь datasets/ready"
        base = _base_tables(built_db)
        assert expected <= base, f"не загружены таблицы: {expected - base}"

    def test_six_source_folders_represented(self, built_db: Path) -> None:
        """6 верхнеуровневых папок (§1) дают свои префиксы среди таблиц."""
        prefixes = {name.split("__", 1)[0] for name in _expected_csv_tables()}
        # FOLDER_PREFIX покрывает 6 папок ready/ (manifest.csv в корне — пропущен).
        assert {
            "video_events",
            "fuel",
            "navigation",
            "sensors",
            "normal_zis",
            "reference",
        } <= prefixes

    def test_seed_and_catalog_tables_present(self, built_db: Path) -> None:
        base = _base_tables(built_db)
        assert "alarm_type_catalog" in base
        assert "driver_reference" in base and "driver_trips" in base


class TestKeyTablesNonEmpty:
    def test_alarm_catalog_has_15_rows(self, built_db: Path) -> None:
        # §1: каталог типов аларм — 15 кодов (14 + DIAGNOSTIC/CameraOffline, w3-2).
        assert _count(built_db, "alarm_type_catalog") == 15

    def test_alarms_and_videofiles_non_empty(self, built_db: Path) -> None:
        # alarms>0 (54 алярма §1.3); видеофайлы смаплены в таблицу.
        assert _count(built_db, "video_events__selected_video_alarms") > 0
        assert _count(built_db, "video_events__video_files") > 0

    def test_v_incidents_view_materialized(self, built_db: Path) -> None:
        # SQL-вью применились в правильном порядке → лента 55 (54 видео + 1 no-video seed, §1.3/w3-5).
        assert _count(built_db, "v_incidents") == 55


class TestIdempotency:
    def test_rebuild_keeps_schema_and_no_duplicate_rows(self, tmp_path: Path) -> None:
        """`make db` дважды → одинаковая схема и те же row-counts (без дублей)."""
        db_path = tmp_path / "idem.duckdb"
        kwargs = dict(
            db_path=db_path,
            ready_dir=_READY,
            json_path=_JSON,
            sql_dir=_SQL,
            seed_dir=_SEED,
        )

        etl.build(**kwargs)
        tables_1 = _base_tables(db_path)
        catalog_1 = _count(db_path, "alarm_type_catalog")
        alarms_1 = _count(db_path, "video_events__selected_video_alarms")

        etl.build(**kwargs)  # пересборка в тот же файл
        tables_2 = _base_tables(db_path)

        assert tables_2 == tables_1, "схема изменилась после пересборки"
        # CREATE OR REPLACE / DROP+CREATE → без удвоения строк.
        assert _count(db_path, "alarm_type_catalog") == catalog_1 == 15
        assert _count(db_path, "video_events__selected_video_alarms") == alarms_1
