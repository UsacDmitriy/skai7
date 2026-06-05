-- b10 · View v_vehicle — контракт 00-CONTRACT.md §7.2 (идея #2 В-2/ТС, #10)
-- Карточка ТС: агрегаты алярмов за период + статус 3 канонических камер
-- (ADAS ch1 / DMS ch5 / СНЗ ch2|ch3) из "video_events__video_files".
-- Список водителей (1 ТС = N водителей) строится сервисом из "driver_trips" (не отсюда:
-- эта view — 1 строка на ТС). Модель ТС и risk_score (синтетика/формула §2) — в сервисе (§27).
-- Идемпотентность b1: DROP VIEW IF EXISTS.

DROP VIEW IF EXISTS "v_vehicle";
CREATE VIEW "v_vehicle" AS
WITH "cams" AS (
  -- статус канала ТС: «онлайн», если есть хоть один файл download_status='downloaded'.
  SELECT
    "unit_state_number"                                                        AS "vehicle_plate",
    max(CASE WHEN "channel" = 1 AND "download_status" = 'downloaded' THEN 1 ELSE 0 END) AS "cam_adas_ok",
    max(CASE WHEN "channel" = 5 AND "download_status" = 'downloaded' THEN 1 ELSE 0 END) AS "cam_dms_ok",
    max(CASE WHEN "channel" IN (2, 3) AND "download_status" = 'downloaded' THEN 1 ELSE 0 END) AS "cam_snz_ok"
  FROM "video_events__video_files"
  GROUP BY "unit_state_number"
)
SELECT
  i."vehicle_plate",
  any_value(i."unit_id")                                                       AS "unit_id",
  any_value(i."unit_name")                                                     AS "unit_name",
  count(*)                                                                     AS "period_alarms",
  count(*) FILTER (
    WHERE i."severity" = 'critical' OR i."alarm_code" IN ('OVERSPEED', 'DMS_SMOKING')
  )                                                                            AS "gross",
  count(*) FILTER (WHERE i."severity" = 'critical')                           AS "critical",
  max(i."speed_kmh")                                                          AS "max_speed_kmh",
  COALESCE(sum(i."mileage_km"), 0.0)                                          AS "mileage_km",
  COALESCE(c."cam_adas_ok", 0)                                                AS "cam_adas_ok",
  COALESCE(c."cam_dms_ok", 0)                                                 AS "cam_dms_ok",
  COALESCE(c."cam_snz_ok", 0)                                                 AS "cam_snz_ok",
  -- cameras_ok = число онлайн-слотов из 3 (сервис формирует строку "N/3").
  COALESCE(c."cam_adas_ok", 0) + COALESCE(c."cam_dms_ok", 0) + COALESCE(c."cam_snz_ok", 0) AS "cameras_online"
FROM "v_incidents" i
LEFT JOIN "cams" c
  ON c."vehicle_plate" = i."vehicle_plate"
GROUP BY
  i."vehicle_plate", c."cam_adas_ok", c."cam_dms_ok", c."cam_snz_ok";
