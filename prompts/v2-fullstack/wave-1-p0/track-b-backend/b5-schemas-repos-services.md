# b5 · Pydantic-схемы, репозитории, сервисы

> Трек **Backend/Data**. Против `00-CONTRACT.md` §2/§3.1. **Владеет:** `api/domain/*`, `api/repositories/*`, `api/services/*`.
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — детерминированная логика/вёрстка против контракта; гейт = секция Check.
> Кодит против контракта (поля/схемы/таблицы) — не ждёт рантайма b1/b3. Подключается роутерами b6.

## Цель

Доменные модели (Pydantic v2), доступ к DuckDB (репозитории) и бизнес-логику (сервисы).
**Incidents — полностью**; reports/vehicles — рабоче; fuel/sensors/navigation — стабы.

## domain/ (Pydantic v2) — ЕДИНЫЙ владелец всех схем (P0 §3.1 + full-scope §7.5)

b5 — **единственный владелец `api/domain/*`**. Здесь определяются ВСЕ Pydantic-модели, включая P1/P2
из §7.5 (их используют b9–b13, но материализует только b5 — иначе конфликт владения `domain/`).

- `common.py` — `Severity`, `Source`, `Status` (Literal/Enum), базовые типы.
- `incidents.py` — `Camera` (+`offline_from/to`), `TelemetryPoint`, `IncidentSummary`, `IncidentDetail`
  (наследует Summary; включает `confidence`, `event_version`, `driver_region/department/safety_score`,
  `sensor_active_after_sec`, `cam_extra[]` по §3.1).
- `reports.py` — **полные §7.5**: `ReportQuery {kind, plate?, driver_name?, period_days=3, view?}`
  (заменяет старую форму `{text}` из §3.3 — её НЕ создавать), `ReportKPI`, `ReportPeriod`, `ViolationRow`,
  `DriverRef`, `DriverReport`, `FleetReport`, `VehicleReport`.
- `entities.py` — `Action {incident_id, action, comment}`, `Ticket`, `DispatchAlert`, `TripDossier`,
  `RebRecovery`, `SabotageEvent` (§7.5).
- `vehicles.py` — `VehicleSummary`.
- Имена полей и опциональность — **точно** как в §3.1/§7.5 (camelCase только где указано: `hasVideo`).

## repositories/ (DuckDB SQL → dict/DataFrame)

- `incidents_repo.py`:
  - `list_incidents(db, **filters) -> list[dict]` — `SELECT * FROM "v_incidents"` + WHERE по severity/source/status/plate + LIMIT/OFFSET.
  - `get_incident(db, id) -> dict | None`.
  - `track_points_for(db, id) -> list[dict]` (из `video_events__track_points`).
  - `video_files_for(db, id) -> list[dict]` (из `video_events__video_files`).
  - `count_alarms_in_window(db, plate, ts, days=7) -> int` (для events_last_7d).
  - `video_path_for(db, id, channel) -> str | None`.
- `vehicles_repo.py` — `list_vehicles(db)` из `video_events__vehicles`.
- `_stubs.py` (или fuel_repo/sensors_repo/navigation_repo) — пустые функции с `# TODO`, таблицы существуют.

## services/

- `incidents_service.py` — **сборка контракта**: берёт строку `v_incidents` (repo) + enrichment (b2):
  `driver/driver_id/driver_phone/vehicle_model/speed_limit_kmh/is_night/continuous_driving_min/events_last_7d/risk_score/status/evidence_summary/cameras/telemetry`.
  - `list_summaries(db, filters) -> list[IncidentSummary]`.
  - `get_detail(db, id) -> IncidentDetail | None`.
  - `get_telemetry(db, id) -> list[TelemetryPoint]`.
- `reports_service.py` — `driver_report(db, plate)`, `fleet_report(db)`, `query(db, text)` (NLU-заглушка: regex по «ФИО/госномер/период» → driver_report или fleet_report; `# TODO Groq/Whisper`).
- `actions_service.py` — `record(action)`: append в `output/actions.csv` (колонки `created_at,incident_id,action,comment`), обновление статуса инцидента в рантайм-словаре.
- `fuel_service.py`/`sensors_service.py`/`navigation_service.py` — стабы, поднимают `NotImplementedError` / возвращают `None`, `# TODO`.

## Check

- `from api.services.incidents_service import get_detail` импортируется.
- Pydantic-модели валидируются на примере из `data/mock/incidents.py` (форма совпадает).
- `incidents_service.get_detail` возвращает `IncidentDetail` со всеми enrichment-полями (после `make db`).
