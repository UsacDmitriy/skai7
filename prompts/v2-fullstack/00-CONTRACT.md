# 00 · МАСТЕР-КОНТРАКТ — SKAI Full-Stack v2

> **Единый источник истины** для всех треков (Design ‖ Backend ‖ Frontend). Каждый агент кодит
> **против этого контракта**, а не против рантайма другого трека. Имена таблиц/колонок/полей/
> эндпоинтов/токенов меняются ТОЛЬКО здесь и ТОЛЬКО по согласованию.

## 0. Конвенции (из CLAUDE.md)

- Язык кода/идентификаторов — английский; UI-тексты и комментарии — по необходимости русский.
- Термин **alarm** (не event) в коде и API.
- SQL-идентификаторы (таблицы/колонки) — в **двойных кавычках** (регистр CSV сохраняется: `AlarmId`, `Type`, `UnitStateNumber`).
- Деньги/координаты — числа; временные метки — строки ISO-8601 UTC (как в CSV).

---

## 1. Данные: DuckDB

БД-артефакт: **`data/skai.duckdb`** (в `.gitignore`, пересборка `make db`). Источник — все CSV в `datasets/ready/` + справочник `data/analysis/alarm_types.json`. DuckDB читает CSV напрямую (`read_csv_auto`), большие таблицы (~1M точек) не держим в памяти приложения.

### 1.1 Имена таблиц: `{prefix}__{sanitized_csv}`

CSV без `.csv`, lowercase. Колонки — заголовки CSV **дословно**.

| Папка `datasets/ready/` | Префикс |
|---|---|
| `video_events/*.csv` | `video_events` |
| `video_events/work_rest_single_vehicle/*.csv` | `video_events__wr` |
| `fuel_reconciliation/*.csv` | `fuel` |
| `sensor_diagnostics/*.csv` | `sensors` |
| `navigation_problem_tracks/*.csv` | `navigation` |
| `normal_tracks_zis/*.csv` | `normal_zis` |
| `reference/*.csv` | `reference` |

Коллизии разруливаются префиксом: `video_events__track_points` ≠ `navigation__track_points`.

Ключевые таблицы домена incidents:
`video_events__selected_video_alarms` (54), `video_events__video_files` (94, есть `channel` 1/2/3/5 и `media_relative_path`), `video_events__track_points` (6635), `video_events__track_summary` (54), `video_events__max_speed_points` (80), `video_events__vehicles` (21).

### 1.2 Справочник `alarm_type_catalog`

Из `data/analysis/alarm_types.json` (массив `alarm_types`). Колонки:
`raw, code, label_ru, source, severity, requires_video, auto_request_video`. 14 строк.

### 1.3 View `v_incidents` — контракт колонок (одна строка на алярм, ровно 54)

База: `"video_events__selected_video_alarms"`. JOIN'ы не размножают строки (для `lat/lon`,
`cam_*_url` — подзапрос с выбором одной строки).

| Колонка | Тип | Источник |
|---|---|---|
| `id` | TEXT | `AlarmId` |
| `alarm_type` | TEXT | `Type` (raw) |
| `alarm_code` | TEXT | `alarm_type_catalog.code` (LEFT JOIN raw=Type) |
| `alarm_label_ru` | TEXT | `alarm_type_catalog.label_ru` |
| `source` | TEXT | `alarm_type_catalog.source` |
| `severity` | TEXT | `alarm_type_catalog.severity` |
| `risk_level` | TEXT | = `severity` |
| `ts` | TEXT | `Begin` |
| `ts_end` | TEXT | `End` |
| `vehicle_plate` | TEXT | `UnitStateNumber` |
| `unit_id` | TEXT | `UnitId` |
| `unit_name` | TEXT | `UnitName` |
| `speed_kmh` | REAL | `Speed` |
| `address` | TEXT | `Address` (nullable) |
| `lat` | REAL | первая точка `video_events__track_points` (MIN `point_index`) по `alarm_id=AlarmId` |
| `lon` | REAL | то же, `longitude` |
| `video_count` | INT | `VideoCount` |
| `video_available` | INT | `1` если `VideoCount>0` иначе `0` |
| `cam_dms_url` | TEXT | `media_relative_path` из `video_files` где `channel=5` (MIN) |
| `cam_front_url` | TEXT | `media_relative_path` где `channel=1` (MIN) |
| `mileage_km` | REAL | `track_summary.total_mileage_km` |
| `movement_duration` | TEXT | `track_summary.total_movement_duration` |

