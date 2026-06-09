-- b16 · incident_scene — кэш VLM-контекста сцены (00-CONTRACT.md §8.1)
-- Источник: data/ai/scene_labels.json (предрасчёт api/etl/scene_precompute.py,
--   VLM по кадру ch1/ch5 оффлайн). Рантайм/`make db` НЕ требует VLM и сети.
-- Префикс 30_ — порядок после view (10_v_incidents). Плоский JSON-массив:
--   1 строка на видео-алярм (54), source ∈ {vlm,cache}.
-- COALESCE/CAST гарантируют типы и отсутствие NULL даже при «нет кадра».
-- DuckDB-синтаксис: идентификаторы в двойных кавычках.

CREATE OR REPLACE TABLE "incident_scene" AS
SELECT
  CAST("id" AS VARCHAR)                                  AS "id",
  COALESCE(CAST("weather" AS VARCHAR), 'unknown')        AS "weather",
  COALESCE(CAST("day_night" AS VARCHAR), 'night')        AS "day_night",
  COALESCE(CAST("road_surface" AS VARCHAR), 'unknown')   AS "road_surface",
  COALESCE(CAST("area" AS VARCHAR), 'unknown')           AS "area",
  COALESCE(CAST("visibility" AS VARCHAR), 'unknown')     AS "visibility",
  COALESCE(CAST("scene_confidence" AS DOUBLE), 0.0)      AS "scene_confidence",
  COALESCE(CAST("source" AS VARCHAR), 'cache')           AS "source"
FROM read_json_auto('data/ai/scene_labels.json');
