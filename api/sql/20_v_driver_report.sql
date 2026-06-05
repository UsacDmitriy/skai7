-- b10 · View v_driver_report — контракт 00-CONTRACT.md §7.2 (идея #2, В-1)
-- Алярмы и метрики по "vehicle_plate" поверх "v_incidents" (создаётся первым: 10_ < 20_).
-- «Сырое + агрегаты»: счётчики по severity/source, max(speed), доля ночных, суммарный
-- пробег, список alarm_code. risk_score/safety_score (формула §2) досчитывает сервис (§27).
-- Идемпотентность b1: DROP VIEW IF EXISTS в начале.
-- DuckDB-синтаксис: идентификаторы в двойных кавычках.

DROP VIEW IF EXISTS "v_driver_report";
CREATE VIEW "v_driver_report" AS
SELECT
  i."vehicle_plate",
  any_value(i."unit_id")                                                       AS "unit_id",
  count(*)                                                                     AS "total",
  count(*) FILTER (WHERE i."source" IN ('DMS', 'ADAS', 'COMBINED'))            AS "video_da",
  count(*) FILTER (WHERE i."source" = 'TELEMATICS')                            AS "telematics",
  -- gross (§7.5): critical ИЛИ OVERSPEED/DMS_SMOKING — тот же предикат, что в сервисе.
  count(*) FILTER (
    WHERE i."severity" = 'critical' OR i."alarm_code" IN ('OVERSPEED', 'DMS_SMOKING')
  )                                                                            AS "gross",
  count(*) FILTER (WHERE i."severity" = 'critical')                           AS "critical",
  count(*) FILTER (WHERE i."severity" = 'high')                               AS "high",
  count(*) FILTER (WHERE i."severity" = 'medium')                             AS "medium",
  count(*) FILTER (WHERE i."severity" = 'low')                                AS "low",
  max(i."speed_kmh")                                                          AS "max_speed_kmh",
  -- доля ночных: час локального времени из строки ts ('YYYY-MM-DD HH:...') ∈ [22,6).
  count(*) FILTER (
    WHERE CAST(substr(i."ts", 12, 2) AS INTEGER) >= 22
       OR CAST(substr(i."ts", 12, 2) AS INTEGER) < 6
  )                                                                            AS "night_count",
  COALESCE(sum(i."mileage_km"), 0.0)                                          AS "mileage_km",
  list(i."alarm_code")                                                        AS "alarm_codes"
FROM "v_incidents" i
GROUP BY i."vehicle_plate";
