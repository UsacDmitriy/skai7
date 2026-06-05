# b10 · Reports — SQL-views + reports_service

> Трек **Backend/Data**. Против `00-CONTRACT.md` §7.2/§7.4/§7.5 (база — §3.3). **Владеет:** `api/sql/20_v_driver_report.sql`, `api/sql/21_v_fleet.sql`, `api/sql/22_v_vehicle.sql`; расширение `api/services/reports_service.py`.
> **Модель:** 🔵 Sonnet — детерминированная логика/вёрстка против контракта; гейт = секция Check.
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
  список водителей за период (**1 ТС = N водителей** через `driver_trips`, не `driver_reference`;
  `role` main/secondary и `trips` берутся из `driver_trips`).

> SQL-views держат «сырое+агрегаты»; `risk_score`-зависимые величины, требующие формулы §2,
> досчитывает сервис (как в §1.3 для `v_incidents`).

## Расширение `api/services/reports_service.py`

Дополнить существующий сервис b5 (не ломая `driver_report`/`fleet_report`):

- `driver_report(db, plate, period_days=3) -> DriverReport` — поверх `v_driver_report`, обогащение
  водителя через `driver_reference` (b7); `kpi: ReportKPI` (всего/ВА/телематика/грубых); `violations:
  ViolationRow[]` с `is_gross`; `disciplinary_warning = gross>=3 OR safety_score<60` (§7.5).
- `fleet_report(db, period_days=3, view="drivers") -> FleetReport` — поверх `v_fleet`; разрез
  `view ∈ {"drivers","vehicles"}`. `by_vehicles[]` несёт `risk_score`, `gross`, `cameras_ok="N/3"`.
- **Правило «грубых» (gross)** — единое (§7.5): `severity=critical OR alarm_code ∈ {OVERSPEED, DMS_SMOKING}`.
  Реализовать как хелпер `is_gross(row)` и переиспользовать в driver/fleet/vehicle.
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

## Edge cases / поведение

- **Правило gross:** `is_gross(row)` истинно ⟺ `severity="critical"` ИЛИ `alarm_code ∈ {OVERSPEED, DMS_SMOKING}` (§7.5); один и тот же хелпер в driver/fleet/vehicle (нет расхождений между разрезами).
- **`disciplinary_warning`:** истинно ⟺ `gross>=3` ИЛИ `safety_score<60`; на границах `gross=3`/`safety_score=59` → `true`, `gross=2`+`safety_score=60` → `false`.
- **Пустой период / нет алярмов:** `driver_report`/`fleet_report`/`vehicle_report` за период без событий → KPI все `0` (`total/video_da/telematics/gross`), `violations=[]`, `disciplinary_warning` только по `safety_score`; **не ошибка**.
- **Неизвестный plate:** `driver_report`/`vehicle_report` для plate вне `driver_reference`/данных → по контракту: пустой отчёт (нулевые KPI, водитель из синтетики `driver_for`) либо 404 на уровне роутера; сервис не бросает необработанное исключение.
- **ФИО→plate резолв:** `query` по `driver_name` без совпадения в `driver_reference` → безопасный дефолт (fleet или пустой driver-отчёт), не падать; неоднозначное ФИО (несколько ТС) — детерминированный выбор.
- **Согласованность сумм KPI:** `total == video_da + telematics`; `gross<=total`; в `FleetReport` сумма `total`/`gross` по `by_drivers` согласована с агрегатной `kpi` (один источник `v_incidents`).
- **vehicle: 1 ТС = N водителей:** `drivers` берётся из `driver_trips` (не `driver_reference`), ≥1 строка, ровно один `role="main"`; `cameras` всегда длины 3, `cameras_ok` формата `"N/3"`.
- **Детерминизм по входу:** одинаковый `(plate, period_days)` → идентичный отчёт между вызовами (NLU regex-fallback детерминирован, view стабильны).
