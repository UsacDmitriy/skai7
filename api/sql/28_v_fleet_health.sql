-- w3-9 · View v_fleet_health — контракт 00-CONTRACT.md §9.0/§9.3/§9.6 (хаб «Здоровье парка»).
-- Объединение disjoint-популяций по НОРМАЛИЗОВАННОМУ госномеру: fuel ∪ sensors ∪ navigation.
--   fuel    — собственный ключ "fuel__fuel_vehicles.vehicle_id" (в reference__vehicle_matches
--             топлива НЕТ); vehicle_id у топлива и есть чистый госномер (§9.0).
--   sensors — "plate" = public_state_number из reference__vehicle_matches (sensors_bv), уже
--             резолвлен во v_sensors. ТС без резолва (plate IS NULL) НЕ кладётся в ростер:
--             его нельзя надёжно сматчить кросс-доменно (§9.0 «резолвятся через matches»).
--   nav     — "plate" = public_state_number из v_nav_problem (5 matched). Unmatched-ТС
--             (plate IS NULL) выпадает — он не кликабелен в РЭБ и не имеет общего ключа (§9.5).
-- Нормализация — ЕДИНАЯ для всех источников: upper(regexp_replace(<plate>, '\s', '', 'g')),
-- т.е. strip пробелов + верхний регистр (§9.0). Один и тот же public_state_number в sensors_bv
-- и navigation_problem → один plate_norm → строки честно схлопываются (has_sensors ∧ has_nav).
-- Итог: 10 fuel ⊎ 6 sensors-с-резолвом ⊎ 1 nav-only (О834МР193) = 17 ТС, 2 из них в видеопарке.
-- in_video_fleet: plate_norm ∈ норм. v_incidents.vehicle_plate (О802УЕ198, С725АТ159).
-- Отсутствующий домен → KPI = NULL (фронт рендерит «—», не ошибка, §9.5). reb_link_id — UUID
-- (public_unit_id), не «грязный лейбл». Идемпотентность b1: DROP VIEW IF EXISTS.

DROP VIEW IF EXISTS "v_fleet_health";
CREATE VIEW "v_fleet_health" AS
WITH "fuel_src" AS (
  -- Топливный остров: ключ = собственный vehicle_id (= чистый госномер).
  SELECT
    upper(regexp_replace("vehicle_id", '\s', '', 'g')) AS "plate_norm",
    "vehicle_id"                                        AS "plate",
    "volume_delta_zis_minus_card_l"                     AS "fuel_delta_l"
  FROM "v_fuel"
),
"sensors_src" AS (
  -- Только ТС с резолвленным госномером (plate IS NOT NULL) — иначе нет ключа объединения.
  SELECT
    upper(regexp_replace("plate", '\s', '', 'g'))      AS "plate_norm",
    "plate"                                             AS "plate",
    "distance_gap_odometer_minus_gps_km"               AS "sensors_gap_can_gps_km",
    "online_status"                                     AS "sensors_online_status"
  FROM "v_sensors"
  WHERE "plate" IS NOT NULL
),
"nav_src" AS (
  -- Только matched-ТС (plate IS NOT NULL); unmatched не кликабелен в РЭБ и без общего ключа.
  SELECT
    upper(regexp_replace("plate", '\s', '', 'g'))      AS "plate_norm",
    "plate"                                             AS "plate",
    "gap_count"                                         AS "nav_gap_count",
    "reb_link_id"                                       AS "reb_link_id"
  FROM "v_nav_problem"
  WHERE "plate" IS NOT NULL
),
"keys" AS (
  -- Объединение без дублей по нормализованному госномеру (UNION дедуплицирует).
  SELECT "plate_norm" FROM "fuel_src"
  UNION
  SELECT "plate_norm" FROM "sensors_src"
  UNION
  SELECT "plate_norm" FROM "nav_src"
),
"video" AS (
  -- Норм. госномера видеопарка для флага in_video_fleet (§9.0: ровно 2 пересечения).
  SELECT DISTINCT upper(regexp_replace("vehicle_plate", '\s', '', 'g')) AS "plate_norm"
  FROM "v_incidents"
  WHERE "vehicle_plate" IS NOT NULL
)
SELECT
  k."plate_norm",
  -- Дисплей-госномер: fuel disjoint, поэтому coalesce даёт чистый public_state_number у sensors/nav.
  coalesce(f."plate", s."plate", n."plate")            AS "plate",
  (f."plate_norm" IS NOT NULL)                         AS "has_fuel",
  (s."plate_norm" IS NOT NULL)                         AS "has_sensors",
  (n."plate_norm" IS NOT NULL)                         AS "has_nav",
  f."fuel_delta_l",                                    -- топливо Δ ЗИС−карта (NULL → «—»)
  s."sensors_gap_can_gps_km",                          -- пробег CAN−GPS (NULL → «нет данных»)
  s."sensors_online_status",                           -- online/stale/offline (NULL → «—»)
  n."nav_gap_count",                                   -- число разрывов GPS (NULL → «—»)
  n."reb_link_id",                                     -- = public_unit_id (UUID), вход в /api/reb/{id}
  (v."plate_norm" IS NOT NULL)                         AS "in_video_fleet"
FROM "keys" k
LEFT JOIN "fuel_src"    f ON f."plate_norm" = k."plate_norm"
LEFT JOIN "sensors_src" s ON s."plate_norm" = k."plate_norm"
LEFT JOIN "nav_src"     n ON n."plate_norm" = k."plate_norm"
LEFT JOIN "video"       v ON v."plate_norm" = k."plate_norm"
-- Детерминированный порядок: видеопарк сверху, дальше по норм. госномеру (стабильно при повторе).
ORDER BY (NOT (v."plate_norm" IS NOT NULL)), k."plate_norm";