> **Колонки обогащения** (`driver`, `driver_id`, `driver_phone`, `vehicle_model`, `risk_score`,
> `speed_limit_kmh`, `is_night`, `continuous_driving_min`, `events_last_7d`, `status`) в `v_incidents`
> **НЕ материализуются** (оставляем расчёт сервису). View отдаёт только «сырое+каталог». Обогащение —
> детерминированно в `api/core/enrichment.py` (см. §2). Это отличие от wave-06 (там были NULL).

---

## 2. Enrichment — детерминированные правила (`api/core/enrichment.py`)

Цель — заполнить поля, которых нет в CSV, **воспроизводимо** (один и тот же вход → один и тот же
выход между запусками). Никакого `random` без seed, никаких `Date.now()`.

| Поле | Правило |
|---|---|
| `lat` / `lon` | Реальные: первая точка `track_points` по алярму (уже в `v_incidents`). |
| `driver` | Детерминированно по `vehicle_plate`: `seed = crc32(plate)`; выбор ФИО из фиксированного пула (≥20 имён). |
| `driver_id` | `"DRV-" + (seed % 9000 + 1000)`. |
| `driver_phone` | `"+7" + 10 цифр` из `seed` (стабильно). |
| `vehicle_model` | Детерминированно по `plate` из пула моделей (ГАЗон NEXT, КамАЗ-5490, Volvo FH, МАЗ-5440, ГАЗель NEXT, …). |
| `speed_limit_kmh` | Эвристика: `90` по умолчанию; если `source=DMS`/городской тип — `60`. Зафиксировать таблицу по `alarm_code`. |
| `is_night` | `True` если час `ts` (UTC) ∈ [22, 06). |
| `continuous_driving_min` | Из `track_summary.total_movement_duration` (парс HH:MM:SS → минуты), иначе `0`. |
| `events_last_7d` | `COUNT(*)` алярмов того же `vehicle_plate` за 7 дней до `ts` (по `selected_video_alarms`). |
| `risk_score` (0–100) | `clamp( 100 * (0.45*sev_w + 0.25*speed_ratio + 0.15*night + 0.15*freq_w) )`, где `sev_w`={critical:1.0, high:0.7, medium:0.45, low:0.2}; `speed_ratio = min(speed_kmh/speed_limit_kmh, 1.5)/1.5`; `night`={1 если is_night иначе 0}; `freq_w = min(events_last_7d/7, 1)`. Округлять до целого. |
| `status` | Дефолт `"active"`. Переопределяется журналом действий (см. §3.4 `/actions`). |
| `evidence_summary` | Шаблон по `alarm_code` (как в `data/mock/incidents.py`), подставляя speed/severity. |
| `cameras[]` | Из `video_files` по алярму. Канон меток: ch1→«ADAS · Фронт», ch5→«DMS · Салон», ch2→«СНЗ · Доп.», ch3→«СНЗ · Кузов». `status="online"` если есть файл `download_status=downloaded`; `"warning"` («Нестабильна») если `download_status=partial`/битый/частичный файл; иначе `"offline"`. Длина массива всегда 3 канонических (ADAS/DMS/СНЗ), отсутствующий → `offline`. |
| `Camera.offline_from/to` | Для `offline`/`warning`: окно недоступности из `sensor_diagnostics`/`video_files.created_at`; если нет — детерминированно по `seed(id)` относительно `ts` (для no-video placeholder). |
| `telemetry[]` | Из `track_points` по алярму: точки около `ts` (±60с) → `{ts_offset, speed, ax, ay}`. **`ax` = производная скорости** `(speed[i]-speed[i-1])/Δt` в м/с² (не `0.0`, иначе график-акселерометр плоский); `ay`=`0.0` (нет данных). |
| `driver_region` / `driver_department` | Из `driver_reference` (§7.1) по `vehicle_plate`. |
| `driver_safety_score` | Из `driver_reference.safety_score`. |
| `confidence` (0–100) | «Уверенность версии события». Источника нет → детерминированно: `70 + seed(id) % 30` (стабильно), но `requires_video=false`/нет видео → −10. |
| `event_version` | Текст основной гипотезы причины по `alarm_code` (как `evidence_summary`, короткая форма) либо `null`. |
| `sensor_active_after_sec` | No-video: сколько секунд DMS-сенсор фиксировал событие после ухода камеры в offline. Из разницы `End`(аларма) и `offline_from`; если нет — `seed(id)%10`. |

