# W3-6 · Домен fuel (топливная сверка ЗИС vs карты) — снять 501-стаб

> Волна 3 · бэклог. Трек **Backend/Data**. Против `00-CONTRACT.md` **§9** (аддендум, contract-change #2)
> + §9.0/§9.1/§9.2/§9.3/§9.5. **Модель:** 🔵 Sonnet — детерминированная логика против контракта; гейт = секция Check.
> **Владеет:** `api/sql/25_v_fuel.sql`, `api/services/fuel_service.py`, роутер `api/routers/fuel.py`
> (сейчас все пути → `501`). **Паттерн:** как `api/services/reb_service.py` (читать view/таблицы через
> `rows_to_dicts`, сборку Pydantic делать в сервисе; репозиторного слоя не вводить). **Не блокирует** P0/P1/P2.

## Контекст (тёмные данные)

В `data/skai.duckdb` загружены `fuel__fuel_vehicles` (10 ТС), `fuel__fuel_summary`,
`fuel__fuel_reconciliation` (30), `fuel__fuel_events` (27 заправок ЗИС) — но роутер
[`api/routers/fuel.py`](../../../../api/routers/fuel.py) отдаёт `501`, и данные нигде не показаны.
**Топливо — изолированный остров** (§9.0: пересечение с видеопарком = 0): домен самодостаточен, не
линкуется к инцидентам/водителям/РЭБ. Заголовочный KPI — `volume_delta_zis_minus_card_l` (расхождение
бак-сенсор ЗИС vs топливные карты).

## Что сделать

1. **View `api/sql/25_v_fuel.sql`** (идемпотентный `DROP VIEW IF EXISTS "v_fuel"`): `fuel__fuel_vehicles`
   LEFT JOIN агрегат `fuel__fuel_reconciliation` по `vehicle_id` → `recon_status` = худший статус сверки
   (`missing_sensor_event` > `review` > `matched`). Колонки — под `FuelVehicleSummary` (§9.2).
2. **Сервис `api/services/fuel_service.py`**:
   - `list_fuel(db) -> list[FuelVehicleSummary]` — из `v_fuel` (10 строк).
   - `get_fuel(db, plate) -> FuelVehicleCard | None` — `None`, если ТС нет (роутер → 404). Сборка:
     summary из `fuel__fuel_summary`; `reconciliation: FuelReconRow[]` и `events: FuelEvent[]` —
     читаются по `vehicle_id` напрямую (во view не материализуются). **Нормализация** госномера
     (strip пробелов/регистра) при матче, чтобы `/api/fuel/А144ЕВ193` работал из UI.
3. **Pydantic-схемы** — в новом модуле `api/domain/fleet_health.py` (сосед `entities.py`):
   `FuelVehicleSummary`, `FuelReconRow`, `FuelEvent`, `FuelVehicleCard` строго по §9.2.
4. **Роутер `api/routers/fuel.py`** — заменить тела стабов: `GET /api/fuel` → `FuelVehicleSummary[]`,
   `GET /api/fuel/{plate}` → `FuelVehicleCard` (404 при `None`). Авто-discovery в `api/main.py` —
   регистрация не нужна.

## Check

- `make db` идемпотентен; `SELECT count(*) FROM v_fuel` = **10**.
- `curl -s localhost:8000/api/fuel | jq length` = **10**; элемент содержит `volume_delta_zis_minus_card_l`, `recon_status`.
- `curl -s localhost:8000/api/fuel/А144ЕВ193 | jq '.reconciliation|length, .events|length'` — непустые; схема `FuelVehicleCard`.
- Неизвестный госномер → `GET /api/fuel/НЕТ999` → **404** (детерминированно).
- `recon_status` ∈ {matched, review, missing_sensor_event}; пустые `reconciliation`/`events` — валидны (не ошибка).
- Роутер `fuel.py` больше не содержит `501` (`grep -L 501 api/routers/fuel.py`).

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**; незакоммиченная
работа в worktree на барьер не попадёт:

```bash
git add -A && git commit -m "w3-6: домен fuel (v_fuel + fuel_service + роутер), снят 501"
```
