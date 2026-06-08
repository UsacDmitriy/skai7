-- w3-8 · View v_nav_problem — контракт 00-CONTRACT.md §9.2/§9.3 (Волна 3, аддендум).
-- Список проблемных треков навигации → вход в существующий /api/reb/{id} (§7.4, b12).
-- navigation__navigation_problem_vehicles (5 matched + 1 unmatched) LEFT JOIN агрегат
-- разрывов navigation__track_periods по public_unit_id (gap = period_type=3 = потеря GPS;
-- длительность парсится из "HH:MM:SS" как в 24_v_reb.sql). reb_link_id = public_unit_id
-- (UUID есть в обеих таблицах; track_periods.vehicle_id хранит «грязный» лейбл
-- `С725АТ159(ТМ)` ≠ чистый public_state_number — поэтому связь по UUID). У unmatched-ТС
-- public_unit_id=null → reb_link_id=null (строка не кликабельна в РЭБ, §9.5).
-- in_video_fleet считает сервис (plate норм. ∈ v_incidents.vehicle_plate).
-- Идемпотентность b1: DROP VIEW IF EXISTS (повторный make db без дублей).

DROP VIEW IF EXISTS "v_nav_problem";
CREATE VIEW "v_nav_problem" AS
WITH "period_agg" AS (
  -- Агрегат периодов трека по ТС: число разрывов GPS и суммарная их длительность.
  SELECT
    "public_unit_id",
    count(*) FILTER (WHERE "period_type" = 3)        AS "gap_count",
    count(*)                                         AS "total_periods",
    -- Сумма длительностей разрывов из "HH:MM:SS" (только period_type=3), ≥ 0.
    coalesce(sum(
      CASE WHEN "period_type" = 3 THEN
        CAST(list_element(string_split("period_duration", ':'), 1) AS BIGINT) * 3600
        + CAST(list_element(string_split("period_duration", ':'), 2) AS BIGINT) * 60
        + CAST(list_element(string_split("period_duration", ':'), 3) AS BIGINT)
      ELSE 0 END
    ), 0)                                            AS "total_gap_duration_sec"
  FROM "navigation__track_periods"
  GROUP BY "public_unit_id"
)
SELECT
  pv."public_unit_id"                          AS "public_unit_id",
  pv."public_state_number"                     AS "plate",            -- чистый госномер (null у unmatched)
  pv."source_vehicle"                          AS "vehicle_label",    -- «грязный» лейбл (есть всегда)
  pv."normalized_vehicle"                      AS "plate_norm",       -- норм. ключ для get-матчинга
  pv."public_brand"                            AS "brand",
  pv."problem_description"                     AS "problem_description",
  pv."match_status"                            AS "match_status",
  coalesce(pa."gap_count", 0)                  AS "gap_count",
  coalesce(pa."total_periods", 0)              AS "total_periods",
  coalesce(pa."total_gap_duration_sec", 0)     AS "total_gap_duration_sec",
  pv."public_unit_id"                          AS "reb_link_id"       -- = public_unit_id; null у unmatched
FROM "navigation__navigation_problem_vehicles" pv
LEFT JOIN "period_agg" pa ON pa."public_unit_id" = pv."public_unit_id"
-- matched сверху, дальше детерминированно по чистому госномеру и UUID.
ORDER BY (pv."match_status" <> 'matched'), pv."public_state_number" NULLS LAST, pv."public_unit_id" NULLS LAST;