Пулы имён/моделей — в `enrichment.py` как константы. Все формулы — чистые функции, покрыты unit-тестами.

---

## 3. REST API (FastAPI, префикс `/api`)

Все ответы — JSON. Ошибки — `{"detail": "..."}` со стандартными HTTP-кодами. CORS открыт для Vite dev (`http://localhost:5173`).

### 3.1 Pydantic-схемы (домен incidents) — контракт ответов

```text
Severity  = "critical" | "high" | "medium" | "low"
Source    = "DMS" | "ADAS" | "TELEMATICS" | "COMBINED"
Status    = "active" | "in_progress" | "validated" | "closed"

Camera        { id: str, label: str, status: "online"|"offline"|"warning", hasVideo: bool,
                offline_from: str|null, offline_to: str|null }   # окна offline для no-video
TelemetryPoint{ ts_offset: int, speed: float, ax: float, ay: float }   # ax = производная скорости (§2)

IncidentSummary {            # для ленты GET /incidents
  id: str, alarm_type: str, alarm_code: str, alarm_label_ru: str,
  source: Source, severity: Severity, risk_level: Severity, risk_score: int,
  ts: str, vehicle_plate: str, driver: str, vehicle_model: str,
  speed_kmh: float, lat: float|null, lon: float|null, address: str|null,
  video_available: bool, status: Status
}

IncidentDetail extends IncidentSummary {   # для GET /incidents/{id}
  ts_end: str, unit_id: str, unit_name: str, driver_id: str, driver_phone: str,
  driver_region: str, driver_department: str, driver_safety_score: int,   # из driver_reference (§7.1)
  speed_limit_kmh: int, is_night: bool, continuous_driving_min: int, events_last_7d: int,
  confidence: int, event_version: str|null,            # «версия события · уверенность %» (enrichment §2)
  sensor_active_after_sec: int|null,                   # no-video: DMS-сенсор работал ещё N сек после offline
  mileage_km: float, movement_duration: str, video_count: int,
  cam_front_url: str|null, cam_dms_url: str|null,
  cam_extra: {channel: int, url: str}[],               # доп. каналы ch2/ch3 для блока «Другие камеры»
  evidence_summary: str, cameras: Camera[], telemetry: TelemetryPoint[]
}
```

Структура (вложенность/набор сущностей) эталонна `data/mock/incidents.py`, но **имена полей — по этому контракту**.
Старый мок использует legacy-имена → канон-маппинг (b5/f3 переименовывают при загрузке):
`score`→`risk_score`, `event_source`→`source`, `alarm_type_label`→`alarm_label_ru`. **Источник истины имён — §3.1, а не мок.**

### 3.2 Эндпоинты — `incidents` (реализуются полностью)

