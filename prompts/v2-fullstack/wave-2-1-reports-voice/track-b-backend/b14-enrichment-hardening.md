# b14 · Enrichment hardening — edge-cases поверх b2 (доработка Волны 1)

> Трек **Backend/Data**. Против `00-CONTRACT.md` §2 (enrichment). **Владеет:** правкой `api/core/enrichment.py`
> **Модель:** 🔵 Sonnet — детерминированная логика/вёрстка против контракта; гейт = секция Check.
> (доработка уже реализованного модуля b2 — **НЕ переписывает**, только усиливает граничные ветки/детерминизм).
> **Зависит от:** b2 (готов, Волна 1). **Волна 2.1**, окно 1 (backend), параллельно с b7–b10.
> Возникло из-за того, что b2 выполнен в Волне 1 — DoD-глубина идеи #3 не успела войти в исходный промпт
> и вынесена сюда (см. `FEATURES.md`, идея #3).

## Цель

Довести `enrichment` (идея #3) до Definition of Done на уже построенном модуле: клампы, дефолты для
неизвестных кодов, фиксированная топология камер, детерминизм — без изменения публичных сигнатур b2.

## Состав (правки в `api/core/enrichment.py`)

- `risk_score(...)` — результат всегда **clamp в [0,100]**; монотонность по severity при равных прочих
  (`critical ≥ high ≥ medium ≥ low`). Никаких выходов за диапазон на крайних входах.
- `speed_limit_for(code)` — неизвестный `alarm_code` → дефолт **`90`** (не NULL, не исключение);
  городские/DMS-коды → `60`. Аналогично label/severity неизвестного кода — дефолтные, без NULL.
- `cameras_from_videofiles(...)` — длина результата **ровно 3**; каждая камера `status ∈ {online, warning, offline}`;
  нет видео по каналу → `status="offline"`, `hasVideo=false`, `url=null` (не падать).
- При отсутствии видеоканала у инцидента — `confidence` **−10** (нет видео).
- `is_night`, `speed_limit_for`, `ax` (Δspeed/Δt) — детерминированы: один вход → один выход, без `random`/`datetime.now`.

## Check

- `python -c "from api.core import enrichment"` без ошибок; функции остаются чистыми (нет I/O/глобального состояния/недетерминизма).
- `risk_score` clamp в [0,100] на крайних входах (`speed=0,events=0` и `speed≫limit,events≫7`); монотонность по severity при фиксированных speed/limit/night/events.
- `speed_limit_for("__UNKNOWN__")` → `90`; label/severity неизвестного кода — дефолтные, без NULL.
- `cameras_from_videofiles([])` → 3 камеры со `status="offline"`/`hasVideo=false`; при отсутствии видеоканала `confidence` инцидента −10.
- `cameras` всегда длины 3, каждый `status ∈ {online, warning, offline}`.
- `is_night("...T22:00:00Z") is True`, `is_night("...T06:00:00Z") is False` (граница [22,6)).
- Регрессий по существующим тестам b2/t1 нет (`pytest api/tests/unit/test_enrichment.py`).
