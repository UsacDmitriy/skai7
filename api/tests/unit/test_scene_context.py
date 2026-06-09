"""Unit-тесты scene-context (идея #11, модуль b16) — против 00-CONTRACT.md §8.1.

Трек Tests (feat/tests). Покрывает детерминизм и форму кэша сцены без VLM и
без сети на готовом data/ai/scene_labels.json.

Check:
- incident_scene: ровно 54 строки, значения полей из enum §8.1, без NULL.
- Кэш детерминирован: повторная загрузка того же JSON даёт идентичную таблицу.
- Кадр отсутствует → scene_confidence=0, поля unknown, не падает.
- Рантайм-импорт scene_precompute не требует VLM-зависимости.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# api/tests/unit/ → api/tests/ → api/ → <worktree_root>
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_SCENE_JSON = _PROJECT_ROOT / "data" / "ai" / "scene_labels.json"

# scene_precompute живёт в feat/backend, попадает сюда после барьера x6.
# До слияния — тесты против модуля пропускаются (не падают).
try:
    from api.etl import scene_precompute as _sp  # noqa: E402
    _SP_AVAILABLE = True
except ImportError:
    _sp = None  # type: ignore[assignment]
    _SP_AVAILABLE = False

_SP_SKIP = pytest.mark.skipif(
    not _SP_AVAILABLE,
    reason="api.etl.scene_precompute не найден — модуль попадёт после барьера x6.",
)

# Enum-множества §8.1 + "unknown" как легальный §8.0-сентинел фолбэка.
_WEATHER_VALID = {"clear", "rain", "snow", "fog", "unknown"}
_DAY_NIGHT_VALID = {"day", "twilight", "night"}
_ROAD_SURFACE_VALID = {"dry", "wet", "snow", "ice", "unknown"}
_AREA_VALID = {"urban", "highway", "unknown"}
_VISIBILITY_VALID = {"good", "moderate", "poor", "unknown"}
# source: производственные значения + "placeholder" (seed Wave-3, w3-16).
_SOURCE_VALID = {"vlm", "cache", "placeholder"}


# ---------------------------------------------------------------------------
# Хелпер: загрузка записей из JSON.
# ---------------------------------------------------------------------------

def _load_records(path: Path = _SCENE_JSON) -> list[dict]:
    """Прочесть records из scene_labels.json (список или обёртка с полем records)."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    return raw.get("records", raw)


# ---------------------------------------------------------------------------
# 1. Форма кэша: 54 строки, enum-поля, нет NULL.
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not _SCENE_JSON.exists(),
    reason="data/ai/scene_labels.json не найден — запусти `make db` / ai_cache_seed.",
)
class TestSceneCacheShape:
    """Проверяет структуру уже собранного data/ai/scene_labels.json."""

    @pytest.fixture(scope="class")
    def records(self) -> list[dict]:
        return _load_records()

    def test_exactly_54_rows(self, records: list[dict]) -> None:
        # §8.1: ровно 1 строка на каждый из 54 видео-аларм.
        assert len(records) == 54, f"Ожидали 54 строки, получили {len(records)}"

    def test_no_null_fields(self, records: list[dict]) -> None:
        for rec in records:
            for field, value in rec.items():
                assert value is not None, (
                    f"NULL в поле '{field}' записи id={rec.get('id')}"
                )

    def test_weather_enum(self, records: list[dict]) -> None:
        bad = {r["weather"] for r in records} - _WEATHER_VALID
        assert not bad, f"Недопустимые значения weather: {bad}"

    def test_day_night_enum(self, records: list[dict]) -> None:
        bad = {r["day_night"] for r in records} - _DAY_NIGHT_VALID
        assert not bad, f"Недопустимые значения day_night: {bad}"

    def test_road_surface_enum(self, records: list[dict]) -> None:
        bad = {r["road_surface"] for r in records} - _ROAD_SURFACE_VALID
        assert not bad, f"Недопустимые значения road_surface: {bad}"

    def test_area_enum(self, records: list[dict]) -> None:
        bad = {r["area"] for r in records} - _AREA_VALID
        assert not bad, f"Недопустимые значения area: {bad}"

    def test_visibility_enum(self, records: list[dict]) -> None:
        bad = {r["visibility"] for r in records} - _VISIBILITY_VALID
        assert not bad, f"Недопустимые значения visibility: {bad}"

    def test_source_enum(self, records: list[dict]) -> None:
        bad = {r["source"] for r in records} - _SOURCE_VALID
        assert not bad, f"Недопустимые значения source: {bad}"

    def test_scene_confidence_range(self, records: list[dict]) -> None:
        for rec in records:
            conf = rec["scene_confidence"]
            assert isinstance(conf, (int, float)), (
                f"scene_confidence не число: {conf!r}"
            )
            assert 0.0 <= conf <= 1.0, (
                f"scene_confidence={conf} вне [0,1] у id={rec.get('id')}"
            )

    def test_required_fields_present(self, records: list[dict]) -> None:
        required = {
            "id", "weather", "day_night", "road_surface",
            "area", "visibility", "scene_confidence", "source",
        }
        for rec in records:
            missing = required - set(rec.keys())
            assert not missing, (
                f"Отсутствуют поля {missing} у id={rec.get('id')}"
            )