| Метод | Путь | Ответ | Параметры |
|---|---|---|---|
| GET | `/api/incidents` | `IncidentSummary[]` | `severity?`, `source?`, `status?`, `vehicle_plate?`, `limit?=100`, `offset?=0` |
| GET | `/api/incidents/{id}` | `IncidentDetail` | — (404 если нет) |
| GET | `/api/incidents/{id}/telemetry` | `TelemetryPoint[]` | — |
| GET | `/api/incidents/{id}/video/{channel}` | `FileResponse` (mp4) | `channel ∈ {1,2,3,5}` (404/416 если нет файла) |

### 3.3 Эндпоинты — `reports` (P0-частично) и `vehicles`

| GET | `/api/vehicles` | `VehicleSummary[]` | список ТС из `video_events__vehicles` + обогащение driver/model |
| GET | `/api/reports/driver/{plate}` | `DriverReport` | алярмы+метрики по ТС (идея #2, В-1) |
| GET | `/api/reports/fleet` | `FleetReport` | агрегаты по парку (идея #2, В-2) |
| POST | `/api/reports/query` | `DriverReport \| FleetReport` | `{ "text": "Нарушения Иванова за 3 дня" }` — NLU-заглушка: парс по простым правилам, TODO Groq/Whisper |

### 3.4 Эндпоинты — `actions` и stub-домены

| POST | `/api/actions` | `Action` | тело `{incident_id, action, comment}`; `action ∈ {mark_reviewed, create_task, export_report, request_archive, call_driver, notify_hr, validate, stop_vehicle}`; пишет в `output/actions.csv`; меняет `status` инцидента в рантайме |
| GET | `/api/fuel/*`, `/api/sensors/*`, `/api/navigation/*` | `501 Not Implemented` | только роутеры-скелеты + TODO; таблицы в DuckDB уже есть |

---

## 4. Дизайн-токены (для Track D)

Источник — `init/context/DESIGN.md`. Ключевые значения, которые трек D переносит в `tailwind.config` и CSS-переменные:

```text
primary #1E3A8A · primary-dark #1E3070 · primary-50 #EFF6FF
bg #F8FAFC · surface #FFFFFF · text #0F172A · text-muted #64748B · border #E2E8F0
severity: critical #DC2626/#FEE2E2/#991B1B · high #EA580C/#FEF3C7/#B45309
          warning #EAB308/#FEF9C3/#854D0E · ok #16A34A/#DCFCE7/#166534
score-bar fill: linear-gradient(90deg,#16A34A,#EAB308 50%,#DC2626)
font: Inter; numbers tabular-nums; radius 6px (кнопки/карточки), 12px (badge/modal)
spacing base 4px; кнопка h36; иконки Lucide React
```

Маппинг `severity` (из API) → цвет: `critical/high/medium/low`. В DESIGN.md `medium`≈`warning`-палитра? Нет: API severity = `critical|high|medium|low`. Соответствие токенов: `critical→Critical`, `high→High`, `medium→Warning`(жёлтый), `low→OK`(зелёный). Зафиксировать так в d1.

---

## 5. Файлы и владение (без пересечений между агентами)

| Агент | Владеет |
|---|---|
| d1 | `web/tailwind.config.ts`, `web/src/styles/tokens.css` |
| d2 | `web/src/components/ui/*` (Button, SeverityBadge, ScoreBar, Card, VideoPlayer, DataTable, TelemetryChart) |
| d3 | `web/src/components/index.ts`, страница-витрина `web/src/pages/_StyleGuide.tsx` |
| b1 | `api/etl/build_duckdb.py` |
| b2 | `api/core/enrichment.py` |
| b3 | `api/sql/10_v_incidents.sql` |
| b4 | `api/main.py`, `api/core/config.py`, `api/core/duckdb_conn.py`, `api/requirements.txt` |
| b5 | `api/domain/*`, `api/repositories/*`, `api/services/*` |
| b6 | `api/routers/*` |
| f1 | `web/package.json`, `web/vite.config.ts`, `web/index.html`, `web/src/main.tsx`, `web/src/App.tsx`, роутинг |
| f2 | `web/src/api/client.ts`, `web/src/api/types.ts` |
| f3 | `web/src/api/fixtures.ts` |
| f4 | `web/src/pages/IncidentCard.tsx`, `web/src/pages/Monitor.tsx`, `web/src/pages/Report.tsx` |
| x1 | удаление Streamlit; `requirements.txt`, `.gitignore`, `Makefile` |
| x2 | `api/main.py` (include routers), `web/vite.config.ts` (proxy), `Makefile` |
| x3 | только запуск/проверки + `api/tests/*` |

**Интеграция b1↔b3:** `build_duckdb.py` после загрузки таблиц и каталога выполняет все
`api/sql/*.sql` в лексикографическом порядке → view от b3 подхватывается автоматически.


---

## 6. Customer Requirements (из интервью)

> Источник: `context/customer-research.md`

### Acceptance criteria для P0:

**Карточка инцидента (`/incidents/:id`):**
- `video_available=true` → два плеера (cam_front + cam_dms) синхронно
- `video_available=false` → placeholder + `[Запросить архив]`
- TelemetryChart: скорость из `track_points`, маркер t=0
- Блок причины: [😴 Усталость] [📱 Телефон] [🚗 Подрезали] [⚙ Техн. сбой]
- `[📹 Позвонить через камеру]` — три состояния: idle/connecting/active

**Отчёт (`/report`) — killer feature Оздоева:**
- Клик на строку нарушения → VideoPanel справа с правильным видео
- `cam_dms_url` (ch5) для DMS-нарушений, `cam_front_url` (ch1) для ADAS
- NL-запрос → подтверждение → дашборд (4 состояния)

**Монитор (`/monitor`):**
- Ролевой switcher: Логист (только телематика) / Диспетчер / Безопасник
- Одна точка на `unit_id` (не на `AlarmId`) — дедупликация ТС

### Enrichment (нет в реальных данных, mock обязателен):
```python
DRIVER_MOCK = {
    # unit_id → driver info
    # Пока: синтетически по госномеру
}
RISK_SCORE_FORMULA = "severity_weight * speed_factor * night_multiplier"
```

---

## 7. Расширение скоупа: P1/P2 + Voice/NLU + Driver (full-scope v2.1)

> Этот раздел расширяет контракт с P0-домена `incidents` до полного продукта (идеи #1–#10).
> Решения по скоупу: **P0+P1+P2**, **реальная интеграция Voice/NLU и справочника водителей**.
> Базовые §1–§6 остаются в силе; ниже — добавки, не переопределяющие их.

### 7.1 Справочник водителей — `driver_reference` (реальная таблица, не рантайм-mock)

Идентичности водителей нет в исходных датасетах. Заводим **реальную таблицу DuckDB**
`driver_reference`, посеянную детерминированно один раз и **заменяемую** на внешний источник
(RFID/HR-API) без изменения контракта API.

- Артефакт сида: `data/seed/driver_reference.csv` (в git, не генерируется на лету).
- Колонки: `vehicle_plate, unit_id, driver_id, driver_name, driver_phone, department, region, safety_score`.
- **Мульти-водитель на ТС (для В-2 «по ТС», макет требует «основной + другие»):** второй сид
  `data/seed/driver_trips.csv` (`vehicle_plate, driver_id, driver_name, role: "main"|"secondary", trips: int`)
  — детерминированно 1–2 водителя на ТС (основной + опц. второй). `v_vehicle.drivers` строится из него,
  не из `driver_reference` (который остаётся «основной водитель ТС»).
- Генерация сида (скрипт `api/etl/seed_drivers.py`): для каждого уникального `UnitStateNumber`/`UnitId`
  из `video_events__selected_video_alarms` — детерминированно (seed `crc32(plate)`) выбрать ФИО/телефон/
  подразделение/регион из фиксированных пулов (≥20 имён, ≥5 регионов). `safety_score` = 100 − среднего
  `risk_score` алярмов этого ТС.
- В DuckDB грузится как таблица `driver_reference` (b1 подхватывает `data/seed/*.csv` с префиксом `seed`
  → имя `seed__driver_reference`, либо b7 создаёт явно — см. b7).
- `enrichment.driver_for(plate)` (§2) меняется: **сначала** ищет в `driver_reference`, **иначе** падает
  на синтетику по `crc32`. Так «реальный» путь и демо-fallback сосуществуют.

> Замена на внешний источник = только перегенерация `driver_reference.csv` / смена загрузчика b7.
> API-схемы (`driver`, `driver_id`, `driver_phone`) не меняются.

### 7.2 Новые SQL-views (Track B, файлы `api/sql/2x_*.sql`)

| View | Файл | Назначение | Идея |
|---|---|---|---|
| `v_driver_report` | `api/sql/20_v_driver_report.sql` | алярмы+метрики по `vehicle_plate` (агрегаты периода) | #2 В-1 |
| `v_fleet` | `api/sql/21_v_fleet.sql` | агрегаты по парку: по водителям и по ТС | #2 В-2 |
| `v_vehicle` | `api/sql/22_v_vehicle.sql` | карточка ТС: статус камер + список водителей за период (1 ТС = N водителей) | #2 В-2/ТС, #10 |
| `v_sabotage` | `api/sql/23_v_sabotage.sql` | корреляция: алярм `CAMERA_TAMPER`/тёмный DMS-канал + `speed_kmh>0` из `track_points` | #9 |
| `v_reb` | `api/sql/24_v_reb.sql` | разрывы GPS из `navigation__track_periods` (`period_type=3`) + соседние видимые периоды | #8 |

Все view идут поверх таблиц b1; порядок имён (`10_`,`20_`…) гарантирует, что `v_incidents` создаётся первым.

### 7.3 Voice/NLU — реальная интеграция (Track B)

| Слой | Технология | Файл | Контракт |
|---|---|---|---|
| STT | `faster-whisper` `large-v3` (локально, RU/KK/EN) | `api/services/stt_service.py` | `transcribe(wav_bytes, lang?) -> {text, lang, confidence}` |
| NLU | Groq API + LLaMA 3.3 70B (env `GROQ_API_KEY`); fallback — локальный regex | `api/services/nlu_service.py` | `parse(text) -> ReportQuery{kind:"driver"\|"fleet", plate?, driver_name?, period_days?, view?}` |

- Конфиг (`api/core/config.py`): `groq_api_key`, `whisper_model="large-v3"`, `whisper_device="cpu"`.
- `nlu_service.parse` сначала пробует Groq (structured JSON prompt), при ошибке/без ключа — детерминированный
  regex-парсер (ФИО/госномер/«за N дней/дня»). Обе ветки возвращают одну и ту же `ReportQuery`.
- Зависимости (b4 `api/requirements.txt`): `faster-whisper`, `groq`. Тяжёлая модель STT грузится лениво.

### 7.4 Новые эндпоинты (Track B, роутеры b6+)

| Метод | Путь | Ответ | Идея |
|---|---|---|---|
| POST | `/api/reports/transcribe` | `{text, lang, confidence}` | #2 (голос → текст; тело — `multipart/form-data` wav) |
| POST | `/api/reports/query` | `{query: ReportQuery, report: DriverReport\|FleetReport}` | #2 (теперь реальный NLU + отчёт; заменяет заглушку §3.3) |
| GET | `/api/reports/vehicle/{plate}` | `VehicleReport` | #2 В-2/ТС, #10 |
| GET | `/api/tickets` | `Ticket[]` | #6 (читает `output/actions.csv`) |
| GET | `/api/alerts/{id}` | `DispatchAlert` (видео ±15с + телеметрия момента) | #5 |
| GET | `/api/trips/{id}` | `TripDossier` (трек + таймлайн событий) | #7 |
| GET | `/api/reb/{id}` | `RebRecovery` (GPS-разрывы + соседние видеокадры) | #8 |
| GET | `/api/sabotage` | `SabotageEvent[]` (из `v_sabotage`) | #9 |

> `POST /api/reports/query` из §3.3 расширяется: ответ оборачивается в `{query, report}`. fuel/sensors/navigation
> остаются стабами `501` (кроме `navigation`→`/api/reb`, который теперь реализован).

### 7.5 Новые Pydantic-схемы (b5+)

```text
ReportQuery   { kind: "driver"|"fleet", plate?: str, driver_name?: str, period_days?: int=3, view?: "drivers"|"vehicles" }

ReportKPI     { total: int, video_da: int, telematics: int, gross: int }   # всего / ВА видео-детекции / телематика / грубых
ReportPeriod  { from: str, to: str, days: int }
ViolationRow  { id, ts, alarm_code, alarm_label_ru, source: Source, severity: Severity, is_gross: bool }

DriverReport  {                                  # GET /reports/driver/{plate} (идея #2 В-1)
  driver: DriverRef, vehicle_plate: str, vehicle_model: str,
  period: ReportPeriod, mileage_km: float, trips: int,
  kpi: ReportKPI, disciplinary_warning: bool,    # порог: gross>=3 ИЛИ safety_score<60
  violations: ViolationRow[]                      # клик по строке → IncidentDetail (killer-feature)
}

FleetReport   {                                  # GET /reports/fleet (идея #2 В-2)
  period: ReportPeriod, kpi: ReportKPI, vehicles_count: int,
  by_drivers: { driver: DriverRef, vehicle_plate, vehicle_model, mileage_km, risk_score: int, gross: int, total: int }[],
  by_vehicles: { plate, vehicle_model, main_driver: str, mileage_km, risk_score: int, gross: int, total: int, cameras_ok: str }[]  # cameras_ok="2/3"
}

VehicleReport { plate, vehicle_model, risk_score: int, cameras: Camera[],  # GET /reports/vehicle/{plate}, len(cameras)=3
                drivers: DriverRef[], period: ReportPeriod, period_alarms: ViolationRow[], mileage_km, trips: int }
DriverRef     { driver_id, driver_name, role: "main"|"secondary", trips: int, safety_score: int, risk_score: int }
Ticket        { id, created_at, incident_id, action, comment, status: "new"|"in_progress"|"closed" }
DispatchAlert { incident: IncidentDetail, video_window_sec: int=15, requested_at: str }
TripDossier   { vehicle_plate, track: TelemetryPoint[], timeline: {ts_offset, alarm_code, label, has_video}[] }
RebRecovery   { vehicle_plate, gps_track: {lat,lon,ts}[], gap_periods: {start,end,duration_sec}[], video_frames: {ts, channel, url}[] }
SabotageEvent { id, vehicle_plate, ts, dms_dark: bool, speed_kmh: float, driver_name, video_url }
```

> **«Грубые» (gross):** `severity ∈ {critical}` ИЛИ `alarm_code ∈ {OVERSPEED, DMS_SMOKING}` (критическая скорость + курение —
> по интервью Оздоева). Считается в `reports_service` (b10). `is_gross` материализуется в `ViolationRow`.

### 7.6 Дизайн-токены — добавки (Track D, d4/d5)

```text
map: marker severity colors = severity-палитра §4; marker-online #16A34A · marker-offline #94A3B8
     cluster radius 40px; dedup: 1 unit_id = 1 marker (НЕ 1 AlarmId)
voice: idle (primary outline) · recording (critical pulse) · processing (primary spinner)
timeline: track line #1E3A8A; event dot = severity color; t=0 marker critical
roles: Логист 🏭 / Диспетчер 🛡 / Безопасник 🔒 — chip-токены primary-50/primary
leaflet tiles: тёмная тема для /monitor (24/7)
```

### 7.7 Владение новыми файлами (без пересечений)

| Агент | Владеет | Зависит от |
|---|---|---|
| b7 driver-reference | `data/seed/driver_reference.csv`, `api/etl/seed_drivers.py`; правка `enrichment.driver_for` (по согласованию с b2) | b1, §7.1 |
| b8 stt-service | `api/services/stt_service.py` | b4 |
| b9 nlu-service | `api/services/nlu_service.py` | b4 |
| b10 reports-views | `api/sql/20_v_driver_report.sql`, `21_v_fleet.sql`, `22_v_vehicle.sql`; `api/services/reports_service.py` (расширение) | b1, b3, b7, b9 |
| b11 sabotage | `api/sql/23_v_sabotage.sql`, `api/services/sabotage_service.py`, роутер `api/routers/sabotage.py` | b1 |
| b12 reb | `api/sql/24_v_reb.sql`, `api/services/reb_service.py`, роутер `api/routers/reb.py` | b1 |
| b13 tickets+alerts+trips | `api/services/tickets_service.py`, роутеры `tickets.py`/`alerts.py`/`trips.py` | b5, b6 |
| d4 map-primitives | `web/src/components/map/*` (Leaflet MapView, MarkerLayer, RoleToggle) | d1 |
| d5 voice+timeline | `web/src/components/ui/VoiceButton.tsx`, `ConfirmationModal.tsx`, `Timeline.tsx` | d1, d2 |
| f5 events-feed | `web/src/pages/EventsFeed.tsx` | d2, f2 |
| f6 monitor-map | `web/src/pages/Monitor.tsx` (полный, заменяет scaffold f4) | d4, f2 |
| f7 analytics-voice | `web/src/pages/Report.tsx` (полный, заменяет scaffold f4), `web/src/api/voice.ts` | d5, f2 |
| f8 tickets | `web/src/pages/Tickets.tsx` | d2, f2 |
| f9 dispatch-alert | `web/src/pages/DispatchAlert.tsx` (или модал) | d2, f2 |
| f10 trip-dossier | `web/src/pages/TripDossier.tsx` | d4, d5, f2 |
| f11 reb-recovery | `web/src/pages/RebRecovery.tsx` | d4, f2 |
| f12 sabotage | `web/src/components/SabotageWidget.tsx` + секция в Report/Monitor | d2, f2 |
| f13 role-toggle | интеграция `RoleToggle` (d4) в EventsFeed/Monitor; фильтрация по роли | d4, f5, f6 |

> `f6`/`f7` **заменяют** scaffold-версии `Monitor.tsx`/`Report.tsx` из f4. После full-scope f4 владеет
> только `IncidentCard.tsx`; Monitor/Report переходят к f6/f7. Зафиксировать при запуске Волны 3.

### 7.8 Acceptance criteria — P1/P2

**Лента событий (`/`, идея #4):** badge источника `[📹/⚡/⚡📹]`, фильтр «Нет видео», ролевой switcher, поиск по plate/ФИО, клик→карточка.
**Монитор (`/monitor`, идея #4/#10):** Leaflet, 1 `unit_id` = 1 маркер, цвет по severity, ролевой режим (Логист — без DMS-алармов), тёмная тема.
**Отчёт (`/report`, идея #2):** 🎤 → `transcribe` → текст → `query` → подтверждающее окно (`ConfirmationModal`) → дашборд В-1/В-2; клик по нарушению → видео справа.
**Tickets (`/tickets`, идея #6):** таблица из `output/actions.csv`, фильтры по типу/статусу/дате.
**Dispatch alert (идея #5):** при `auto_request_video=true` алярме — модал с видео ±15с + 3 кнопки.
**Видеодосье (`/trip/:id`, идея #7):** трек + таймлайн событий, клик по точке → видео момента.
**РЭБ (`/reb/:id`, идея #8):** GPS-трек с разрывами + соседние видеокадры; данные из `navigation_problem_tracks`.
**Саботаж (идея #9):** список `v_sabotage` (тёмный DMS + speed>0), кнопки «Заявка»/«HR».
**Карта по ролям (идея #10):** переключатель роли скрывает/показывает слои; дедупликация ТС.
