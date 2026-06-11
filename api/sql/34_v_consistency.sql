-- b28 · v_consistency_checks — слой доверия к данным (00-CONTRACT.md §10.1–§10.3).
-- Одна строка = одна детерминированная кросс-датасетная проверка целостности:
--   "check_id", "affected_count", "total". Статусы/ratio считает СЕРВИС (§10.2), не SQL.
-- 7 канонических проверок (§10.3), по CTE на каждую. Это НЕ AI-фича: чистый SQL
-- поверх существующих таблиц DuckDB, без сети/ML. Тоталы считаются запросом (не хардкод).
-- Идемпотентно: CREATE OR REPLACE VIEW — повторный `make db` пересоздаёт view.
-- Префикс 34_ — после таблиц/view ETL (b1) и AI-слоя (33_). DuckDB: идентификаторы в кавычках.
--
-- alarms = video_events__selected_video_alarms; track_points = video_events__track_points.

CREATE OR REPLACE VIEW "v_consistency_checks" AS
WITH
-- 1. ТС из alarms, по чьему госномеру нет ни одной точки трека (пробел телематики).
video_fleet_no_track AS (
  SELECT 'video_fleet_no_track' AS "check_id",
         COUNT(*) FILTER (WHERE tp.unit_state_number IS NULL) AS "affected_count",
         COUNT(*) AS "total"
  FROM (SELECT DISTINCT "UnitStateNumber" AS usn
        FROM video_events__selected_video_alarms) a
  LEFT JOIN (SELECT DISTINCT unit_state_number
             FROM video_events__track_points) tp
    ON a.usn = tp.unit_state_number
),
-- 2. Алармы с VideoCount > 0, но без строк в video_files (пробел доказательной базы — кейс Фомина).
incident_no_video AS (
  SELECT 'incident_no_video' AS "check_id",
         COUNT(*) FILTER (WHERE vf.alarm_id IS NULL) AS "affected_count",
         COUNT(*) AS "total"
  FROM video_events__selected_video_alarms a
  LEFT JOIN (SELECT DISTINCT alarm_id FROM video_events__video_files) vf
    ON CAST(a."AlarmId" AS VARCHAR) = CAST(vf.alarm_id AS VARCHAR)
  WHERE CAST(a."VideoCount" AS INTEGER) > 0
),
-- 3. ТС с более чем одним TerminalId — источник дублей на карте (кейс Маслова/Балтики).
terminal_duplication AS (
  SELECT 'terminal_duplication' AS "check_id",
         COUNT(*) FILTER (WHERE n_terminals > 1) AS "affected_count",
         COUNT(*) AS "total"
  FROM (SELECT "UnitStateNumber",
               COUNT(DISTINCT "TerminalId") AS n_terminals
        FROM video_events__selected_video_alarms
        GROUP BY "UnitStateNumber")
),
-- 4. Покрытие справочника госномеров: доля строк, не сматченных по источникам (fuel/sensors/navigation).
plate_match_coverage AS (
  SELECT 'plate_match_coverage' AS "check_id",
         COUNT(*) FILTER (WHERE match_status <> 'matched') AS "affected_count",
         COUNT(*) AS "total"
  FROM reference__vehicle_matches
),
-- 5. Алармы, где timestamp_utc убывает при росте point_index (битый порядок точек трека).
timestamp_monotonicity AS (
  SELECT 'timestamp_monotonicity' AS "check_id",
         COUNT(DISTINCT alarm_id) FILTER (WHERE is_decreasing) AS "affected_count",
         COUNT(DISTINCT alarm_id) AS "total"
  FROM (SELECT alarm_id,
               timestamp_utc < LAG(timestamp_utc)
                 OVER (PARTITION BY alarm_id ORDER BY point_index) AS is_decreasing
        FROM video_events__track_points)
),
-- 6. Координаты вне здравого смысла: NULL/пустые/вне ±90/±180/(0,0) в alarms и track_points.
--    alarms."Latitude"/"Longitude" — VARCHAR (могут быть пустыми → не валят view, попадают сюда).
coordinate_rows AS (
  SELECT TRY_CAST(NULLIF("Latitude", '') AS DOUBLE) AS lat,
         TRY_CAST(NULLIF("Longitude", '') AS DOUBLE) AS lon
  FROM video_events__selected_video_alarms
  UNION ALL
  SELECT latitude AS lat, longitude AS lon
  FROM video_events__track_points
),
coordinate_sanity AS (
  SELECT 'coordinate_sanity' AS "check_id",
         COUNT(*) FILTER (
           WHERE lat IS NULL OR lon IS NULL
              OR lat < -90 OR lat > 90 OR lon < -180 OR lon > 180
              OR (lat = 0 AND lon = 0)
         ) AS "affected_count",
         COUNT(*) AS "total"
  FROM coordinate_rows
),
-- 7. Расхождение скоростей видео↔телематика. b29 заменяет эту CTE-заглушку на агрегат
--    v_speed_check (доля алармов с agreement='major'). До b29 view нет → нейтральный 0/0.
speed_disagreement AS (
  SELECT 'speed_disagreement' AS "check_id",
         0 AS "affected_count",
         0 AS "total"
)
SELECT "check_id", "affected_count", "total" FROM video_fleet_no_track
UNION ALL SELECT "check_id", "affected_count", "total" FROM incident_no_video
UNION ALL SELECT "check_id", "affected_count", "total" FROM terminal_duplication
UNION ALL SELECT "check_id", "affected_count", "total" FROM plate_match_coverage
UNION ALL SELECT "check_id", "affected_count", "total" FROM timestamp_monotonicity
UNION ALL SELECT "check_id", "affected_count", "total" FROM coordinate_sanity
UNION ALL SELECT "check_id", "affected_count", "total" FROM speed_disagreement;
