"""
ETL: оффлайн VLM-предрасчёт контекста сцены (идея #11, b16 · §8.1/§8.4).

По 54 видео-алярмам из ``v_incidents`` берёт репрезентативный кадр (первый
доступный ``cam_front_url`` ch1, иначе ``cam_dms_url`` ch5), прогоняет через VLM
и кэширует метки сцены в ``data/ai/scene_labels.json``. Рантайм API/``make db``
читает готовую таблицу ``incident_scene`` — **без VLM и без сети**.

Бэкенд VLM выбирается переменной окружения ``SCENE_VLM_BACKEND`` (по умолчанию
``none`` ⇒ детерминированный фолбэк §8.0). Зависимость от VLM — **только здесь**
(ленивый импорт внутри бэкенда), в рантайме не нужна.

Поля §8.1 (incident_scene):
    id, weather ∈ {clear,rain,snow,fog}, day_night ∈ {day,twilight,night},
    road_surface ∈ {dry,wet,snow,ice,unknown}, area ∈ {urban,highway,unknown},
    visibility ∈ {good,moderate,poor}, scene_confidence (0..1),
    source ∈ {vlm,cache}.

Фолбэк (нет кадра/файла/бэкенда) — детерминированно: ``weather="unknown"``,
``day_night`` из часа ``ts``, остальные сценовые поля ``"unknown"``,
``scene_confidence=0.0``, ``source="cache"`` (§8.0). Не падать.

Детерминизм: ни ``Date.now()``, ни ``random``. Метки — функция от данных алярма
(``id``, ``ts``, кадр). ``ORDER BY id`` + фиксированный порядок ключей ⇒
повторный прогон даёт байт-идентичный файл (идемпотентность/``--force``).

Usage:
    python -m api.etl.scene_precompute            # no-op если кэш есть
    python -m api.etl.scene_precompute --force    # пересобрать кэш
    python api/etl/scene_precompute.py [db_path] [--force]
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Allow `python api/etl/scene_precompute.py` entry point (no -m flag)
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import duckdb

DB_PATH = Path("data/skai.duckdb")
AI_DIR = Path("data/ai")
SCENE_PATH = AI_DIR / "scene_labels.json"

# Бэкенд VLM: none (фолбэк) | florence2 | moondream | groq | claude.
VLM_BACKEND = os.getenv("SCENE_VLM_BACKEND", "none").strip().lower()

# Enum §8.1 — допустимые значения + сентинел "unknown" фолбэка (§8.0).
_WEATHER = {"clear", "rain", "snow", "fog", "unknown"}
_DAY_NIGHT = {"day", "twilight", "night"}
_ROAD_SURFACE = {"dry", "wet", "snow", "ice", "unknown"}
_AREA = {"urban", "highway", "unknown"}
_VISIBILITY = {"good", "moderate", "poor", "unknown"}


# ── Детерминированный day_night из часа ts (§8.0) ──────────────────────────────
def _hour_of(ts: str) -> int:
    """Час из строки ts ('2026-05-15 03:37:22+04' или ISO с 'T'). Без datetime.now:
    берём литеральный час метки (§8.0)."""
    time_part = ts.replace("T", " ").split(" ", 1)[1]
    return int(time_part.split(":")[0])


def _day_night_from_hour(hour: int) -> str:
    """Час → day_night ∈ {day,twilight,night} (§8.1). day 08–17, twilight 06–07 и
    18–20, иначе night. Единственное «реальное» поле фолбэка."""
    if 8 <= hour < 18:
        return "day"
    if (6 <= hour < 8) or (18 <= hour < 21):
        return "twilight"
    return "night"


# ── Кадр и VLM-бэкенд (ленивый импорт; не нужны в рантайме) ────────────────────
def _frame_ref(cam_front_url: str | None, cam_dms_url: str | None) -> str | None:
    """Репрезентативный кадр: первый доступный ch1 (front), иначе ch5 (dms)."""
    return cam_front_url or cam_dms_url


def _extract_frame(media_rel_path: str):
    """Один кадр из видео (opencv, без чтения файла целиком). Возвращает BGR-массив
    или None, если файла нет / декодер недоступен. Ленивый импорт cv2."""
    path = Path(media_rel_path)
    if not path.is_file():
        return None
    try:
        import cv2  # ленивый импорт — только в предрасчёте
    except Exception:
        return None
    cap = cv2.VideoCapture(str(path))
    try:
        ok, frame = cap.read()  # первый кадр — детерминированно, без таймстемпа
    finally:
        cap.release()
    return frame if ok else None


def _make_backend(name: str):
    """Фабрика VLM-бэкенда. ``none`` ⇒ None (чистый фолбэк). Реальные бэкенды —
    ленивый импорт тяжёлых зависимостей; ошибка импорта при ЯВНОМ выборе → RuntimeError
    (config-явный выбор не должен молча деградировать)."""
    if name in ("", "none", "off", "fallback"):
        return None
    if name in ("florence2", "moondream"):
        return _LocalVlmBackend(name)
    if name in ("groq", "claude"):
        return _ApiVlmBackend(name)
    raise RuntimeError(
        f"Неизвестный SCENE_VLM_BACKEND={name!r}; допустимо: "
        "none|florence2|moondream|groq|claude"
    )


class _LocalVlmBackend:
    """Локальная VLM (Florence-2 / Moondream) через transformers. Ленивая загрузка
    модели при первом вызове. Зависимости (torch/transformers/PIL) импортируются
    здесь — в рантайме API не нужны."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._model = None

    def _ensure_loaded(self):
        if self._model is not None:
            return
        try:
            import torch  # noqa: F401
            from transformers import AutoModelForCausalLM, AutoProcessor
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"SCENE_VLM_BACKEND={self.name} требует torch+transformers: {exc}"
            ) from exc
        model_id = {
            "florence2": "microsoft/Florence-2-base",
            "moondream": "vikhyatk/moondream2",
        }[self.name]
        self._processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
        self._model = AutoModelForCausalLM.from_pretrained(
            model_id, trust_remote_code=True
        ).eval()

    def __call__(self, frame) -> dict:
        self._ensure_loaded()
        # Локальная VLM запускается оффлайн; парсинг подписи → enum-поля делает
        # _parse_caption. Детали prompt'а зависят от модели — намеренно компактно.
        import numpy as np  # noqa: F401
        from PIL import Image

        image = Image.fromarray(frame[:, :, ::-1])  # BGR→RGB
        prompt = "<MORE_DETAILED_CAPTION>"
        inputs = self._processor(text=prompt, images=image, return_tensors="pt")
        out = self._model.generate(**inputs, max_new_tokens=128, do_sample=False)
        caption = self._processor.batch_decode(out, skip_special_tokens=True)[0]
        return _parse_caption(caption)


