-- w3-6 · View v_fuel — контракт 00-CONTRACT.md §9.2/§9.3 (аддендум волны 3)
-- Топливная сверка ЗИС vs карты: "fuel__fuel_vehicles" ⋈ агрегат
-- "fuel__fuel_reconciliation" по "vehicle_id". recon_status — ХУДШИЙ статус
-- сверки по ТС: missing_sensor_event > review > matched.
-- Колонки строго под FuelVehicleSummary (§9.2). Списки reconciliation/events
-- здесь НЕ материализуются — fuel_service читает их по "vehicle_id" напрямую.
-- Идемпотентность (повторный make db без дублей): DROP VIEW IF EXISTS.

DROP VIEW IF EXISTS "v_fuel";
CREATE VIEW "v_fuel" AS
WITH "recon_agg" AS (
  -- Худший статус сверки по ТС (ранг: missing_sensor_event > review > matched).
  SELECT
    "vehicle_id",
    CASE
      WHEN bool_or("status" = 'missing_sensor_event') THEN 'missing_sensor_event'
      WHEN bool_or("status" = 'review')               THEN 'review'
      ELSE 'matched'
    END AS "recon_status"
  FROM "fuel__fuel_reconciliation"
  GROUP BY "vehicle_id"
)
SELECT
  v."vehicle_id",
  v."model",
  v."vin",
  v."fuel_volume_zis_l",
  v."fuel_volume_card_l",
  v."volume_delta_zis_minus_card_l",          -- headline KPI
  v."refuel_count_zis",
  v."transaction_count_card",
  CAST(v."period_start" AS VARCHAR)           AS "period_start",
  CAST(v."period_end"   AS VARCHAR)           AS "period_end",
  -- ТС без строк сверки → matched (нет расхождений; recon_status ∈ enum §9.2).
  COALESCE(r."recon_status", 'matched')       AS "recon_status"
FROM "fuel__fuel_vehicles" v
LEFT JOIN "recon_agg" r
  ON r."vehicle_id" = v."vehicle_id"
ORDER BY v."vehicle_id";
