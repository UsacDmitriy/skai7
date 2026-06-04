# b10 · Reports — SQL-views + reports_service

> Трек **Backend/Data**. Против `00-CONTRACT.md` §7.2/§7.4/§7.5 (база — §3.3). **Владеет:** `api/sql/20_v_driver_report.sql`, `api/sql/21_v_fleet.sql`, `api/sql/22_v_vehicle.sql`; расширение `api/services/reports_service.py`.
> Кодит против контракта. **Зависит от:** b1 (таблицы DuckDB), b3 (`v_incidents`, создаётся первым — порядок `10_` < `20_`), b7 (`driver_reference`), b9 (`nlu_service.parse`). Параллелится по SQL с b11/b12 (разные файлы), но `reports_service.py` — только b10.

## Цель

Аналитика по водителю/парку/ТС (идея #2): SQL-views поверх таблиц b1 + расширение сервиса отчётов
реальным NLU (b9) и справочником водителей (b7). Заменяет NLU-заглушку из §3.3.

## SQL-views (применяются b1 в лексикографическом порядке, поверх `v_incidents`)

- `api/sql/20_v_driver_report.sql` → `v_driver_report` (идея #2, В-1):
  алярмы и метрики по `"vehicle_plate"` за период. Поверх `"v_incidents"`: счётчики по `severity`,
  `max(speed_kmh)`, доля ночных, суммарный пробег (через `track_summary`), список алярмов.
  Каждый view начинается с `DROP VIEW IF EXISTS` (идемпотентность b1).
- `api/sql/21_v_fleet.sql` → `v_fleet` (идея #2, В-2):
  агрегаты по парку **в двух разрезах** — по водителям (через `driver_reference`) и по ТС
  (по `vehicle_plate`/`unit_id`): кол-во алярмов, средний/макс `risk`, кол-во ТС/водителей.
- `api/sql/22_v_vehicle.sql` → `v_vehicle` (идея #2 В-2/ТС, #10):
  карточка ТС — `vehicle_plate`, модель, статус камер (из `video_events__video_files`),
  список водителей за период (**1 ТС = N водителей** через `driver_reference`).

> SQL-views держат «сырое+агрегаты»; `risk_score`-зависимые величины, требующие формулы §2,
> досчитывает сервис (как в §1.3 для `v_incidents`).

## Расширение `api/services/reports_service.py`

Дополнить существующий сервис b5 (не ломая `driver_report`/`fleet_report`):

- `driver_report(db, plate, period_days=3) -> DriverReport` — поверх `v_driver_report`, обогащение
  водителя через `driver_reference` (b7); метрики периода.
- `fleet_report(db, period_days=3, view="drivers") -> FleetReport` — поверх `v_fleet`; разрез
  `view ∈ {"drivers","vehicles"}` (по водителям / по ТС).
- `vehicle_report(db, plate, period_days=3) -> VehicleReport` — поверх `v_vehicle` (схема §7.5):
  `cameras: Camera[]`, `drivers: DriverRef[]` (роль main/secondary по числу поездок), `period_alarms`, `mileage_km`.
- `query(db, text, period_days=None) -> dict` — **реальный NLU**: `q = nlu_service.parse(text)` (b9),
  по `q.kind` зовёт `driver_report`/`fleet_report` (используя `q.plate`/`q.driver_name`/`q.period_days`/`q.view`);
  возвращает обёртку `{"query": q, "report": <DriverReport|FleetReport>}` (формат ответа §7.4).
  ФИО→plate: резолв через `driver_reference` по `driver_name`.

## Check

- После `make db` существуют view `v_driver_report`, `v_fleet`, `v_vehicle` (`SELECT * ... LIMIT 1` без ошибок).
- `reports_service.driver_report(db, plate)` возвращает `DriverReport` с водителем из `driver_reference`.
- `reports_service.vehicle_report(db, plate)` возвращает `VehicleReport`; `drivers` — список `DriverRef` (≥1), `cameras` заполнены.
- `reports_service.query(db, "Нарушения Иванова за 3 дня")` без ключа Groq возвращает `{"query": ReportQuery, "report": DriverReport}`.
- `query(db, "отчёт по парку")` → `kind="fleet"`, `report` — `FleetReport`.
- Повторный `make db` пересоздаёт view без дублей (`DROP VIEW IF EXISTS`).
