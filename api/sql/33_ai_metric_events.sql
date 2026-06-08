-- w3-16 · Таблица ai_metric_events — контракт 00-CONTRACT.md §8.7 (каркас под Волну 4).
-- Событийный лог AI-слоя: одна строка = один вызов AI-фичи (scene/forecast/zones/
-- fatigue/copilot/metrics…). Здесь только ПУСТОЙ DDL: b25 (metrics_service) пишет и
-- агрегирует события (recommendation_acceptance, copilot_tool_success, …), b24
-- (ai_runtime) проставляет "source" ∈ {live,cache,fallback}.
-- Идемпотентность: CREATE TABLE IF NOT EXISTS — повторный `make db` НЕ затирает
-- уже накопленные события (в отличие от view с DROP). Загружается независимо и
-- лексикографически: не зависит от 30_/31_*.sql (b16/b17), которых ещё нет.

CREATE TABLE IF NOT EXISTS "ai_metric_events" (
  "id"            VARCHAR,                       -- идентификатор события (генерит b25)
  "ts"            TIMESTAMP,                     -- момент вызова (детерминизм: пишется вызовом, не Date.now в логике view)
  "feature_name"  VARCHAR,                       -- scene|forecast|zones|fatigue|copilot|verdict|metrics
  "incident_id"   VARCHAR,                       -- nullable: алярм-контекст, если применимо
  "plate"         VARCHAR,                       -- nullable: ТС-контекст, если применимо
  "latency_ms"    INTEGER,                       -- длительность обработки запроса
  "source"        VARCHAR,                       -- live|cache|fallback (§8.6); проставляет b24
  "success"       BOOLEAN,                       -- успешен ли вызов
  "error_detail"  VARCHAR,                       -- nullable: текст ошибки при success=false
  CHECK ("source" IS NULL OR "source" IN ('live', 'cache', 'fallback'))
);
