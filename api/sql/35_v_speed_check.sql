-- b29 · v_speed_check — кросс-сверка скоростей событие↔GPS-трек (00-CONTRACT.md §10.2/§10.3).
-- Одна строка = один аларм. Сравнивает скорость из события аларма ("Speed") и скорость
-- ближайшей по времени точки GPS-трека (окно ±10 с от event_begin_utc).
-- ASSUMPTION (§10.2): CAN-скорости в датасете нет → источник истины GPS-трек
--   (track_points.speed_kmh), truth_source='gps_track'. delta/agreement считает СЕРВИС.
-- Окно ищем оконной функцией (row_number по |Δt|), НЕ ASOF JOIN — детерминированнее.
-- ⚠️ alarm_id в источниках бывает число/строка → обе стороны JOIN приводим к VARCHAR.
-- Идемпотентно: CREATE OR REPLACE VIEW. Префикс 35_ — после 34_ (b28). DuckDB: кавычки.
--
-- alarms = video_events__selected_video_alarms; LEFT JOIN'ы ничего не теряют → строк = числу алармов.

CREATE OR REPLACE VIEW "v_speed_check" AS
WITH nearest AS (
  SELECT alarm_id,
         speed_kmh,
         timestamp_utc,
         row_number() OVER (
           PARTITION BY alarm_id
           ORDER BY abs(epoch(timestamp_utc) - epoch(event_begin_utc))
         ) AS rn,
         abs(epoch(timestamp_utc) - epoch(event_begin_utc)) AS dist_s
  FROM video_events__track_points
)
SELECT CAST(a."AlarmId" AS VARCHAR)                              AS "id",
       CAST(NULLIF(CAST(a."Speed" AS VARCHAR), '') AS DOUBLE)    AS "event_speed_kmh",
       CASE WHEN n.dist_s <= 10 THEN n.speed_kmh END             AS "track_speed_kmh",
       m.max_speed_kmh                                           AS "max_track_speed_kmh"
FROM video_events__selected_video_alarms a
LEFT JOIN nearest n
  ON n.alarm_id = CAST(a."AlarmId" AS VARCHAR) AND n.rn = 1
LEFT JOIN (SELECT alarm_id, max(speed_kmh) AS max_speed_kmh
           FROM video_events__max_speed_points
           GROUP BY alarm_id) m
  ON m.alarm_id = CAST(a."AlarmId" AS VARCHAR);
