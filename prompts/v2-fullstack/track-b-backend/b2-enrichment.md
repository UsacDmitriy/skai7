# b2 · Enrichment — детерминированное обогащение

> Трек **Backend/Data**. Против `00-CONTRACT.md` §2. **Владеет:** `api/core/enrichment.py`.
> Параллельно с b1/b3/b4 (чистые функции, без БД).

## Цель

Чистый модуль детерминированных функций, заполняющих поля, которых нет в CSV. Один вход → один
выход между запусками (seed по госномеру, без `random`/`datetime.now`).

## Функции (сигнатуры)

```python
def driver_for(plate: str) -> str            # ФИО из пула ≥20 по seed=zlib.crc32(plate)
def driver_id_for(plate: str) -> str         # "DRV-XXXX"
def driver_phone_for(plate: str) -> str      # "+7XXXXXXXXXX"
def vehicle_model_for(plate: str) -> str     # из пула моделей по seed
def speed_limit_for(alarm_code: str) -> int  # таблица по коду; дефолт 90, городские/DMS → 60
def is_night(ts_iso: str) -> bool            # час UTC в [22,6)
def continuous_driving_min(movement_duration: str | None) -> int  # парс "HH:MM:SS" → минуты
def risk_score(severity: str, speed_kmh: float, speed_limit_kmh: int,
               is_night: bool, events_last_7d: int) -> int  # формула из §2, 0..100
def evidence_summary(alarm_code: str, speed_kmh: float, severity: str) -> str  # шаблон по коду
def cameras_from_videofiles(rows: list[dict]) -> list[dict]   # Camera[] из строк video_files
def telemetry_from_trackpoints(rows: list[dict], event_ts_iso: str) -> list[dict]  # TelemetryPoint[]
```

## Правила (точно по §2 контракта)

- Пулы `_DRIVER_NAMES`, `_VEHICLE_MODELS` — модульные константы (взять стиль из `data/mock/incidents.py`).
- `risk_score`: `sev_w={critical:1.0,high:0.7,medium:0.45,low:0.2}`; `speed_ratio=min(speed/limit,1.5)/1.5`; итог `round(100*(0.45*sev_w+0.25*speed_ratio+0.15*night+0.15*min(events/7,1)))`, clamp 0..100.
- `cameras_from_videofiles`: канал `1`→«ADAS · Передняя», `5`→«DMS · Салон», `2/3`→«CH{n} · доп.»; `status="online"` если `download_status=="downloaded"`, иначе `"offline"`; `hasVideo` соответственно.
- `telemetry_from_trackpoints`: выбрать точки в окне ±60с вокруг `event_ts`, посчитать `ts_offset` (сек), `speed=speed_kmh`; `ax/ay` нет в данных → производная скорости по времени для `ax` (Δspeed/Δt в м/с²), `ay=0.0`; пометить `# TODO: реальный акселерометр отсутствует в датасете`.

## Тесты (`api/tests/test_enrichment.py` — допускается создать здесь)

- Детерминизм: `driver_for("Т780РН198")` стабилен между вызовами.
- `risk_score(critical,107,90,True,5)` > `risk_score(low,30,90,False,0)`; оба в [0,100].
- `is_night("2026-05-14T23:37:22Z") is True`; `is_night("2026-05-15T10:15:00Z") is False`.

## Edge cases / поведение

- `risk_score`: результат всегда ∈ [0,100] (clamp); монотонен по severity при равных прочих — `critical ≥ high ≥ medium ≥ low`.
- `speed_limit_for(неизвестный alarm_code)` → дефолт `90` (не NULL, не исключение); городские/DMS-коды → `60`.
- `cameras_from_videofiles`: длина ровно `3` (каналы 1/5 + один доп.); каждая камера имеет `status ∈ {online, warning, offline}`; нет видео по каналу → `status="offline"`, `hasVideo=false`, `url=null` (не выпадаем).
- `is_night`, `speed_limit_for`, `ax` (Δspeed/Δt) детерминированы: один вход → один выход; без `random`/`datetime.now`.

## Check

- `python -c "from api.core import enrichment"` без ошибок.
- Все функции — чистые (нет I/O, нет глобального состояния, нет недетерминизма).
- `risk_score` clamp в [0,100] на крайних входах (speed=0, events=0 и speed≫limit, events≫7); монотонность по severity при фиксированных speed/limit/night/events.
- `speed_limit_for("__UNKNOWN__")` → `90` (label/severity по неизвестному коду — дефолтные, без NULL).
- `cameras_from_videofiles([])` → 3 камеры со `status="offline"`/`hasVideo=false`; при отсутствии видеоканала `confidence` инцидента −10 (нет видео).
- `cameras` всегда длины 3, каждый `status ∈ {online, warning, offline}`.
- `is_night("...T22:00:00Z") is True`, `is_night("...T06:00:00Z") is False` (граница [22,6)).
