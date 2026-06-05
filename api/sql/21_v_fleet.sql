-- b10 · View v_fleet — контракт 00-CONTRACT.md §7.2 (идея #2, В-2)
-- Агрегаты по парку в гранулярности «1 строка = 1 ТС»; оба разреза отчёта
-- (по водителям / по ТС) строятся сервисом поверх этих строк (1 ТС = 1 основной
-- водитель из "driver_reference"). Итоги по парку (кол-во ТС/водителей) — в сервисе.
-- «Сырое + агрегаты»: risk_score (формула §2) досчитывает сервис (§27).
-- Идемпотентность b1: DROP VIEW IF EXISTS.

DROP VIEW IF EXISTS "v_fleet";
CREATE VIEW "v_fleet" AS
SELECT
  i."vehicle_plate",
  any_value(i."unit_id")                                                       AS "unit_id",
  -- основной водитель ТС из справочника (§7.1); LEFT JOIN — ТС без записи не теряется.
  dr."driver_id",
  dr."driver_name",
  dr."department",
  dr."region",
  dr."safety_score",
  count(*)                                                                     AS "total",
  count(*) FILTER (
    WHERE i."severity" = 'critical' OR i."alarm_code" IN ('OVERSPEED', 'DMS_SMOKING')
  )                                                                            AS "gross",
  count(*) FILTER (WHERE i."source" IN ('DMS', 'ADAS', 'COMBINED'))            AS "video_da",
  count(*) FILTER (WHERE i."source" = 'TELEMATICS')                            AS "telematics",
  count(*) FILTER (WHERE i."severity" = 'critical')                           AS "critical",
  max(i."speed_kmh")                                                          AS "max_speed_kmh",
  COALESCE(sum(i."mileage_km"), 0.0)                                          AS "mileage_km"
FROM "v_incidents" i
LEFT JOIN "driver_reference" dr
  ON dr."vehicle_plate" = i."vehicle_plate"
GROUP BY
  i."vehicle_plate", dr."driver_id", dr."driver_name",
  dr."department", dr."region", dr."safety_score";
