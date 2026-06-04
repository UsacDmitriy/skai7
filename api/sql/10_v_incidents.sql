-- b3 · View v_incidents — контракт 00-CONTRACT.md §1.3
-- Одна строка на алярм (ровно 54). «Сырое + каталог», без enrichment-полей.
-- DuckDB-синтаксис: идентификаторы в двойных кавычках.

DROP VIEW IF EXISTS "v_incidents";
CREATE VIEW "v_incidents" AS
SELECT
  a."AlarmId"                       AS "id",
  a."Type"                          AS "alarm_type",
  c."code"                          AS "alarm_code",
  c."label_ru"                      AS "alarm_label_ru",
  c."source"                        AS "source",
  c."severity"                      AS "severity",
  c."severity"                      AS "risk_level",
  CAST(a."Begin" AS VARCHAR)        AS "ts",
  CAST(a."End" AS VARCHAR)          AS "ts_end",
  a."UnitStateNumber"               AS "vehicle_plate",
  a."UnitId"                        AS "unit_id",
  a."UnitName"                      AS "unit_name",
  CAST(a."Speed" AS DOUBLE)         AS "speed_kmh",
  a."Address"                       AS "address",
  tp."latitude"                     AS "lat",
  tp."longitude"                    AS "lon",
  a."VideoCount"                    AS "video_count",
  CASE WHEN a."VideoCount" > 0 THEN 1 ELSE 0 END AS "video_available",
  dms."media_relative_path"         AS "cam_dms_url",
  front."media_relative_path"       AS "cam_front_url",
  ts."total_mileage_km"             AS "mileage_km",
  CAST(ts."total_movement_duration" AS VARCHAR) AS "movement_duration"
FROM "video_events__selected_video_alarms" a
LEFT JOIN "alarm_type_catalog" c
  ON c."raw" = a."Type"
-- первая точка трека по алярму (MIN point_index)
LEFT JOIN (
  SELECT "alarm_id", "latitude", "longitude"
  FROM (
    SELECT
      "alarm_id",
      "latitude",
      "longitude",
      ROW_NUMBER() OVER (PARTITION BY "alarm_id" ORDER BY "point_index") AS "rn"
    FROM "video_events__track_points"
  )
  WHERE "rn" = 1
) tp ON tp."alarm_id" = a."AlarmId"
-- DMS-камера: channel=5
LEFT JOIN (
  SELECT "alarm_id", MIN("media_relative_path") AS "media_relative_path"
  FROM "video_events__video_files"
  WHERE "channel" = 5
  GROUP BY "alarm_id"
) dms ON dms."alarm_id" = a."AlarmId"
-- Фронтальная камера: channel=1
LEFT JOIN (
  SELECT "alarm_id", MIN("media_relative_path") AS "media_relative_path"
  FROM "video_events__video_files"
  WHERE "channel" = 1
  GROUP BY "alarm_id"
) front ON front."alarm_id" = a."AlarmId"
LEFT JOIN "video_events__track_summary" ts
  ON ts."alarm_id" = a."AlarmId";
