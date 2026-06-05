-- b11 · View v_sabotage — контракт 00-CONTRACT.md §7.2/§7.5 (идея #9)
-- Детектор саботажа камеры: корреляция «камера ослеплена/закрыта» с фактом движения ТС.
-- Если DMS-канал тёмный (нет доступного кадра channel=5) ИЛИ алярм CAMERA_TAMPER,
-- а ТС едет (speed_kmh>0) — водитель, вероятно, заклеил/закрыл камеру.
--
-- Колонки под схему SabotageEvent (§7.5): id, vehicle_plate, ts, dms_dark, speed_kmh, video_url.
-- driver_name НЕ материализуем — досчитывает сервис через driver_reference (§7.1, b7).
-- DuckDB-синтаксис: идентификаторы в двойных кавычках. Идемпотентность b1: DROP VIEW IF EXISTS.

DROP VIEW IF EXISTS "v_sabotage";
CREATE VIEW "v_sabotage" AS
WITH "dms" AS (
  -- DMS-кадр доступен, если есть хоть один файл channel=5 со статусом 'downloaded'.
  -- ≤1 строка на alarm_id (GROUP BY) — анти-размножение спайна.
  SELECT "alarm_id"
  FROM "video_events__video_files"
  WHERE "channel" = 5 AND "download_status" = 'downloaded'
  GROUP BY "alarm_id"
),
"trk" AS (
  -- Скорость движения по алярму из трека (макс. по точкам). ≤1 строка на alarm_id.
  SELECT "alarm_id", max("speed_kmh") AS "track_speed_kmh"
  FROM "video_events__track_points"
  GROUP BY "alarm_id"
),
"vid" AS (
  -- video_url доступного канала: приоритет DMS(5) → ADAS/фронт(1) → доп.(2,3).
  -- ROW_NUMBER()=1 гарантирует ≤1 строку на alarm_id; MIN-tie-break — детерминизм.
  SELECT "alarm_id", "media_relative_path"
  FROM (
    SELECT
      "alarm_id",
      "media_relative_path",
      ROW_NUMBER() OVER (
        PARTITION BY "alarm_id"
        ORDER BY
          CASE "channel" WHEN 5 THEN 0 WHEN 1 THEN 1 WHEN 2 THEN 2 WHEN 3 THEN 3 ELSE 9 END,
          "media_relative_path"
      ) AS "rn"
    FROM "video_events__video_files"
    WHERE "download_status" = 'downloaded' AND "media_relative_path" IS NOT NULL
  )
  WHERE "rn" = 1
)
SELECT
  a."AlarmId"                                           AS "id",
  a."UnitStateNumber"                                   AS "vehicle_plate",
  CAST(a."Begin" AS VARCHAR)                            AS "ts",
  -- Тёмный DMS = нет доступного кадра channel=5.
  CASE WHEN dms."alarm_id" IS NULL THEN TRUE ELSE FALSE END AS "dms_dark",
  CAST(COALESCE(trk."track_speed_kmh", a."Speed", 0) AS DOUBLE) AS "speed_kmh",
  vid."media_relative_path"                             AS "video_url"
FROM "video_events__selected_video_alarms" a
LEFT JOIN "alarm_type_catalog" c ON c."raw" = a."Type"
LEFT JOIN "dms" ON dms."alarm_id" = a."AlarmId"
LEFT JOIN "trk" ON trk."alarm_id" = a."AlarmId"
LEFT JOIN "vid" ON vid."alarm_id" = a."AlarmId"
-- Событие саботажа = (тёмный DMS ИЛИ CAMERA_TAMPER) И движение (speed_kmh>0). Оба обязательны.
WHERE (dms."alarm_id" IS NULL OR c."code" = 'CAMERA_TAMPER')
  AND COALESCE(trk."track_speed_kmh", a."Speed", 0) > 0;
