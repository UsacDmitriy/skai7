-- b17 · incident_weather — кросс-проверка погоды (00-CONTRACT.md §8.2)
-- Источник: data/ai/weather_cache.json (предрасчёт api/etl/weather_precompute.py,
--   Open-Meteo historical + solar elevation). Рантайм/`make db` НЕ требует сети.
-- JOIN с incident_scene (b16) → discrepancy / discrepancy_kind.
-- discrepancy_kind ∈ {weather, daynight, none}:
--   weather  — scene.weather∈{rain,snow} ↔ api_weather=clear (или наоборот)
--   daynight — scene.day_night=night И is_day=true
--   none     — расхождений нет / недостаточно данных для сравнения
-- Порядок: weather-приоритет перед daynight (аналог severity-cascade).
-- DuckDB-синтаксис: идентификаторы в двойных кавычках.

CREATE OR REPLACE TABLE "incident_weather" AS
WITH "raw" AS (
  SELECT
    CAST("id"                 AS VARCHAR)  AS "id",
    CAST("ts"                 AS VARCHAR)  AS "ts",
    CAST("lat"                AS DOUBLE)   AS "lat",
    CAST("lon"                AS DOUBLE)   AS "lon",
    COALESCE(CAST("api_weather"       AS VARCHAR), 'unknown') AS "api_weather",
    CAST("api_precip_mm"      AS DOUBLE)   AS "api_precip_mm",
    CAST("api_visibility_m"   AS DOUBLE)   AS "api_visibility_m",
    COALESCE(CAST("is_day"    AS BOOLEAN), false)             AS "is_day",
    CAST("solar_elevation_deg" AS DOUBLE)  AS "solar_elevation_deg"
  FROM read_json_auto('data/ai/weather_cache.json')
)
SELECT
  r."id",
  r."ts",
  r."lat",
  r."lon",
  r."api_weather",
  r."api_precip_mm",
  r."api_visibility_m",
  r."is_day",
  r."solar_elevation_deg",
  -- discrepancy: true если сцена противоречит данным API
  CASE
    WHEN (s."weather" IN ('rain', 'snow') AND r."api_weather" = 'clear')
      OR (s."weather" = 'clear' AND r."api_weather" IN ('rain', 'snow'))
      THEN true
    WHEN s."day_night" = 'night' AND r."is_day" = true
      THEN true
    ELSE false
  END AS "discrepancy",
  -- discrepancy_kind: weather > daynight > none
  CASE
    WHEN (s."weather" IN ('rain', 'snow') AND r."api_weather" = 'clear')
      OR (s."weather" = 'clear' AND r."api_weather" IN ('rain', 'snow'))
      THEN 'weather'
    WHEN s."day_night" = 'night' AND r."is_day" = true
      THEN 'daynight'
    ELSE 'none'
  END AS "discrepancy_kind"
FROM "raw" r
LEFT JOIN "incident_scene" s ON s."id" = r."id";
