# 00 · МАСТЕР-КОНТРАКТ — SKAI Full-Stack v2

> **Статус: 🔒 FROZEN (Барьер 0) · 2026-06-04.** Контракт заморожен — это единственный источник
> истины для всех треков. Поля, схемы (§3.1/§7.5), эндпоинты и токены зафиксированы; до разморозки
> треки кодят строго против этих определений. **Любое изменение — только по явному согласованию**
> (PR с пометкой `contract-change`, апдейт даты заморозки) и с синхронной правкой зависимых промптов.
>
> **Единый источник истины** для всех треков (Design ‖ Backend ‖ Frontend). Каждый агент кодит
> **против этого контракта**, а не против рантайма другого трека. Имена таблиц/колонок/полей/
> эндпоинтов/токенов меняются ТОЛЬКО здесь и ТОЛЬКО по согласованию.

> **Changelog (contract-change):**
> - **2026-06-04 · #1 (синхронизация с макетами 07 Заявки):**
>   (a) В `Source` (§3.1) добавлено значение `"DIAGNOSTIC"` — для алярмов сенсорной диагностики
>   («Камера офлайн» и т.п., источник `sensor_diagnostics` / `alarm_type_catalog.source`), бейдж «⚙ Диагностика».
>       DIAGNOSTIC присутствует в `alarm_type_catalog` (тип `CameraOffline`/`CAMERA_OFFLINE`, w3-2), но в демо-датасете
>       нет живого алярма этого типа (`v_incidents` остаётся ровно 54) — бейдж проводной, но в демо неактивный, это не баг.
>   (b) `Ticket.status` (§7.5) приведён к единому enum `Status` (§3.1) `active|in_progress|validated|closed`
>   вместо прежнего `new|in_progress|closed`; «Просрочена» больше **не статус** — добавлены производные
>   поля `deadline` и `is_overdue`. Синхронно поправлен промпт `prompts/claude-design/07-tickets-screen`.
> - **2026-06-05 · #2 (Волна 3 — раскрытие тёмных данных, аддендум §9):** домены `fuel`/`sensors`
>   повышены из `501`-стабов до реальных эндпоинтов; `navigation` получает list-эндпоинт, ведущий в
>   существующий `/api/reb/{id}`. Добавлен экран «Здоровье парка» (`/fleet-health`) на объединении ТС.
>   Изменение **аддитивное**: §1–§8 не трогаются, новые контракты живут в **§9** (не FROZEN).
>   Отменяет строку §7.4 «fuel/sensors/navigation остаются стабами 501» в части `fuel`/`sensors`/`navigation-list`.

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
`video_events__selected_video_alarms` (55 = 54 видео-алярма + 1 seeded no-video, w3-5), `video_events__video_files` (94, есть `channel` 1/2/3/5 и `media_relative_path`), `video_events__track_points` (6635), `video_events__track_summary` (54), `video_events__max_speed_points` (80), `video_events__vehicles` (21).

### 1.2 Справочник `alarm_type_catalog`

Из `data/analysis/alarm_types.json` (массив `alarm_types`). Колонки:
`raw, code, label_ru, source, severity, requires_video, auto_request_video`. 14 строк.

### 1.3 View `v_incidents` — контракт колонок (одна строка на алярм, 55)

База: `"video_events__selected_video_alarms"`. JOIN'ы не размножают строки (для `lat/lon`,
`cam_*_url` — подзапрос с выбором одной строки).

> **No-video инцидент (w3-5).** P0-набор содержит **≥1 строку с `video_available=0`** (`SELECT
> video_available, count(*) FROM v_incidents GROUP BY 1` → есть `(0, ≥1)`). Это детерминированный
> seed-алярм `CAMERA_TAMPER` (`Type=Sabotage`, `VideoCount=0`, без `video_files`): саботаж DMS-камеры —
> естественный кейс «видео нет». Делает достижимой ветку empty-state + «Запросить архив» и поля §2,
> действующие только для no-video (`sensor_active_after_sec`, `cam_*_url=null`, 3 камеры → `offline`).
> В Волне 2 к ним добавятся no-video инциденты из невидеосорсов (саботаж/РЭБ/диагностика) через UNION.

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
Source    = "DMS" | "ADAS" | "TELEMATICS" | "COMBINED" | "DIAGNOSTIC"   # DIAGNOSTIC — алярмы сенсорной диагностики (камера офлайн и т.п.), бейдж «⚙ Диагностика»
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
- `video_available=true` → два плеера (cam_front + cam_dms) **синхронны** (общий play/seek)
- `video_available=false` → placeholder + `[Запросить архив]`
- TelemetryChart: скорость из `track_points`, статичный маркер события t=0 **+ движущийся `playheadOffset`**,
  идущий за `currentTime` видео (idea #1 «маркер двигается вместе с видео»); клик по графику перематывает видео
- Блок причины: [😴 Усталость] [📱 Телефон] [🚗 Подрезали] [⚙ Техн. сбой]
- `[📹 Позвонить через камеру]` — три состояния: idle/connecting/active

**Отчёт (`/report`) — killer feature Оздоева:**
- Клик на строку нарушения → VideoPanel справа с правильным видео
- `cam_dms_url` (ch5) для DMS-нарушений, `cam_front_url` (ch1) для ADAS
- NL-запрос → подтверждение → дашборд (4 состояния)

> **Правило воспроизведения видео (анти-регресс DEF-3, barrier-1 smoke x3).**
> Поля `cam_dms_url` / `cam_front_url` / `cam_extra[].url` — это `media_relative_path` из БД
> (пути относительно корня проекта), они **НЕ являются URL для `<video src>`** и служат только
> двум целям: (1) индикатор наличия видео (non-null ⇒ канал есть), (2) выбор канала
> (DMS→5, ADAS→1). Источник для плеера — **всегда** API-эндпоинт `GET /api/incidents/{id}/video/{channel}`
> через `client.videoUrl(id, channel)` (f2). Шаблон: `src = inc.cam_dms_url ? client.videoUrl(inc.id, 5) : undefined`.
> Прямой биндинг `src={cam_dms_url}` ломает воспроизведение (относительный путь → 404). Касается f4, f7 и любого нового экрана с видео.

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
  violations: ViolationRow[],                     # клик по строке → IncidentDetail (killer-feature)
  narrative: str|null                             # b22 (Волна 4.2): связный текст-нарратив; null до Волны 4
}

