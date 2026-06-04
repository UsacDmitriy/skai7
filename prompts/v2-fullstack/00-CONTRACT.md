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
| `cameras[]` | Из `video_files` по алярму: канал 1→«ADAS · Передняя», 5→«DMS · Салон», 2/3→доп. `status="online"` если есть файл с `download_status=downloaded`, иначе `offline`. |
| `telemetry[]` | Из `track_points` по алярму: точки около `ts` → `{ts_offset, speed, ax, ay}`. `ax/ay` нет в данных → `0.0` (TODO-маркер) либо производная скорости. |

Пулы имён/моделей — в `enrichment.py` как константы. Все формулы — чистые функции, покрыты unit-тестами.

---

## 3. REST API (FastAPI, префикс `/api`)

Все ответы — JSON. Ошибки — `{"detail": "..."}` со стандартными HTTP-кодами. CORS открыт для Vite dev (`http://localhost:5173`).

### 3.1 Pydantic-схемы (домен incidents) — контракт ответов

```text
Severity  = "critical" | "high" | "medium" | "low"
Source    = "DMS" | "ADAS" | "TELEMATICS" | "COMBINED"
Status    = "active" | "in_progress" | "validated" | "closed"

Camera        { id: str, label: str, status: "online"|"offline"|"warning", hasVideo: bool }
TelemetryPoint{ ts_offset: int, speed: float, ax: float, ay: float }

IncidentSummary {            # для ленты GET /incidents
  id: str, alarm_type: str, alarm_code: str, alarm_label_ru: str,
  source: Source, severity: Severity, risk_level: Severity, risk_score: int,
  ts: str, vehicle_plate: str, driver: str, vehicle_model: str,
  speed_kmh: float, lat: float|null, lon: float|null, address: str|null,
  video_available: bool, status: Status
}

IncidentDetail extends IncidentSummary {   # для GET /incidents/{id}
  ts_end: str, unit_id: str, unit_name: str, driver_id: str, driver_phone: str,
  speed_limit_kmh: int, is_night: bool, continuous_driving_min: int, events_last_7d: int,
  mileage_km: float, movement_duration: str, video_count: int,
  cam_front_url: str|null, cam_dms_url: str|null,
  evidence_summary: str, cameras: Camera[], telemetry: TelemetryPoint[]
}
```

Форма эталонна `data/mock/incidents.py` — фронт (f2/f3) и бэк (b5) обязаны совпадать пополю.

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

| POST | `/api/actions` | `Action` | тело `{incident_id, action, comment}`; `action ∈ {mark_reviewed, create_task, export_report, request_archive, call_driver}`; пишет в `output/actions.csv`; меняет `status` инцидента в рантайме |
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
