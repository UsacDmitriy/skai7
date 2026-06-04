# b5 · Pydantic-схемы, репозитории, сервисы

> Трек **Backend/Data**. Против `00-CONTRACT.md` §2/§3.1. **Владеет:** `api/domain/*`, `api/repositories/*`, `api/services/*`.
> Кодит против контракта (поля/схемы/таблицы) — не ждёт рантайма b1/b3. Подключается роутерами b6.

## Цель

Доменные модели (Pydantic v2), доступ к DuckDB (репозитории) и бизнес-логику (сервисы).
**Incidents — полностью**; reports/vehicles — рабоче; fuel/sensors/navigation — стабы.

## domain/ (Pydantic v2, строго по §3.1)

- `common.py` — `Severity`, `Source`, `Status` (Literal/Enum), базовые типы.
- `incidents.py` — `Camera`, `TelemetryPoint`, `IncidentSummary`, `IncidentDetail` (наследует Summary).
- `reports.py` — `DriverReport`, `FleetReport`, `ReportQuery {text:str}`, `Action {incident_id, action, comment}`.
- `vehicles.py` — `VehicleSummary`.
- Имена полей и опциональность — **точно** как в §3.1 (camelCase только где указано: `hasVideo`).

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