FleetReport   {                                  # GET /reports/fleet (идея #2 В-2)
  period: ReportPeriod, kpi: ReportKPI, vehicles_count: int,
  by_drivers: { driver: DriverRef, vehicle_plate, vehicle_model, mileage_km, risk_score: int, gross: int, total: int }[],
  by_vehicles: { plate, vehicle_model, main_driver: str, mileage_km, risk_score: int, gross: int, total: int, cameras_ok: str }[],  # cameras_ok="2/3"
  narrative: str|null                             # b22 (Волна 4.2): связный текст-нарратив; null до Волны 4
}

VehicleReport { plate, vehicle_model, risk_score: int, cameras: Camera[],  # GET /reports/vehicle/{plate}, len(cameras)=3
                drivers: DriverRef[], period: ReportPeriod, period_alarms: ViolationRow[], mileage_km, trips: int }
DriverRef     { driver_id, driver_name, role: "main"|"secondary", trips: int, safety_score: int, risk_score: int }
Ticket        { id, created_at, incident_id, action, comment, status: Status,   # единый enum Status (§3.1): active|in_progress|validated|closed
                deadline: str|null, is_overdue: bool }   # is_overdue = deadline<now И status∉{closed}; «Просрочена» — не статус, а оверлей по is_overdue
                # RU-метки: active=«Новая» · in_progress=«В работе» · validated=«Проверена» · closed=«Закрыта»
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
> только `IncidentCard.tsx`; Monitor/Report переходят к f6/f7. Зафиксировать при запуске Волны 2 (расширение).

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

## 8. AI-слой (Волна 4) — умное событие, прогнозы, копилот (идеи #11–#16)

> Новый слой поверх готового P0/P1/P2. **Офлайн/детерминизм:** VLM и внешние API гоняются батчем
> **оффлайн один раз** по 54 алярмам, результат — в DuckDB-таблицы + `web/src/api/fixtures.ts`.
> Рантайм читает **кэш**; нет сети/ключей ⇒ кэш/детерминированный фолбэк (как `nlu_service`).
> Без `Date.now()`/`random` в логике.

### 8.0 Реальность данных (определяет фолбэки — проверено по `selected_video_alarms`)

54 алярма распределены всего по **2 различным дням** (2026-05-14: 32, 2026-05-18: 22), и лишь **2 из 21 ТС**
имеют события более чем в один день. Прямое следствие для AI-слоя:

- **`b18` (прогноз риска) — детерминированный fallback ОБЯЗАТЕЛЕН, без ARIMA/IsolationForest**: временного
  ряда на водителя нет. `RiskForecast` строится наивным базлайном (по `events_last_7d`) + статический
  коридор `ci_low/ci_high`; `anomaly=false`, `anomaly_reason="недостаточно истории"`. Тег b18 остаётся 🔴
  (детерминизм/коридор), но ML-ветка — мёртвая на этих данных (включается только при доливке данных).
- **`b20` (цепочки усталости) — честный empty/sparse-state**: Drowsiness=15, Yawning=3, но почти всегда
  разные ТС/дни → цепочек `YAWNING→DROWSY→harsh` в окне почти нет. Возвращать `[]`/одиночный «ранний
  признак», не выдумывать связи. Тест проверяет, что пустой набор — валиден (не падение).
- **`b16`/`b17` (сцена/погода)** — оффлайн-предрасчёт; при отсутствии кэша → детерминированный фолбэк
  (`day_night` из часа `ts`, `weather="unknown"`, `bonus=0`); кэш-каркас готовится в Волне 3 (`w3-16`).

### 8.1 Таблицы (предрасчёт → кэш)

- **`incident_scene`** (1 строка на алярм): `id`, `weather ∈ {clear,rain,snow,fog}`,
  `day_night ∈ {day,twilight,night}`, `road_surface ∈ {dry,wet,snow,ice,unknown}`,
  `area ∈ {urban,highway,unknown}`, `visibility ∈ {good,moderate,poor}`, `scene_confidence` (0..1),
  `source ∈ {vlm,cache}`. Источник — `api/etl/scene_precompute.py` (VLM по кадру ch1/ch5), кэш
  `data/ai/scene_labels.json`. SQL: `api/sql/30_incident_scene.sql`.
- **`incident_weather`** (1 строка на алярм): `id`, `ts`, `lat`, `lon`, `api_weather`, `api_precip_mm`,
  `api_visibility_m`, `is_day` (bool, по solar elevation), `solar_elevation_deg`, `discrepancy` (bool),
  `discrepancy_kind ∈ {weather,daynight,none}`. Источник — Open-Meteo historical + sunrise-sunset,
  кэш `data/ai/weather_cache.json`.
- **`v_risk_zones`** (view, кластеры): `zone_id`, `centroid_lat`, `centroid_lon`, `radius_m`,
  `alarm_count`, `avg_risk`, `top_alarm_code`, `peak_hour` (0..23), `kind ∈ {incident,reb}`.
  DBSCAN по `lat/lon` из `v_incidents` + РЭБ-зоны из `navigation__track_periods` (`period_type=3`).

### 8.2 Enrichment-расширение (`api/core/enrichment.py`)

`risk_score` получает погодно-сценовую надбавку: `wet/ice/poor-visibility/night` ⇒ детерминированный
множитель из `incident_weather`/`incident_scene`. **Обратная совместимость:** без кэша — прежнее поведение.

### 8.3 Эндпоинты

