# b3 · SQL view v_incidents

> Трек **Backend/Data**. Против `00-CONTRACT.md` §1.3. **Владеет:** `api/sql/10_v_incidents.sql`.
> **Исполнение:** owner-only gate — Claude/Codex; ClinePass excluded from shared contracts, integration, deterministic acceptance, and commit — высокие ставки: интеграция / синк / алгоритм / анти-регресс / killer-feature / барьер.
> View `v_incidents` по контракту §1.3 (DuckDB-синтаксис; ранний SQLite-прототип портирован).

## Цель

Чистый SQL-файл с view `v_incidents` — одна строка на алярм (ровно 54), «сырое + каталог».
Колонки обогащения (driver/risk_score/…) здесь **НЕ** добавляем — их считает сервис (b5) через enrichment (b2).

## Требования

1. Файл `api/sql/10_v_incidents.sql`. Префикс `10_` — порядок выполнения в b1.
2. Структура:
   ```sql
   DROP VIEW IF EXISTS "v_incidents";
   CREATE VIEW "v_incidents" AS
   SELECT
     a."AlarmId"          AS "id",
     a."Type"             AS "alarm_type",
     c."code"             AS "alarm_code",
     c."label_ru"         AS "alarm_label_ru",
     c."source"           AS "source",
     c."severity"         AS "severity",
     c."severity"         AS "risk_level",
     a."Begin"            AS "ts",
     a."End"              AS "ts_end",
     a."UnitStateNumber"  AS "vehicle_plate",
     a."UnitId"           AS "unit_id",
     a."UnitName"         AS "unit_name",
     a."Speed"            AS "speed_kmh",
     a."Address"          AS "address",
     tp."latitude"        AS "lat",
     tp."longitude"       AS "lon",
     a."VideoCount"       AS "video_count",
     CASE WHEN a."VideoCount" > 0 THEN 1 ELSE 0 END AS "video_available",
     dms."media_relative_path"   AS "cam_dms_url",
     front."media_relative_path" AS "cam_front_url",
     ts."total_mileage_km"        AS "mileage_km",
     ts."total_movement_duration" AS "movement_duration"
   FROM "video_events__selected_video_alarms" a
   LEFT JOIN "alarm_type_catalog" c ON c."raw" = a."Type"
   LEFT JOIN ( /* первая точка трека по алярму */ ) tp   ON tp."alarm_id" = a."AlarmId"
   LEFT JOIN ( /* MIN(media_relative_path) WHERE channel=5 */ ) dms   ON dms."alarm_id" = a."AlarmId"
   LEFT JOIN ( /* MIN(media_relative_path) WHERE channel=1 */ ) front ON front."alarm_id" = a."AlarmId"
   LEFT JOIN "video_events__track_summary" ts ON ts."alarm_id" = a."AlarmId";
   ```
3. Подзапросы (чтобы остаться 54 строки):
   - `tp`: первая точка по `MIN("point_index")` (или `ROW_NUMBER() OVER (PARTITION BY "alarm_id" ORDER BY "point_index")=1`) из `video_events__track_points` → `latitude/longitude`.
   - `dms`/`front`: `SELECT "alarm_id", MIN("media_relative_path") AS "media_relative_path" FROM "video_events__video_files" WHERE "channel"=5/1 GROUP BY "alarm_id"`.
4. DuckDB-синтаксис: идентификаторы в двойных кавычках; типы приводить при необходимости (`CAST(a."Speed" AS DOUBLE)`).

## Check (после прогона b1)

- `SELECT count(*) FROM "v_incidents"` = 54.
- Для DMS-алярмов `cam_dms_url` непуст; `lat/lon` заполнены там, где есть трек.
- Колонок ровно как в §1.3 (без enrichment-полей).
