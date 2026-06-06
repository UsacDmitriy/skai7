# Волна 4.1 · Умное событие + прогнозы (AI-слой)

Первая под-волна Волны 4. Backend/data + дизайн-примитивы идут **параллельно** (окна 1 и 2), тесты —
в окне 3 после готовности модулей. Кодим против `00-CONTRACT.md` **§8**. Внешние API/VLM — **оффлайн
предрасчёт → кэш** (`data/ai/*.json` + `incident_scene`/`incident_weather`); рантайм читает кэш.

| Окно | Промпты (порядок) | Модель |
|---|---|---|
| 1 Backend | `b24` ai-governance (флаги/latency/кэш — **runtime-основа** для всех AI-фич, §8.6) → `b16` scene-context (предрасчёт VLM) → `b17` weather-crosscheck → enrichment ; `b18` risk-forecast ∥ `b19` geozone-risk ∥ `b20` fatigue-chain | b24/b17/b20 🔵 · b16/b18/b19 🔴 |
| 2 Web | `d7` ai-primitives (`SceneContextChip`/`DiscrepancyBadge`/`ForecastSparkline`/`RiskHeatLayer`) | 🔵 Sonnet |
| 3 Tests | `per-feature/`: `tu-scene` ∥ `tu-weather` ∥ `tu-forecast` ∥ `tu-zones` ∥ `tu-fatigue` | 🔵 Sonnet |

> **Подготовка Волны 3 (обязательна перед стартом):** ML-зависимости + `data/ai/`-кэш + типы/фикстуры +
> CI-каркас уже влиты (`wave-3-backlog/` w3-16…w3-19). **Данные:** алярмы только за 2 дня → `b18` —
> детерминированный fallback (без ARIMA), `b20` — честный empty-state на разреженных цепочках (§8.0).

Дальше → **Барьер 4.1** (`../barrier-4-1-smart-context/x6-smoke-context-forecast.md`).

> Каждый промпт заканчивается секцией `## Коммит` — merge на барьере берёт только коммиты.
