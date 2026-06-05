# W3-14 · Тесты API тёмных данных (fuel / sensors / navigation / fleet-health)

> Волна 3 · бэклог. Трек **T (tests)**. Против `00-CONTRACT.md` **§9** (§9.1/§9.2/§9.5).
> **Модель:** 🔵 Sonnet — детерминированные тесты против контракта; гейт = секция Check.
> **Владеет:** `api/tests/test_fuel_api.py`, `test_sensors_api.py`, `test_navigation_api.py`,
> `test_fleet_health_api.py`. Переиспользует существующий conftest/DuckDB-фикстуру (как `test_reb_api.py`).
> Счёт в гейт покрытия api≥85% (Барьер 3). **Зависит от** w3-6..w3-9.

## Что покрыть (happy + негатив, §FEATURES Definition of Done #6)

1. **fuel** — `GET /api/fuel` → `200`, `len==10`, элемент валидируется схемой `FuelVehicleSummary`
   (есть `volume_delta_zis_minus_card_l`, `recon_status ∈ {matched,review,missing_sensor_event}`).
   `GET /api/fuel/{plate}` (реальный, напр. `А144ЕВ193`) → `200`, `FuelVehicleCard` с непустыми
   `reconciliation`/`events`; неизвестный → `404`; нормализация госномера (с пробелом/в другом регистре) находит ТС.
2. **sensors** — `GET /api/sensors` → `200`, `len==7`; ровно 2 ТС `online_status=="stale"`. `GET /{plate}` →
   `200`, `daily_mileage` длиной 7. **Ассерт: ответ НЕ содержит `graph_points`/`graph_status`** (ключей нет
   ни на одном уровне). ТС без CAN−GPS → `distance_gap…` is `None`. Неизвестный → `404`.
3. **navigation** — `GET /api/navigation` → `200`, `len>=5`; есть unmatched-строка (`reb_link_id is None`);
   ровно 2 с `in_video_fleet==True`. Для matched: `reb_link_id` подаётся в `GET /api/reb/{reb_link_id}` → `200`
   (сквозная связь list→РЭБ). Неизвестный → `404`.
4. **fleet-health** — `GET /api/fleet-health` → `200`; `coverage=={fuel:10,sensors:7,navigation:5,in_video_fleet:2}`;
   `len(rows)==17`; у ТС без домена соответствующий KPI `None` (контракт «—» на фронте).

## Check

- `pytest api/tests/test_fuel_api.py api/tests/test_sensors_api.py api/tests/test_navigation_api.py api/tests/test_fleet_health_api.py -q` — зелёный.
- Каждый домен имеет позитивный (схема/длины) и негативный (`404`) кейс; sensors имеет явный
  анти-регресс-ассерт об отсутствии `graph_points`.
- `pytest --cov=api api/tests` — новые роутеры/сервисы повышают покрытие (вклад в гейт ≥85%).

## Коммит (обязательно)

```bash
git add -A && git commit -m "w3-14: API-тесты fuel/sensors/navigation/fleet-health (happy+негатив)"
```