- `GET /api/incidents/{id}/scene` → `SceneContext` + `WeatherCrossCheck`.
- `GET /api/reports/forecast/{plate}` → `RiskForecast`.
- `GET /api/zones?kind=&hour=` → `RiskZone[]`.
- `GET /api/fatigue?plate=` → `FatigueChain[]`.
- `POST /api/copilot/chat` → `CopilotMessage` (LLM tool-use, Groq + детерминированный фолбэк).
- `GET /api/incidents/{id}/risk-breakdown` → `RiskBreakdown` (§8.8, explainability; детерм. из enrichment) — Волна 4.3.
- `GET /api/metrics/ai` → `AiMetrics`; `GET /api/metrics/data-quality` → `DataQuality` (§8.7) — Волна 4.3.

> Полный список AI-эндпоинтов: scene/forecast/zones/fatigue/copilot (4.1/4.2) + risk-breakdown/metrics (4.3).
> Роутеры `forecast`/`zones`/`fatigue`/`copilot`/`metrics` регистрируются в `ALL_ROUTERS` (или авто-discovery).

### 8.4 Схемы (Pydantic / TS types, §3.1-стиль)

- `SceneContext { id, weather, day_night, road_surface, area, visibility, scene_confidence }`
- `WeatherCrossCheck { id, api_weather, is_day, solar_elevation_deg, discrepancy, discrepancy_kind }`
- `RiskForecast { plate, trend: {date, predicted_events, ci_low, ci_high}[], anomaly: bool, anomaly_reason?, recommendations: string[], narrative?: str }`  # narrative — b22 (Волна 4.2)
- `RiskZone { zone_id, centroid: [lat,lon], radius_m, alarm_count, avg_risk, top_alarm_code, peak_hour, kind }`
- `FatigueChain { plate, trip_id?, events: {code, ts}[], window_min, severity }`
- `CopilotMessage { role: 'user'|'assistant', text, lang: 'ru'|'en', tool_calls?: {name,args}[], data? }`

### 8.5 Владение (без пересечений)

Новые файлы: `api/etl/scene_precompute.py`, `api/sql/30_incident_scene.sql`, `api/services/forecast_service.py`,
`api/services/zones_service.py`, `api/services/copilot_service.py`, `web/src/components/ai/*`,
`data/ai/*.json`. Правки `enrichment.py`/`v_sabotage`/`Report.tsx`/`IncidentCard.tsx`/`Monitor.tsx` —
строго аддитивные, против этого §8.

**Владение Ops & Trust (Волна 4.3) + governance (4.1):**

| Промпт | Владеет | Волна |
|---|---|---|
| b24 | `api/core/ai_flags.py`, `api/core/ai_runtime.py`; мета `AiFeatureState` в AI-ответах | 4.1 |
| b25 | `api/services/metrics_service.py`, роутер `api/routers/metrics.py`; пишет в `ai_metric_events` | 4.3 |
| b26 | `api/core/security.py`, `api/core/audit.py`, `docs/SLO.md`; middleware-регистрация в `api/main.py` | 4.3 |
| f20 | `web/src/components/ai/RiskWaterfall.tsx`; аддит. правки `IncidentCard.tsx`/`Report.tsx` | 4.3 |
| f21 | `web/src/pages/Metrics.tsx`, `web/src/components/ai/DataQualityPanel.tsx`; маршрут `/metrics` | 4.3 |
| t5 | `CURRENT_STATUS.md`, `scripts/gen_status.py` | 4.3 |
| t6 | `.github/workflows/ci.yml`, `.github/workflows/nightly-smoke.yml` | 4.3 |

> **Каркас под эти файлы готовит Волна 3** (`wave-3-backlog/` w3-16…w3-19): `data/ai/` + кэш-схема +
> placeholder, `api/sql/33_ai_metric_events.sql` (пустой DDL), AI-типы/клиент/фикстуры (§8.4/§8.7/§8.8),
> маршруты `/copilot`+`/metrics` + пункты меню, каркас `.github/workflows/` + `scripts/gen_status.py`.
> Промпты Волны 4 **дополняют** этот каркас логикой, не пересоздают его (избегаем кросс-трек конфликта).

### 8.6 Runtime-governance AI (по второму research-отчёту)

Чтобы AI-слой не стал непрозрачным, вводится управляемость:

- **Feature-flags** на каждую AI-фичу (`scene`, `forecast`, `zones`, `fatigue`, `copilot`, `verdict`):
  конфиг `api/core/ai_flags.py` + env; выкл → эндпоинт отдаёт «feature disabled» (не падение), UI скрывает блок.
- **Latency-budget** на запрос (per-feature, мс) + **offline-cache policy/TTL** (кэш `data/ai/*`): нет сети/
  превышен бюджет → отдать кэш/деградировать, не блокировать UI. Контракт деградации единый (как `nlu`).
- Схема `AiFeatureState { name, enabled, source: 'live'|'cache'|'fallback', latency_ms }` в мете AI-ответов.

### 8.7 Измеримость: метрики и качество данных

- `GET /api/metrics/ai` → `AiMetrics` — KPI AI-слоя: `recommendation_acceptance`, `copilot_tool_success`,
  `weather_mismatch_rate`, `zone_hit_rate`, `avg_time_to_triage`, `forecast_coverage`. Источник —
  событийная таблица `ai_metric_events` (аддитивно; пишется эндпоинтами/UI).
- `GET /api/metrics/data-quality` → `DataQuality` — `camera_offline_ratio`, `missing_gps_ratio`,
  `missing_media_ratio`, `weather_mismatch_rate`, `incidents_with_video_ratio`.

### 8.8 Explainability: декомпозиция риска

- `GET /api/incidents/{id}/risk-breakdown` → `RiskBreakdown` — вклад каждого слагаемого `risk_score`
  (§2): `{ severity_w, speed_ratio, night, freq_w, weather_bonus }` + итог; для waterfall-визуализации.
  Чисто детерминированно из enrichment (без ML), зеркалит формулу §2/§8.2.

### 8.9 Hardening-трек (foundation, параллельно AI)

