-- b12 · View v_reb — контракт 00-CONTRACT.md §7.2 (идея #8, РЭБ/GPS-разрывы)
-- Разрывы навигации (period_type=3 — потеря GPS) из "navigation__track_periods"
-- + соседние видимые периоды (period_index ±1 того же ТС/дня) для сшивки трека.
-- View отдаёт «сырое» по периодам: границы (start/end из точек), duration_sec,
-- флаг is_gap. Сборку gps_track/gap_periods/video_frames под §7.5 делает reb_service.
-- Идемпотентность b1: DROP VIEW IF EXISTS (повторный make db без дублей).

DROP VIEW IF EXISTS "v_reb";
CREATE VIEW "v_reb" AS
WITH "period_bounds" AS (
  -- Границы периода по его точкам трека (period_type=3 имеет 1-2 точки —
  -- хватает на start/end; основная длительность берётся из "period_duration").
  SELECT
    p."vehicle_id"        AS "vehicle_plate",
    p."public_unit_id"    AS "unit_id",
    p."date"              AS "date",
    p."period_index"      AS "period_index",
    p."period_type"       AS "period_type",
    p."period_duration"   AS "period_duration",
    min(tp."timestamp")   AS "start",
    max(tp."timestamp")   AS "end"
  FROM "navigation__track_periods" p
  LEFT JOIN "navigation__track_points" tp
    ON tp."public_unit_id" = p."public_unit_id"
   AND tp."date"           = p."date"
   AND tp."period_index"   = p."period_index"
  GROUP BY ALL
),
"gaps" AS (
  -- Разрывы: только потеря GPS (period_type=3).
  SELECT "vehicle_id" AS "vehicle_plate", "date", "period_index"
  FROM "navigation__track_periods"
  WHERE "period_type" = 3
)
SELECT
  b."vehicle_plate",
  b."unit_id",
  b."date",
  b."period_index",
  b."period_type",
  b."start",
  b."end",
  -- duration_sec из "HH:MM:SS" (длительность периода, ≥ 0).
  (
    CAST(list_element(string_split(b."period_duration", ':'), 1) AS BIGINT) * 3600
    + CAST(list_element(string_split(b."period_duration", ':'), 2) AS BIGINT) * 60
    + CAST(list_element(string_split(b."period_duration", ':'), 3) AS BIGINT)
  )                                                AS "duration_sec",
  (b."period_type" = 3)                            AS "is_gap"
FROM "period_bounds" b
-- Только разрывы и их непосредственные соседи (period_index ±1) того же ТС/дня.
WHERE EXISTS (
  SELECT 1 FROM "gaps" g
  WHERE g."vehicle_plate" = b."vehicle_plate"
    AND g."date"          = b."date"
    AND abs(g."period_index" - b."period_index") <= 1
)
ORDER BY b."vehicle_plate", b."date", b."period_index";
