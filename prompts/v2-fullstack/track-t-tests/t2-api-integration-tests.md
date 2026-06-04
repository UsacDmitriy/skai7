# T2 · API интеграционные тесты (pytest + TestClient)

> Track T (Claude Code, `feat/tests`). Против `00-CONTRACT.md` §3 (эндпоинты/схемы) + §7.4/§7.5. **Владеет:** `api/tests/integration/**`.
> Запускается после b6 (P0) и b11–b13 (P1/P2). Использует `make db`. Не редактирует продуктовый код.

## Цель
Проверить контракт API на живом приложении через `fastapi.testclient.TestClient`: коды ответов,
форму JSON (валидация против Pydantic-схем), граничные случаи.

## Состав

`api/tests/integration/test_incidents_api.py`:
- `GET /api/health` → 200.
- `GET /api/incidents` → 200, список `IncidentSummary`; `risk_score:int`, `driver`, `vehicle_model` не пустые.
- фильтры `?severity=&source=&status=&vehicle_plate=` сужают выдачу.
- `GET /api/incidents/{id}` → 200 `IncidentDetail` (есть `cameras[]`, `telemetry[]`, `confidence`,
  `driver_region`, `cam_extra[]`); несуществующий id → 404.
- `GET /api/incidents/{id}/video/{channel}` → 200 mp4 или 404.
- `POST /api/actions` (`validate`/`stop_vehicle`/…) → 200, строка дописана в `output/actions.csv`.

`api/tests/integration/test_reports_api.py`:
- `GET /api/reports/driver/{plate}` → `DriverReport` (kpi, violations с `is_gross`, `disciplinary_warning`).
- `GET /api/reports/fleet?view=drivers|vehicles` → `FleetReport` (оба разреза).
- `GET /api/reports/vehicle/{plate}` → `VehicleReport` (`cameras` len 3, `drivers` ≥1).
- `POST /api/reports/query` `{text}` → `{query, report}`; driver/fleet ветки (regex-fallback без Groq).
- `POST /api/reports/transcribe` (wav multipart) → `{text, lang, confidence}` (можно мокать модель STT).

`api/tests/integration/test_p1p2_api.py`:
- `GET /api/tickets|alerts/{id}|trips/{id}|reb/{id}|sabotage` → 200 + схемы §7.5.
- `GET /api/fuel/*`, `/api/sensors/*` → 501.

## Check
- `pytest api/tests/integration -q` зелёный после `make db`.
- Каждая ручка валидируется против Pydantic-модели (response_model или ручная проверка ключей).
- В `/docs` присутствуют теги всех роутеров (incidents/reports/vehicles/actions/tickets/alerts/trips/sabotage/reb).
