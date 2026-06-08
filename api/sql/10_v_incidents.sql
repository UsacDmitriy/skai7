-- b3 · View v_incidents — контракт 00-CONTRACT.md §1.3
-- Одна строка на алярм (55 = 54 видео-алярма + 1 seeded no-video, см. ниже).
-- w3-5: P0-набор содержит ≥1 no-video инцидент (CAMERA_TAMPER, VideoCount=0), чтобы
--   ветка empty-state + «Запросить архив» (§2/§3.1) была достижима в живых данных, а не
--   мёртвым кодом. Источник — детерминированная строка в selected_video_alarms.csv (без video_files).
-- DuckDB-синтаксис: идентификаторы в двойных кавычках.
--
-- b15 (Волна 2.1, hardening) — целостность спайна поверх b3:
--   * каждый LEFT JOIN даёт ≤1 строку на "alarm_id" (агрегаты / ROW_NUMBER()=1) → count(*) ≡ строкам алярмов (w3-5: 55) инвариант;
--   * детерминизм подзапросов: устойчивый tie-break, чтобы lat/lon/cam_* не «прыгали» между прогонами;
--   * трек берём строго из "video_events__track_points" (НЕ "navigation__track_points" — одноимённый суффикс после b1);
--   * null-safety: "video_available" ∈ {0,1} без NULL; числовые поля приведены к типам (без строковых артефактов CSV).

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
  CAST(tp."latitude" AS DOUBLE)     AS "lat",
  CAST(tp."longitude" AS DOUBLE)    AS "lon",
  a."VideoCount"                    AS "video_count",
  CASE WHEN a."VideoCount" > 0 THEN 1 ELSE 0 END AS "video_available",
  dms."media_relative_path"         AS "cam_dms_url",
  front."media_relative_path"       AS "cam_front_url",
  CAST(ts."total_mileage_km" AS DOUBLE) AS "mileage_km",
  CAST(ts."total_movement_duration" AS VARCHAR) AS "movement_duration"
FROM "video_events__selected_video_alarms" a
LEFT JOIN "alarm_type_catalog" c
  ON c."raw" = a."Type"
-- Первая точка трека по алярму. Коллизия имён: берём строго "video_events__track_points",
-- НЕ "navigation__track_points" (одноимённый суффикс существует после b1).
-- Детерминизм: (alarm_id, point_index) не уникальна (до 5 строк с разными lat/lon),
-- поэтому к "point_index" добавлен устойчивый total-order tie-break — ровно 1 строка на alarm_id.
LEFT JOIN (
  SELECT "alarm_id", "latitude", "longitude"
  FROM (
    SELECT
      "alarm_id",
      "latitude",
      "longitude",
      ROW_NUMBER() OVER (
        PARTITION BY "alarm_id"
        ORDER BY "point_index", "period_index", "period_type",
                 "timestamp_utc", "latitude", "longitude"
      ) AS "rn"
    FROM "video_events__track_points"
  )
  WHERE "rn" = 1
) tp ON tp."alarm_id" = a."AlarmId"
-- DMS-камера: channel=5 — MIN("media_relative_path") стабильно выбирает один кадр (≤1 строка на alarm_id).
LEFT JOIN (
  SELECT "alarm_id", MIN("media_relative_path") AS "media_relative_path"
  FROM "video_events__video_files"
  WHERE "channel" = 5
  GROUP BY "alarm_id"
) dms ON dms."alarm_id" = a."AlarmId"
-- Фронтальная камера: channel=1 — MIN("media_relative_path") стабильно (≤1 строка на alarm_id).
LEFT JOIN (
  SELECT "alarm_id", MIN("media_relative_path") AS "media_relative_path"
  FROM "video_events__video_files"
  WHERE "channel" = 1
  GROUP BY "alarm_id"
) front ON front."alarm_id" = a."AlarmId"
-- Сводка трека: гарантируем ≤1 строку на alarm_id через ROW_NUMBER()=1 (анти-размножение,
-- даже если в источнике появятся дубли) с устойчивым tie-break по raw_track_path.
LEFT JOIN (
  SELECT "alarm_id", "total_mileage_km", "total_movement_duration"
  FROM (
    SELECT
      "alarm_id",
      "total_mileage_km",
      "total_movement_duration",
      ROW_NUMBER() OVER (
        PARTITION BY "alarm_id"
        ORDER BY "event_begin_utc", "raw_track_path"
      ) AS "rn"
    FROM "video_events__track_summary"
  )
  WHERE "rn" = 1
) ts ON ts."alarm_id" = a."AlarmId";
