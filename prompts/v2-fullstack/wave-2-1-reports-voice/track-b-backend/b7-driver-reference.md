# b7 · Справочник водителей — driver_reference

> Трек **Backend/Data**. Против `00-CONTRACT.md` §7.1 (база — §2 enrichment). **Владеет:** `data/seed/driver_reference.csv`, `api/etl/seed_drivers.py`; правка `enrichment.driver_for` (по согласованию с b2).
> **Модель:** 🔵 Sonnet — детерминированная логика/вёрстка против контракта; гейт = секция Check.
> Кодит против контракта. **Зависит от:** b1 (таблица `video_events__selected_video_alarms` в DuckDB), §2 enrichment (формула `risk_score`). Параллелится с b8/b9/b11/b12 (не пересекаются по файлам).

## Цель

Завести **реальную таблицу DuckDB** `driver_reference` с идентичностями водителей, посеянную
детерминированно один раз и **заменяемую** на внешний источник (RFID/HR-API) без изменения контракта API.
Перевести `enrichment.driver_for(plate)` со чистой синтетики на «сначала справочник, иначе синтетика».

## Артефакт сида: `data/seed/driver_reference.csv` (в git, не генерируется на лету)

Колонки (SQL-идентификаторы в двойных кавычках при запросах):
`vehicle_plate, unit_id, driver_id, driver_name, driver_phone, department, region, safety_score`.

## Скрипт `api/etl/seed_drivers.py`

1. Открыть `data/skai.duckdb`, прочитать уникальные пары `("UnitStateNumber", "UnitId")` из
   `"video_events__selected_video_alarms"`.
2. Для каждого ТС детерминированно (seed `= crc32(plate)`, без `random` без seed):
   - `driver_id` = `"DRV-" + str(seed % 9000 + 1000)` (как в §2).
   - `driver_name` — выбор из фиксированного пула **≥20 ФИО** по `seed % len(NAMES)`.
   - `driver_phone` — `"+7" + 10 цифр` из `seed` (стабильно, как в §2).
   - `department` — из фиксированного пула подразделений по `seed`.
   - `region` — из фиксированного пула **≥5 регионов** по `seed`.
   - `safety_score` = `round(100 − avg(risk_score))` по всем алярмам этого ТС
     (`risk_score` считается по формуле §2 через `api/core/enrichment.py`; clamp в `[0, 100]`).
3. Записать строки в `data/seed/driver_reference.csv` (header дословно как колонки выше).
4. Идемпотентность: повторный запуск перезаписывает CSV с тем же содержимым (сид детерминирован).
5. Точки входа: `python -m api.etl.seed_drivers` и `python api/etl/seed_drivers.py`.
6. Пулы (`NAMES`, `DEPARTMENTS`, `REGIONS`) — константы модуля; **те же**, что использует `enrichment`
   (вынести в общий источник либо продублировать с явным комментарием синхронизации с b2).

## Второй сид: `data/seed/driver_trips.csv` (мульти-водитель на ТС, §7.1)

Для В-2 «по ТС» макет требует «основной водитель + другие». `driver_reference` = основной водитель ТС;
`driver_trips` = связь ТС→водители за период. Колонки: `vehicle_plate, driver_id, driver_name, role, trips`.
Генерация (`seed_drivers.py`): для каждого ТС — основной водитель (из `driver_reference`, `role="main"`,
`trips` = 60–80% рейсов) + детерминированно 0–1 вторичный (`role="secondary"`, из пула по `seed*7`,
остаток рейсов). Грузится как таблица `"driver_trips"` (тем же приёмом `CREATE OR REPLACE TABLE`).

## Загрузка в DuckDB

b1 рекурсивно грузит `data/seed/*.csv` с префиксом `seed` → таблицы `"seed__driver_reference"`/`"seed__driver_trips"`.
Для стабильного имени `"driver_reference"` b7 добавляет в конец `seed_drivers.py` (или в отдельный
SQL, подхватываемый b1) шаг:
`CREATE OR REPLACE TABLE "driver_reference" AS SELECT * FROM read_csv_auto('data/seed/driver_reference.csv', header=true)`.
Имя таблицы в API-слое — всегда `"driver_reference"` (не `seed__*`).

## Правка `enrichment.driver_for(plate)` (по согласованию с b2)

`driver_for(db, plate) -> {driver, driver_id, driver_phone}`:
1. **Сначала** `SELECT "driver_name","driver_id","driver_phone" FROM "driver_reference" WHERE "vehicle_plate"=?`.
2. **Иначе** (нет строки/нет таблицы) — fallback на синтетику по `crc32(plate)` (текущая логика §2).
Так «реальный» путь и демо-fallback сосуществуют; синтетика не ломается, если справочника ещё нет.

> Замена на внешний источник = **только** перегенерация `data/seed/driver_reference.csv` или смена
> загрузчика b7. API-схемы (`driver`, `driver_id`, `driver_phone`) **не меняются**.

## Check

- `python -m api.etl.seed_drivers` создаёт `data/seed/driver_reference.csv` с заголовком из 8 колонок.
- Повторный запуск даёт **идентичный** CSV (детерминизм по `crc32`).
- После `make db`: `SELECT count(*) FROM "driver_reference"` > 0; ровно одна строка на уникальный `vehicle_plate`.
- `safety_score` ∈ `[0, 100]` для всех строк; пул ФИО ≥20, регионов ≥5.
- `enrichment.driver_for(db, plate)` для plate из справочника возвращает имя из `driver_reference`;
  для отсутствующего plate — синтетику по `crc32` (без исключения).

## Edge cases / поведение

- **Идемпотентность сидов:** третий+ прогон `seed_drivers.py` не меняет ни `driver_reference.csv`, ни `driver_trips.csv` (побайтно), включая порядок строк (стабильная сортировка по `"vehicle_plate"`).
- **Ровно 1 строка на ТС:** `SELECT "vehicle_plate", count(*) FROM "driver_reference" GROUP BY 1 HAVING count(*)>1` → пусто; `driver_trips` допускает 1–2 строки на ТС (main + опц. secondary), вторичный — не дубль main (`driver_id` различны).
- **Диапазоны:** `safety_score` ∈ `[0,100]` даже при ТС без алярмов (нет строк → `safety_score=100`, без NaN/NULL); `trips≥0`, сумма `trips` по ТС в `driver_trips` не превышает рейсов ТС.
- **Отсутствие ТС / пустой источник:** нет уникальных пар в `"video_events__selected_video_alarms"` → CSV содержит только header, `CREATE OR REPLACE TABLE` даёт пустую таблицу (не падать); `driver_for` любого plate → синтетика.
- **Детерминизм CSV:** одинаковый `crc32(plate)` → одинаковые `driver_id`/`driver_name`/`driver_phone`/`region` между прогонами; пулы (`NAMES`/`REGIONS`) не пересортированы.
- **Стабильность таблицы:** имя в API-слое всегда `"driver_reference"` (не `seed__*`); `make db` повторно не плодит дублей строк (`CREATE OR REPLACE`).

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**; незакоммиченная
работа в worktree на барьер не попадёт:

```bash
git add -A && git commit -m "b7: <что сделано>"
```
