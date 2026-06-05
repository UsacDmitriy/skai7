# b6 · Роутеры FastAPI

> Трек **Backend/Data**. Против `00-CONTRACT.md` §3.2–3.4. **Владеет:** `api/routers/*`.
> **Модель:** 🔵 Sonnet — детерминированная логика/вёрстка против контракта; гейт = секция Check.
> Подключает сервисы b5 (`get_detail`, `list_summaries`, …) и зависимость `get_db` (b4).
> Регистрацию роутеров в app делает x2 (или этот промпт добавляет include — согласовать с b4-комментом).

## Цель

HTTP-слой. **incidents/reports/vehicles/actions — рабочие**; fuel/sensors/navigation — `501`.

## Роутеры (один файл = один APIRouter с prefix)

- `incidents.py` (`prefix="/api/incidents"`):
  - `GET ""` → `list[IncidentSummary]`, query `severity/source/status/vehicle_plate/limit=100/offset=0`.
  - `GET "/{id}"` → `IncidentDetail` (404 если нет).
  - `GET "/{id}/telemetry"` → `list[TelemetryPoint]`.
  - `GET "/{id}/video/{channel}"` → `FileResponse` mp4 из `settings.media_dir` (404 если нет; `channel∈{1,2,3,5}`).
- `reports.py` (`prefix="/api/reports"`): `GET /driver/{plate}`, `GET /fleet`, `POST /query` (тело `ReportQuery`).
- `vehicles.py` (`prefix="/api/vehicles"`): `GET ""` → `list[VehicleSummary]`.
- `actions.py` (`prefix="/api/actions"`): `POST ""` тело `Action` → запись + обновлённый `status`.
- `fuel.py`/`sensors.py`/`navigation.py`: роутеры со всеми путями, возвращают `HTTPException(501, "Not implemented")`, `# TODO`.

## Требования

- Зависимость БД через `Depends(get_db)`.
- `response_model=` на каждом эндпоинте (из domain b5).
- Ошибки — `HTTPException` с `detail`.
- Список всех роутеров экспортировать (`api/routers/__init__.py: ALL_ROUTERS = [...]`) для удобного include в x2.

## Check

- После `make db` + `uvicorn api.main:app` (с include из x2):
  `GET /api/incidents` → 200, массив ≤100 `IncidentSummary`.
  `GET /api/incidents/{валидный_id}` → 200 `IncidentDetail` с cameras/telemetry/risk_score.
  `GET /api/fuel/...` → 501.
- OpenAPI `/docs` показывает все группы тегов.
