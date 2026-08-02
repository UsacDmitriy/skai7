# W3-8 · Домен navigation (список проблемных треков → вход в РЭБ) — снять 501-стаб

> Волна 3 · бэклог. Трек **Backend/Data**. Против `00-CONTRACT.md` **§9** (§9.1/§9.2/§9.3/§9.5) + §7.4 (`/api/reb`).
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — детерминированная логика против контракта; гейт = секция Check.
> **Владеет:** `api/sql/27_v_nav_problem.sql`, `api/services/navigation_service.py`, роутер
> `api/routers/navigation.py` (сейчас → `501`). **Зависит от** b12 (`/api/reb/{id}` уже реализован). **Не блокирует** P0/P1/P2.

## Контекст (экран-сирота РЭБ)

`/api/reb/{id}` ([`api/routers/reb.py`](../../../../api/routers/reb.py), `v_reb`, `reb_service`) **уже
работает**, но экран `/reb/:id` достижим только по прямому URL — нет списка-входа. В БД есть
`navigation__navigation_problem_vehicles` (5 matched + 1 unmatched, поле `problem_description` — живой
текст «Разрывы в треке», «Круги на карте») и `navigation__track_periods` (422; `period_type=3` = потеря GPS).
`/api/navigation` повышается из `501` до **list-эндпоинта**, ведущего в `/api/reb/{id}`.

> **Критично (§9.3):** `navigation__track_periods.vehicle_id` хранит «грязный» лейбл (`С725АТ159(ТМ)`,
> `А 230 КУ/550 RUS`) ≠ чистый `public_state_number`. Поэтому **`reb_link_id = public_unit_id`** (UUID
> есть и в `navigation_problem_vehicles`, и в `track_periods`). У unmatched-ТС `public_unit_id=null` → `reb_link_id=null`.

## Что сделать

1. **View `api/sql/27_v_nav_problem.sql`** (`DROP VIEW IF EXISTS "v_nav_problem"`):
   `navigation__navigation_problem_vehicles` LEFT JOIN агрегат `navigation__track_periods` по
   `public_unit_id` → `gap_count`/`total_periods`/`total_gap_duration_sec` (по `period_type=3`; парс
   `HH:MM:SS` как в [`24_v_reb.sql`](../../../../api/sql/24_v_reb.sql)). Колонки — под `NavProblemVehicle` (§9.2).
2. **Сервис `api/services/navigation_service.py`**:
   - `list_nav_problems(db) -> list[NavProblemVehicle]` (5–6 строк, включая unmatched).
   - `get_nav_problem(db, plate) -> NavProblemVehicle | None` (404 при `None`).
   - `in_video_fleet` = `plate` (норм.) ∈ `v_incidents.vehicle_plate` — `true` для `О802УЕ198`, `С725АТ159`.
3. **Pydantic-схема** `NavProblemVehicle` — в `api/domain/fleet_health.py`, строго по §9.2.
4. **Роутер `api/routers/navigation.py`** — заменить стабы: `GET /api/navigation` → `NavProblemVehicle[]`,
   `GET /api/navigation/{plate}` → `NavProblemVehicle`. **Без коллизии префиксов** с `reb.py` (тот — `/api` + `/reb/{id}`).

## Check

- `make db`; `SELECT count(*) FROM v_nav_problem` ≥ **5**.
- `curl -s :8000/api/navigation | jq length` ≥ 5; элемент содержит `problem_description`, `gap_count`, `reb_link_id`, `in_video_fleet`.
- Для matched-ТС `reb_link_id` (UUID) непуст → `GET /api/reb/<reb_link_id>` отдаёт `200` (связь list→РЭБ работает).
- unmatched-ТС присутствует в списке, но `reb_link_id=null` (не кликабелен в РЭБ).
- Ровно 2 ТС с `in_video_fleet=true`. Неизвестный госномер → **404**; `grep -L 501 api/routers/navigation.py`.

## Коммит (обязательно)

```bash
git add -A && git commit -m "w3-8: домен navigation (v_nav_problem + navigation_service + роутер), список→РЭБ"
```