- **Единый источник истины** `CURRENT_STATUS.md` (авто/полу-авто из тестов+контракта): «реализовано vs
  план» — против дрейфа README↔RUNBOOK↔contract.
- **Remote CI** (`.github/workflows/*`) зеркалит `scripts/check.sh` (lint/typecheck/test) + **nightly smoke
  на ЖИВОМ API** (fixtures маскируют backend-регресс).
- **Security baseline** (демо-уровень, аддитивно): bearer/API-key scaffold, **audit-trail** действий,
  rate-limit/throttle на тяжёлые эндпоинты (STT/copilot), документ SLO/SLA. Без ломки текущих эндпоинтов.

## 9. Волна 3 — раскрытие тёмных данных (fuel / sensors / navigation) · аддендум

> **Аддендум (не FROZEN), 2026-06-05 (contract-change #2).** Цель — целостность MVP: данные, уже
> загруженные в `data/skai.duckdb` (`fuel__*`, `sensors__*`, `navigation__*`), перестают быть «мёртвым
> грузом» и получают экраны + кросс-связи. §1–§8 не трогаются; всё новое — здесь. Эндпоинты `fuel`/
> `sensors` повышены из `501`-стабов; `navigation` получает list-эндпоинт, ведущий в существующий
> `/api/reb/{id}` (§7.4). Детерминизм как везде: без `Date.now()`/`random` в логике.

### 9.0 Принцип покрытия (disjoint-популяции ТС)

Популяции ТС по доменам почти не пересекаются (проверено по БД, госномера нормализованы — без
пробелов/регистра): **fuel = 10 ТС (пересечение с видеопарком 0)**, **sensors = 7**, **navigation = 5**,
объединение = **17 ТС, из них только 2 в видеопарке** (`О802УЕ198`, `С725АТ159`). Это отражает реальный
фрагментированный телематический парк заказчика, а не баг.

- Хаб «Здоровье парка» строится на **объединении** ТС: sensors/navigation резолвятся через
  `reference__vehicle_matches` (`source_list ∈ {sensors_bv, navigation_problem}`, поле `public_state_number`),
  топливо — по собственному ключу `fuel__fuel_vehicles.vehicle_id` (**в `reference__vehicle_matches` топлива нет**).
- Отсутствующий у ТС домен рендерится «—» (не ошибка). Баннер покрытия обязателен: «Топливо:10 · Сенсоры:7 · Навигация:5 · в видеопарке:2».
- **Не обещать кросс-связи там, где нет общих ТС**: топливо ↔ инцидент/водитель/РЭБ не линкуется (0 пересечения).

### 9.1 Эндпоинты (Track B, заменяют стабы `fuel`/`sensors`/`navigation`)

| Метод | Путь | Ответ | Идея |
|---|---|---|---|
| GET | `/api/fuel` | `FuelVehicleSummary[]` (10) | Топливная сверка ЗИС vs карты |
| GET | `/api/fuel/{plate}` | `FuelVehicleCard` (404 при неизв. ТС) | Карточка топлива ТС |
| GET | `/api/sensors` | `SensorVehicleSummary[]` (7) | Сенсорная диагностика (CAN−GPS) |
| GET | `/api/sensors/{plate}` | `SensorVehicleCard` (404) | Карточка сенсоров ТС |
| GET | `/api/navigation` | `NavProblemVehicle[]` (5–6) | Список проблемных треков → РЭБ |
| GET | `/api/navigation/{plate}` | `NavProblemVehicle` (404) | Сводка ТС (deep-view = `/api/reb/{id}`) |

> `/api/reb/{id}` (§7.4) **уже реализован** — `/api/navigation` это **список-вход** к нему.
> Госномера матчатся с нормализацией (strip пробелов/регистра), чтобы `/api/fuel/А144ЕВ193` работал из UI.

### 9.2 Pydantic-схемы (b-сервисы; §3.1/§7.5-стиль, провенанс колонок указан)

```text
# fuel (из fuel__fuel_vehicles / fuel__fuel_summary / fuel__fuel_reconciliation / fuel__fuel_events)
FuelVehicleSummary { vehicle_id: str, model: str, vin: str,
  fuel_volume_zis_l: float, fuel_volume_card_l: float, volume_delta_zis_minus_card_l: float,  # headline KPI
  refuel_count_zis: int, transaction_count_card: int, period_start: str, period_end: str,
  recon_status: "matched"|"review"|"missing_sensor_event" }   # худший статус сверки по ТС
FuelReconRow { row_id: str, transaction_ts: str|null, event_ts: str|null,
  transaction_volume_l: float|null, sensor_volume_l: float|null, volume_delta_l: float|null,
  time_delta_min: float|null, amount_rub: float|null, status: str, reason: str|null }
FuelEvent { event_id: str, event_ts: str, event_name: str, volume_l: float,
  before_l: float|null, after_l: float|null, lat: float|null, lon: float|null, address: str|null }
FuelVehicleCard extends FuelVehicleSummary {
  summary: { fuel_spent_l, total_mileage_km, average_consumption_l_per_100km, average_speed_kmh,
             fuelings_count, defuelings_count },        # fuel__fuel_summary
  reconciliation: FuelReconRow[], events: FuelEvent[] }

# sensors (из sensors__mileage_and_speed / online_snapshot / daily_mileage / engine_statistics / fuel_level_summary / sensor_catalog)
SensorVehicleSummary { public_unit_id: str, vehicle_label: str, plate: str|null,
  gps_total_distance_km: float, distance_odometer_km: float,
  distance_gap_odometer_minus_gps_km: float|null,       # CAN−GPS KPI (может быть null → «нет данных»)
  max_speed_kmh: float, average_speed_kmh: float, satellite_amount: int,
  online_status: "online"|"stale"|"offline", sensor_count: int }
SensorDailyPoint { date: str, distance_km: float }       # ровно 7/ТС → спарклайн (НЕ 959k graph_points)
SensorVehicleCard extends SensorVehicleSummary {
  daily_mileage: SensorDailyPoint[],
  engine: { first_ignition_on, last_ignition_off, ignition_duration, idle_duration },
  fuel_level: { first_fuel_level, last_fuel_level, delta_fuel_level },
  snapshot: { speed_kmh, fuel_volume, satellite_amount, timestamp_utc,
              last_valid_navigation_timestamp, odometer_mileage, longitude, latitude } }

# navigation (из navigation__navigation_problem_vehicles / navigation__track_periods)
NavProblemVehicle { public_unit_id: str|null, plate: str|null, vehicle_label: str|null, brand: str|null,
  problem_description: str,                              # человеческая «история» проблемы (free text)
  match_status: "matched"|"unmatched",
  gap_count: int, total_periods: int, total_gap_duration_sec: int,   # gap = period_type=3
  reb_link_id: str|null,                                 # = public_unit_id (UUID есть в обеих таблицах); null у unmatched
  in_video_fleet: bool }                                 # plate ∈ v_incidents.vehicle_plate (норм.)
```

### 9.3 SQL-views (Track B, файлы `api/sql/2x_*.sql`, идемпотентный `DROP VIEW IF EXISTS`)

- `25_v_fuel.sql` — `v_fuel` = `fuel__fuel_vehicles` ⋈ агрегат `fuel__fuel_reconciliation` по `vehicle_id`
  (`recon_status` = худший: `missing_sensor_event` > `review` > `matched`). Списки `reconciliation`/`events`
  сервис читает по `vehicle_id` напрямую (во view не материализуются).
- `26_v_sensors.sql` — `v_sensors` = `sensors__mileage_and_speed` ⋈ `online_snapshot` ⋈ count(`sensor_catalog`)
  по `public_unit_id`, LEFT JOIN `reference__vehicle_matches` (`source_list='sensors_bv'`) → `plate`.
  **959k `sensors__graph_points` и `graph_status` не отдаются.** `online_status`: сравнение
  `last_valid_navigation_timestamp` с `timestamp_utc` строки (не с `Date.now()`); NULL → `stale`.
- `27_v_nav_problem.sql` — `v_nav_problem` = `navigation__navigation_problem_vehicles` LEFT JOIN агрегат
  `navigation__track_periods` по `public_unit_id` (`gap_count`/`total_gap_duration_sec` по `period_type=3`,
  парс `HH:MM:SS` как в `24_v_reb.sql`). **`reb_link_id = public_unit_id`** (т.к. `track_periods.vehicle_id`
  хранит «грязный» лейбл `С725АТ159(ТМ)` ≠ чистый `public_state_number`).
- `28_v_fleet_health.sql` — `v_fleet_health` = объединение ТС по нормализованному госномеру:
  fuel (own-key) ∪ sensors/navigation (через `reference__vehicle_matches`), с флагами наличия по доменам.

### 9.4 Frontend (Track F; `VITE_USE_FIXTURES=true` обязателен для каждого экрана)

- **Роуты** (`web/src/App.tsx`, внутри `AppShell`): `/fleet-health` (хаб-ростер), `/fleet-health/fuel/:plate`,
  `/fleet-health/sensors/:plate`, `/navigation` (список проблем→`/reb/:id`). `/reb/:id` и `/trip/:id` уже есть.
- **API-слой** (f2/f3): `types.ts` (+`FuelVehicle*`/`SensorVehicle*`/`NavProblemVehicle`), `client.ts`
  (`listFuel/getFuel/listSensors/getSensors/listNavProblems` с fixtures-веткой; **починить отсутствующую
  fixtures-ветку `getReb`/`getVehicleReport`**), `fixtures.ts` (2–3 реальные строки на домен).
- **Хаб «Здоровье парка»**: таблица «одна строка = одно ТС объединения», KPI-колонки (топливо Δ ЗИС−карта;
  пробег CAN−GPS; сенсоры online; навигация gap-бейдж→`/reb/:id`), «—» для отсутствующих доменов, баннер покрытия.
  Клик по строке → самый «богатый» доступный домен (fuel → sensor → REB).
- **Кросс-врезки (целостность, аддитивно — killer-features не ломать):**
  - `IncidentCard.tsx`: «Показать маршрут поездки»→`/trip/${inc.id}` (`trip_id==incident_id`);
    блок «Связанные заявки» (`getTickets().filter(t.incident_id===inc.id)`→`/tickets`); при `create_task` —
    ссылка «Открыть в Заявках».
  - `TripDossier.tsx`: бэк-ссылка «К карточке инцидента»→`/incidents/${id}`.
  - `Report.tsx`: строка нарушения — доп. ссылка→`/incidents/${id}` (инлайн-видео сохранить); строки
    fleet-отчёта — drill в `DriverReport`/фильтрованную ленту.
  - `EventsFeed.tsx`: иконка-экшен в строке→`/trip/${row.id}` (`stopPropagation`).
- **Сигнпостинг**: generic `Placeholder` («Раздел в разработке») заменяется компонентом `ComingSoon`
  (название секции + описание + пилюля «Скоро · Волна 4»); мёртвые пункты меню помечаются бейджем `W4`.

### 9.5 Негативные кейсы

- Неизвестный госномер → `404`; пустые списки `reconciliation`/`events`/`gap_periods` — валидны (не ошибка).
- Сенсорные ТС с `last_valid_navigation_timestamp = NULL` (2 из 7) → `online_status="stale"`, не падение.
- 1 unmatched навигационный ТС (`public_unit_id=null`) — в списке есть (у него реальный `problem_description`),
  но `reb_link_id=null` → строка не кликабельна в РЭБ.
- ТС без CAN−GPS разрыва (`distance_gap…=NULL`) → ячейка «нет данных», не 0.

### 9.6 Владение новыми файлами (без пересечений)

| Агент | Владеет | Зависит от |
|---|---|---|
| w3-6 fuel | `api/sql/25_v_fuel.sql`, `api/services/fuel_service.py`, роутер `api/routers/fuel.py` | b1, §9.2 |
| w3-7 sensors | `api/sql/26_v_sensors.sql`, `api/services/sensors_service.py`, роутер `api/routers/sensors.py` | b1, §9.2 |
| w3-8 navigation | `api/sql/27_v_nav_problem.sql`, `api/services/navigation_service.py`, роутер `api/routers/navigation.py` | b1, b12 (reb) |
| w3-9 fleet-health-view | `api/sql/28_v_fleet_health.sql`, `api/services/fleet_health_service.py`, роутер `api/routers/fleet_health.py` (`GET /api/fleet-health`) | w3-6/7/8 |
| w3-10 api-layer (f2/f3) | `web/src/api/{types,client,fixtures}.ts` (аддитивно) | §9.2 |
| w3-11 fleet-health-hub | `web/src/pages/{FleetHealth,FuelCard,SensorCard,NavProblemList}.tsx` | w3-10, d2/d4 |
| w3-12 cross-wiring | правки `web/src/pages/{IncidentCard,TripDossier,Report,EventsFeed}.tsx` (аддитивно) | w3-10 |
| w3-13 nav-signposting | `web/src/App.tsx`, `web/src/components/.../ComingSoon.tsx` | w3-11 |

---

## 10. Волна 4.4 — Data Trust (консистентность данных) · аддендум

> Добавлено 2026-06-10 (паттерн аддендума §9). Обоснование — интервью клиентов: Фомин (PepsiCo) —
> расхождение скоростей видео↔телематика, «39 ДТП в телематике, видео подтвердило 5»; Маслов (Балтика) —
> дубли ТС из-за двух терминалов, рассинхрон статусов. Конкурентный паттерн — Lytx review-queue
> (см. `COMPETITORS.md`). Волна выполняется ПОСЛЕ барьера x8 (финал Волны 4), барьер — x9.

### 10.0 Принцип

Все проверки — **детерминированный SQL поверх существующих таблиц** DuckDB. Никакого AI/сети:
это НЕ AI-фича → без `AiFeatureState`/`ai_flags`. Тоталы не хардкодить (55/94 и т.п.) — считать запросом.
Повторный вызов любого эндпоинта → байт-идентичный ответ.

### 10.1 Эндпоинты

- `GET /api/consistency` → `ConsistencyReport` (агрегат всех проверок).
- `GET /api/incidents/{id}/speed-check` → `SpeedCheck`; неизвестный `id` → 404.

### 10.2 Схемы (Pydantic / TS)

- `ConsistencyCheck { check_id, title_ru, status: 'ok'|'warn'|'fail', affected_count, total, ratio, sample_ids: string[], description_ru }`
  - `ratio = affected_count/total ∈ [0,1]` (total=0 → ratio=0); `sample_ids` ≤ 5 примеров;
  - статусы считает **сервис** (не SQL): `fail` если `ratio > 0.2`, `warn` если `ratio > 0`, иначе `ok`.
- `ConsistencyReport { checks: ConsistencyCheck[], evidence_rate, speed_agreement_rate, generated_at_source: 'duckdb' }`
  - `evidence_rate = 1 − ratio(incident_no_video)`; `speed_agreement_rate = 1 − ratio(speed_disagreement)`.
- `SpeedCheck { id, event_speed_kmh: number|null, track_speed_kmh: number|null, max_track_speed_kmh: number|null, delta_kmh: number|null, agreement: 'ok'|'minor'|'major'|'no_data', truth_source: 'gps_track' }`
  - пороги по `delta_kmh = |event − track|`: `ok` ≤ 5 · `minor` ≤ 15 · `major` > 15;
  - ближайшая точка трека в окне **±10 с** от начала события; нет точки в окне или нет `"Speed"` события → `no_data` (не 5xx).
- **ASSUMPTION (зафиксировано):** CAN-скорости в датасете НЕТ. Источник истины — GPS-трек
  (`video_events__track_points.speed_kmh`), `truth_source='gps_track'`. Требование Фомина «истина = CAN»
  аппроксимируется GPS до появления CAN-датасета (Волна 5, см. `WAVE-5-BACKLOG.md` W5-5).

### 10.3 SQL views (идемпотентные `CREATE OR REPLACE VIEW`, файлы `api/sql/34_*.sql`, `35_*.sql`)

`34_v_consistency.sql` → view `v_consistency_checks` (строка на проверку: `check_id, affected_count, total`;
по CTE на проверку). Канонические 7 проверок:

| check_id | Таблицы | Суть (SQL-идея) |
|---|---|---|
| `video_fleet_no_track` | alarms, track_points | `"UnitStateNumber"` из alarms без единой строки в `track_points` (по `unit_state_number`) |
| `incident_no_video` | alarms, video_files | алармы с `"VideoCount" > 0`, но без строк в `video_files` (по `alarm_id`) — пробел доказательной базы |
| `terminal_duplication` | alarms | `"UnitStateNumber"` с >1 различным `"TerminalId"` (дубли терминалов — кейс Маслова) |
| `plate_match_coverage` | reference__vehicle_matches | доля строк с `match_status <> 'matched'` по каждому `source_list` (fuel/sensors/navigation) |
| `timestamp_monotonicity` | track_points | `alarm_id`, где `timestamp_utc` убывает при росте `point_index` (битый порядок точек) |
| `coordinate_sanity` | alarms, track_points | NULL/пустые/вне диапазона (±90/±180) /(0,0) координаты — в alarms такие строки реально есть |
| `speed_disagreement` | v_speed_check | доля алармов с `agreement='major'` |

`35_v_speed_check.sql` → view `v_speed_check` (строка на аларм): `event_speed` = `CAST(NULLIF("Speed", '') AS DOUBLE)`
из alarms; `track_speed` = `speed_kmh` ближайшей точки `track_points` в окне ±10 с (оконно:
`row_number() OVER (PARTITION BY alarm_id ORDER BY abs(epoch(timestamp_utc) - epoch(event_begin_utc)))` —
колонка `event_begin_utc` уже есть в `track_points`; ASOF JOIN не использовать);
`max_track_speed` = `max(speed_kmh)` из `video_events__max_speed_points` по `alarm_id`.

### 10.4 Frontend (аддитивно)

- `web/src/components/ai/SpeedCheckBadge.tsx` — бейдж на `IncidentCard.tsx` рядом с `SceneContextChip` (f15):
  «Скорость: событие N · GPS M → совпадает/расходится», tooltip про источник истины (GPS-трек).
- `web/src/components/ai/ConsistencyPanel.tsx` — секция на `Metrics.tsx` ниже `DataQualityPanel` (f21):
  светофор по 7 проверкам + `evidence_rate`/`speed_agreement_rate`.
- Типы §10.2 → `web/src/api/types.ts`; клиент `getConsistency()`, `getSpeedCheck(id)` → `client.ts`;
  фикстуры (включая кейсы `no_data` и `major`) → `fixtures.ts` — за тем же свитчем `USE_FIXTURES`.

### 10.5 Негативные кейсы

- Аларм без точек трека в окне → `agreement='no_data'`, не 5xx; `delta_kmh=null`.
- Пустые `"Latitude"`/`"Longitude"` в alarms не валят view (попадают в `coordinate_sanity`).
- Все `ratio ∈ [0,1]`; пустая таблица-источник → `total=0, ratio=0, status='ok'`.
- Повторный вызов `/api/consistency` и `/speed-check` → идентичный ответ (детерминизм).

### 10.6 Владение (без пересечений)

| Промпт | Владеет | Зависит от |
|---|---|---|
| b28 | `api/sql/34_v_consistency.sql`, `api/services/consistency_service.py`, роутер `api/routers/consistency.py`, `api/domain/consistency.py` | b1 (ETL), §10.1–10.3 |
| b29 | `api/sql/35_v_speed_check.sql`, `api/services/speed_check_service.py`, роутер `api/routers/speed_check.py`, `api/domain/speed.py`; + согласованная замена CTE-заглушки `speed_disagreement` в `34_v_consistency.sql` (b28 знает) | b28 (строго последовательно) |
| f25 | `web/src/components/ai/SpeedCheckBadge.tsx`, `web/src/components/ai/ConsistencyPanel.tsx`; аддитивные правки `IncidentCard.tsx`/`Metrics.tsx`/`api/{types,client,fixtures}.ts` | b28/b29 (схемы §10.2), f15/f21 (точки вставки) |
| tu-consistency | `api/tests/unit/test_consistency.py`, `api/tests/unit/test_speed_check.py` | b28/b29 |

---

## 11. Волна 5.1 — Review Queue (очередь верификации событий) · аддендум

> Добавлено 2026-06-10. Обоснование: Фомин (PepsiCo) — «39 ДТП в телематике, видео подтвердило 5» —
> нужен workflow подтверждения/отклонения событий, а не разовая кнопка; паттерн лидера — Lytx
> human-in-the-loop review queue (`COMPETITORS.md`). Выполняется ПОСЛЕ барьера x9, барьер — x10.

### 11.0 Принцип и статусная модель (единый словарь)

- Статус ревью инцидента: `pending` (нет решения) · `validated` (подтверждён) · `dismissed` (отклонён).
- **Источник истины статуса ревью — ТОЛЬКО журнал `output/review_queue.csv`** (паттерн `actions.csv`):
  колонки `decided_at,incident_id,decision,note`; статус = **последняя** запись по `incident_id`;
  нет записи → `pending`. Легаси-экшен `validate` из §3.4 (`actions.csv`) НЕ трогаем и НЕ дублируем —
  он остаётся аудит-следом; двух источников статуса ревью быть не должно.
- `decided_at` пишется сервером при записи (прецедент `actions_service.record`); в бизнес-логике
  чтения времени нет (детерминизм чтения сохраняется).
- Решение по инциденту перезаписываемо: новая запись в журнале побеждает (append-only журнал).

### 11.1 Эндпоинты

- `GET /api/review-queue?status=pending|validated|dismissed` → `ReviewQueue` (без фильтра — все).
- `POST /api/review-queue/{incident_id}` body `{decision: 'validated'|'dismissed', note?: string}` →
  обновлённый `ReviewItem`; неизвестный `incident_id` → 404; невалидный `decision` → 422.
- При решении — эмит события `review_decision` в `ai_metric_events` через эмиттер b25
  (недоступен/выключен → тихий no-op, решение всё равно записано).

### 11.2 Схемы (Pydantic / TS)

- `ReviewItem { incident_id, alarm_code, severity, vehicle_plate, ts, video_available: bool, status: 'pending'|'validated'|'dismissed', note: string|null, decided_at: string|null }`
- `ReviewQueue { items: ReviewItem[], counts: { pending: int, validated: int, dismissed: int }, evidence_rate: number }`
  - `items` — все инциденты `v_incidents` (не хардкодить 55 — считать), статус из журнала;
  - `counts` согласованы с `items` (сумма = всего инцидентов); `evidence_rate` — из §10 (контекст очереди).

### 11.3 Frontend

- `web/src/pages/ReviewQueue.tsx` — живой экран на **существующем** маршруте `/validation`
  (NAV-пункт «Блок валидации»): таблица инцидентов (код/severity/ТС/время/чип «видео есть/нет»),
  фильтр по статусу, счётчики, кнопки «✓ Подтвердить» / «✗ Отклонить» (+ опц. заметка),
  клик по строке → `/incidents/{id}` (доказательная карточка).
- **Ревизия допущения f22 по его же критерию отката:** у `/validation` появился владелец → бейдж
  «Будущее» снят, ключ удалён из `COMING_SOON`, маршрут ведёт на живой экран. `/response` — без изменений.

### 11.4 Негативные кейсы

- Пустой/отсутствующий журнал → все `pending`, не 5xx. Битая строка журнала → пропустить, не падать.
- Повторное решение → статус перезаписан, в `counts` инцидент один раз.
- 404 на неизвестный id; 422 на неизвестный `decision`; пустая `note` валидна.

### 11.5 Владение (без пересечений)

| Промпт | Владеет | Зависит от |
|---|---|---|
| b30 | `api/services/review_service.py`, роутер `api/routers/review.py`, `api/domain/review.py`; журнал `output/review_queue.csv` | v_incidents (b3), §10 evidence_rate (b28), эмиттер b25 |
| f26 | `web/src/pages/ReviewQueue.tsx`; аддитивные правки `web/src/App.tsx` (роут/NAV/COMING_SOON), `web/src/api/{types,client,fixtures}.ts` | b30 (схемы §11.2), f22 (снимает его «Будущее» с `/validation`) |
| tu-review | `api/tests/unit/test_review.py` | b30 |

---

## 12. Волна 5.2 — Coaching Loop (цикл обучения водителя) · аддендум

> Добавлено 2026-06-10. Обоснование: Оздоев (Газпромнефть, дословный запрос) — инцидент →
> уведомление водителя → курс → тест (порог 18/20) → уведомление руководителя → эскалация при
> повторе за 30 дней. Паттерн лидеров: Samsara coaching effectiveness, Lytx coaching workflow.
> **Данные — СИНТЕТИЧЕСКИЕ** (датасета обучения не существует): честный демо-режим, UI обязан
> это показывать. Выполняется ПОСЛЕ x10, барьер — x11.

### 12.0 Принцип

- Датасет генерируется **детерминированно** из реальных алармов: `crc32(AlarmId)` — никакого
  `random`/`Date.now()` (паттерн `driver_reference`). Повторная генерация → байт-идентичный CSV.
- `repeat_within_30d` — **реальный** расчёт по алармам (та же `UnitStateNumber` + тот же `Type`
  в окне ±30 дней), не синтетика.
- Всё демо-режим: схема несёт литерал `synthetic: true`; UI показывает бейдж «синтетические данные».

### 12.1 Датасет `data/seed/training_assignments.csv` (генератор `api/etl/seed_coaching.py`)

- Загружается автоматически (`build_duckdb._load_seed_csvs`, glob `data/seed/*.csv`) как таблица
  `training_assignments` — ETL-загрузчик НЕ редактируется; в `Makefile` цель `seed` дополняется
  строкой генератора (аддитивно).
- Колонки: `assignment_id, incident_id, vehicle_plate, driver_id, course_id, course_title_ru,
  assigned_at, due_at, test_score, passed, completed_at, repeat_within_30d`.
- Правила генерации (фиксированы):
  - курс по `Type` аларма: `DMS_DROWSY|DMS_YAWNING → C-FATIGUE «Контроль усталости»` ·
    `DMS_PHONE|DMS_DISTRACTION → C-FOCUS «Концентрация и отвлечения»` · `HARSH_* → C-SMOOTH
    «Плавное вождение»` · `OVERSPEED|SpeedLimitViolation → C-SPEED «Скоростной режим»` ·
    `CAMERA_TAMPER|DRIVER_SUBSTITUTION → C-RULES «Регламент и оборудование»` · иначе `C-BASE
    «Базовый курс безопасности»`;
  - `assigned_at` = `Begin` аларма; `due_at` = `assigned_at + 72h`;
  - `test_score` = `crc32(str(AlarmId)) % 21` (0..20); `passed` = `test_score >= 18` (порог Оздоева);
  - `completed_at` = `assigned_at + (crc32(str(AlarmId)) % 48 + 1)h` если `test_score >= 10`, иначе пусто;
  - `driver_id` — из `driver_reference` по `vehicle_plate`.

### 12.2 Эндпоинты

- `GET /api/coaching` → `CoachingSummary[]` (по водителям, сортировка по `repeat_violation_rate` desc).
- `GET /api/coaching/{plate}` → `CoachingCard`; `plate` не из `driver_reference` → 404.

### 12.3 Схемы (Pydantic / TS)

- `CoachingAssignment { assignment_id, incident_id, course_id, course_title_ru, assigned_at, due_at, test_score, status: 'passed'|'failed'|'incomplete', completed_at: string|null, repeat_within_30d: bool }`
  - `status`: `passed` (passed=true) · `failed` (completed_at есть, passed=false) · `incomplete` (completed_at пуст).
- `CoachingKpi { completion_rate, pass_rate, repeat_violation_rate }` — completion = c `completed_at`/всего;
  pass = passed/завершивших (0 завершивших → 0.0); repeat = с `repeat_within_30d`/всего; все ∈ [0,1].
- `CoachingSummary { vehicle_plate, driver_id, driver_name, total: int, kpi: CoachingKpi }`
- `CoachingCard { vehicle_plate, driver_id, driver_name, assignments: CoachingAssignment[], kpi: CoachingKpi, synthetic: true }`

### 12.4 Frontend и негативы

- Секция «Обучение водителя» в driver-ветке отчёта (`Report.tsx`), после существующих KPI-блоков
  (ориентир — блок дисциплинарного предупреждения): KPI-чипы + таблица назначений + **обязательный
  бейдж «синтетические данные (демо)»**.
- Негативы: водитель из `driver_reference` без назначений → пустой список + нулевые KPI (200, не 404);
  повторная генерация CSV → байт-идентичный файл; все ratio ∈ [0,1].

### 12.5 Владение (без пересечений)

| Промпт | Владеет | Зависит от |
|---|---|---|
| b31 | `api/etl/seed_coaching.py`, `data/seed/training_assignments.csv` (коммитится, как driver_reference), строка в `Makefile` цели `seed` | alarms, driver_reference |
| b32 | `api/services/coaching_service.py`, роутер `api/routers/coaching.py`, `api/domain/coaching.py` | b31 (таблица), §12.2–12.3 |
| f27 | аддитивная правка `web/src/pages/Report.tsx`; `web/src/api/{types,client,fixtures}.ts` | b32 (схемы) |
| tu-coaching | `api/tests/unit/test_coaching.py` | b31/b32 |
