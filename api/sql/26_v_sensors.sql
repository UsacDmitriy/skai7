-- w3-7 · View v_sensors — контракт 00-CONTRACT.md §9.2/§9.3 (раскрытие тёмных
-- данных sensors, идея — расхождение пробега CAN(одометр) − GPS).
-- Сводка «одна строка = одно ТС» (7 шт.) под SensorVehicleSummary:
--   sensors__mileage_and_speed (база, 7 строк) ⋈ sensors__online_snapshot
--   ⋈ count(sensors__sensor_catalog) по public_unit_id,
--   LEFT JOIN reference__vehicle_matches (source_list='sensors_bv') → plate.
-- 959k sensors__graph_points и graph_status НЕ участвуют (§9.3, §1: большие
-- таблицы не держим в памяти приложения; динамику строим из daily_mileage).
-- Идемпотентность b1: DROP VIEW IF EXISTS (повторный make db без дублей).

DROP VIEW IF EXISTS "v_sensors";
CREATE VIEW "v_sensors" AS
WITH "sensor_counts" AS (
  -- Кол-во датчиков в каталоге по ТС (627 строк → агрегат по public_unit_id).
  SELECT "public_unit_id", count(*) AS "sensor_count"
  FROM "sensors__sensor_catalog"
  GROUP BY "public_unit_id"
),
"plate_match" AS (
  -- Чистый госномер из справочника матчей (sensors_bv). max() дедуплицирует
  -- на случай >1 строки на ТС; NULL у несматченного ТС остаётся NULL.
  SELECT "public_unit_id", max("public_state_number") AS "plate"
  FROM "reference__vehicle_matches"
  WHERE "source_list" = 'sensors_bv'
  GROUP BY "public_unit_id"
)
SELECT
  m."public_unit_id",
  m."vehicle_id"                            AS "vehicle_label",
  pm."plate"                                AS "plate",
  m."gps_total_distance_km",
  m."distance_odometer_km",                                 -- CAN-одометр (может быть NULL)
  m."distance_gap_odometer_minus_gps_km",                   -- CAN−GPS KPI (NULL → «нет данных»)
  m."max_speed_kmh",
  m."average_speed_kmh",
  s."satellite_amount",
  -- online_status: сравнение last_valid_navigation_timestamp с timestamp_utc
  -- строки снапшота (НЕ Date.now()); NULL → stale. Свежий валидный фикс
  -- (≤10 мин до снапшота) → online, иначе фикс устарел → offline.
  CASE
    WHEN s."last_valid_navigation_timestamp" IS NULL THEN 'stale'
    WHEN abs(date_diff('second',
                       s."last_valid_navigation_timestamp",
                       s."timestamp_utc")) <= 600 THEN 'online'
    ELSE 'offline'
  END                                       AS "online_status",
  coalesce(sc."sensor_count", 0)            AS "sensor_count"
FROM "sensors__mileage_and_speed" m
LEFT JOIN "sensors__online_snapshot" s ON s."public_unit_id" = m."public_unit_id"
LEFT JOIN "sensor_counts"           sc ON sc."public_unit_id" = m."public_unit_id"
LEFT JOIN "plate_match"             pm ON pm."public_unit_id" = m."public_unit_id"
ORDER BY m."vehicle_id";