class _ApiVlmBackend:
    """Облачная vision-модель (Groq / Claude). Кадр → base64 → запрос. Ленивый
    импорт клиента; ключ из окружения. Сетевой вызов — ТОЛЬКО в предрасчёте."""

    def __init__(self, name: str) -> None:
        self.name = name

    def __call__(self, frame) -> dict:
        import base64

        import cv2  # для кодирования кадра в JPEG

        ok, buf = cv2.imencode(".jpg", frame)
        if not ok:
            raise RuntimeError("не удалось закодировать кадр в JPEG")
        b64 = base64.b64encode(buf.tobytes()).decode("ascii")
        caption = self._query(b64)
        return _parse_caption(caption)

    def _query(self, image_b64: str) -> str:
        if self.name == "groq":
            from groq import Groq  # ленивый импорт

            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            resp = client.chat.completions.create(
                model="llama-3.2-90b-vision-preview",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _VLM_PROMPT},
                        {"type": "image_url",
                         "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                    ],
                }],
            )
            return resp.choices[0].message.content or ""
        from anthropic import Anthropic  # ленивый импорт

        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        msg = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=256,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": _VLM_PROMPT},
                    {"type": "image", "source": {
                        "type": "base64", "media_type": "image/jpeg", "data": image_b64}},
                ],
            }],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


_VLM_PROMPT = (
    "Опиши дорожную сцену по кадру строго как JSON с ключами "
    "weather(clear|rain|snow|fog), road_surface(dry|wet|snow|ice|unknown), "
    "area(urban|highway|unknown), visibility(good|moderate|poor), "
    "confidence(0..1). Только JSON, без пояснений."
)


def _parse_caption(text: str) -> dict:
    """Подпись/JSON от VLM → enum-поля §8.1. Любое нераспознанное значение → 'unknown'
    (для visibility/weather — 'unknown'-сентинел фолбэка). Детерминированно."""
    weather = road = area = visibility = "unknown"
    confidence = 0.0
    # Пытаемся выделить JSON-объект из ответа.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
        except Exception:  # noqa: BLE001
            obj = {}
        weather = _coerce(obj.get("weather"), _WEATHER)
        road = _coerce(obj.get("road_surface"), _ROAD_SURFACE)
        area = _coerce(obj.get("area"), _AREA)
        visibility = _coerce(obj.get("visibility"), _VISIBILITY)
        try:
            confidence = max(0.0, min(1.0, float(obj.get("confidence", 0.0))))
        except (TypeError, ValueError):
            confidence = 0.0
    return {
        "weather": weather,
        "road_surface": road,
        "area": area,
        "visibility": visibility,
        "scene_confidence": round(confidence, 3),
    }