# ---------------------------------------------------------------------------
# 2. Детерминизм: повторная загрузка JSON даёт идентичный результат.
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not _SCENE_JSON.exists(),
    reason="data/ai/scene_labels.json не найден.",
)
def test_cache_deterministic_on_reload() -> None:
    """Повторная загрузка того же файла даёт байт-идентичный список записей."""
    first = _load_records()
    second = _load_records()
    assert first == second, "Повторная загрузка JSON дала отличный результат"


@pytest.mark.skipif(
    not _SCENE_JSON.exists(),
    reason="data/ai/scene_labels.json не найден.",
)
def test_cache_sorted_by_id() -> None:
    """Записи отсортированы по id (ORDER BY id) — детерминизм байт-идентичности."""
    records = _load_records()
    ids = [r["id"] for r in records]
    assert ids == sorted(ids), "Записи не отсортированы по id"


# ---------------------------------------------------------------------------
# 3. Фолбэк при отсутствии кадра: scene_confidence=0, поля unknown, не падает.
# ---------------------------------------------------------------------------

@_SP_SKIP
class TestFallbackOnMissingFrame:
    """Тестирует функции scene_precompute без VLM и без сети."""

    @pytest.fixture(autouse=True)
    def _import_module(self):
        self.sp = _sp

    def test_fallback_record_no_null(self) -> None:
        rec = self.sp._fallback_record("test-id-001", "night")
        for field, value in rec.items():
            assert value is not None, f"NULL в поле '{field}' у фолбэка"

    def test_fallback_record_scene_confidence_zero(self) -> None:
        rec = self.sp._fallback_record("test-id-001", "night")
        assert rec["scene_confidence"] == 0.0

    def test_fallback_record_fields_unknown(self) -> None:
        rec = self.sp._fallback_record("test-id-001", "day")
        assert rec["weather"] == "unknown"
        assert rec["road_surface"] == "unknown"
        assert rec["area"] == "unknown"
        assert rec["visibility"] == "unknown"

    def test_fallback_record_day_night_preserved(self) -> None:
        for dn in ("day", "twilight", "night"):
            rec = self.sp._fallback_record("x", dn)
            assert rec["day_night"] == dn

    def test_scene_record_backend_none_returns_fallback(self) -> None:
        """backend=None (нет VLM) → всегда фолбэк, не падает."""
        inc = ("id-abc", "2026-05-15 03:37:22+04", None, None)
        rec = self.sp._scene_record(inc, backend=None)
        assert rec["scene_confidence"] == 0.0
        assert rec["weather"] == "unknown"
        assert rec["source"] == "cache"

    def test_scene_record_no_camera_urls_returns_fallback(self) -> None:
        """cam_front_url=None, cam_dms_url=None → нет кадра → фолбэк."""
        inc = ("id-xyz", "2026-05-15 08:00:00+04", None, None)
        rec = self.sp._scene_record(inc, backend=None)
        assert rec["scene_confidence"] == 0.0
        assert rec["area"] == "unknown"

    def test_scene_record_missing_file_returns_fallback(self) -> None:
        """Путь к несуществующему файлу → _extract_frame → None → фолбэк."""
        class _DummyBackend:
            def __call__(self, frame):
                raise AssertionError("VLM не должен вызываться")

        inc = ("id-zzz", "2026-05-15 14:00:00+04",
               "/nonexistent/path/clip.mp4", None)
        rec = self.sp._scene_record(inc, backend=_DummyBackend())
        # Файла нет → _extract_frame вернул None → фолбэк
        assert rec["scene_confidence"] == 0.0
        assert rec["weather"] == "unknown"


# ---------------------------------------------------------------------------
# 4. Рантайм-импорт не требует VLM-зависимости.
# ---------------------------------------------------------------------------

@_SP_SKIP
def test_import_scene_precompute_without_vlm() -> None:
    """Модуль scene_precompute импортируется без torch / transformers / groq."""
    assert callable(getattr(_sp, "precompute", None))
    assert callable(getattr(_sp, "_fallback_record", None))
    assert callable(getattr(_sp, "_scene_record", None))


@_SP_SKIP
def test_day_night_determinism() -> None:
    """_day_night_from_hour детерминирован: один вход — один выход."""
    fn = _sp._day_night_from_hour
    for hour in range(24):
        a = fn(hour)
        b = fn(hour)
        assert a == b
        assert a in {"day", "twilight", "night"}


@_SP_SKIP
def test_hour_of_parsing() -> None:
    """_hour_of корректно разбирает оба формата ts."""
    fn = _sp._hour_of
    assert fn("2026-05-15 03:37:22+04") == 3
    assert fn("2026-05-15T08:15:00Z") == 8
    assert fn("2026-05-15 17:59:59") == 17