def _coerce(value, allowed: set[str]) -> str:
    """Привести значение к enum: lower/strip; вне набора → 'unknown'."""
    if isinstance(value, str):
        v = value.strip().lower()
        if v in allowed:
            return v
    return "unknown"


# ── Сборка строки incident_scene ──────────────────────────────────────────────
def _fallback_record(incident_id: str, day_night: str) -> dict:
    """Детерминированный фолбэк (§8.0): сценовые поля 'unknown', day_night из ts,
    confidence=0, source='cache'. Фиксированный порядок ключей."""
    return {
        "id": incident_id,
        "weather": "unknown",
        "day_night": day_night,
        "road_surface": "unknown",
        "area": "unknown",
        "visibility": "unknown",
        "scene_confidence": 0.0,
        "source": "cache",
    }


def _scene_record(inc: tuple, backend) -> dict:
    """Строка incident_scene по алярму. backend=None или нет кадра ⇒ фолбэк."""
    incident_id, ts, cam_front_url, cam_dms_url = inc
    day_night = _day_night_from_hour(_hour_of(ts))
    if backend is None:
        return _fallback_record(incident_id, day_night)

    media_rel = _frame_ref(cam_front_url, cam_dms_url)
    frame = _extract_frame(media_rel) if media_rel else None
    if frame is None:
        return _fallback_record(incident_id, day_night)  # нет кадра/файла — не падать

    try:
        labels = backend(frame)
    except Exception as exc:  # noqa: BLE001 — единичный сбой VLM не валит батч
        print(f"  [scene] VLM fail {incident_id}: {exc} → фолбэк")
        return _fallback_record(incident_id, day_night)

    return {
        "id": incident_id,
        "weather": labels["weather"],
        "day_night": day_night,  # day_night всегда из ts (детерминизм §8.0)
        "road_surface": labels["road_surface"],
        "area": labels["area"],
        "visibility": labels["visibility"],
        "scene_confidence": labels["scene_confidence"],
        "source": "vlm",
    }


def _load_incidents(db_path: Path) -> list[tuple]:
    """54 видео-алярма из v_incidents (есть кадр ch1 или ch5), ORDER BY id."""
    with duckdb.connect(str(db_path), read_only=True) as conn:
        return conn.execute(
            'SELECT "id", "ts", "cam_front_url", "cam_dms_url" '
            "FROM v_incidents "
            'WHERE "cam_front_url" IS NOT NULL OR "cam_dms_url" IS NOT NULL '
            'ORDER BY "id"'
        ).fetchall()


def _write_cache(path: Path, records: list[dict]) -> None:
    """Детерминированная запись плоского JSON-массива (read_json_auto) + trailing
    newline. Сорт по id уже выполнен вызывающим."""
    text = json.dumps(records, ensure_ascii=False, indent=2)
    path.write_text(text + "\n", encoding="utf-8")


def precompute(
    db_path: Path = DB_PATH,
    ai_dir: Path = AI_DIR,
    backend_name: str = VLM_BACKEND,
    force: bool = False,
) -> int:
    """Собрать data/ai/scene_labels.json (54 строки). Идемпотентно: при наличии
    кэша без force — no-op. Возвращает число строк."""
    ai_dir.mkdir(parents=True, exist_ok=True)
    scene_path = ai_dir / "scene_labels.json"

    if scene_path.exists() and not force:
        try:
            existing = json.loads(scene_path.read_text(encoding="utf-8"))
            n = len(existing) if isinstance(existing, list) else len(existing.get("records", []))
        except Exception:  # noqa: BLE001
            n = -1
        print(f"  [scene] кэш есть ({n} записей) — no-op (--force для пересборки)")
        return n

    backend = _make_backend(backend_name)
    rows = _load_incidents(db_path)
    records = [_scene_record(inc, backend) for inc in rows]
    records.sort(key=lambda r: r["id"])  # устойчивый порядок → байт-идентичность

    _write_cache(scene_path, records)
    mode = backend_name if backend is not None else "fallback"
    print(f"  [scene] scene_labels.json {len(records):>4} записей (backend={mode})")
    print(f"Done. Scene cache written to {scene_path.resolve()}")
    return len(records)


if __name__ == "__main__":
    argv = sys.argv[1:]
    force = "--force" in argv
    positional = [a for a in argv if not a.startswith("--")]
    kwargs: dict = {"force": force}
    if positional:
        kwargs["db_path"] = Path(positional[0])
    precompute(**kwargs)
