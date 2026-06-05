# Волна 4.1 · Умное событие + прогнозы (AI-слой)

Первая под-волна Волны 4. Backend/data + дизайн-примитивы идут **параллельно** (окна 1 и 2), тесты —
в окне 3 после готовности модулей. Кодим против `00-CONTRACT.md` **§8**. Внешние API/VLM — **оффлайн
предрасчёт → кэш** (`data/ai/*.json` + `incident_scene`/`incident_weather`); рантайм читает кэш.

| Окно | Промпты (порядок) | Модель |
|---|---|---|
| 1 Backend | `b16` scene-context (предрасчёт VLM) → `b17` weather-crosscheck → enrichment ; `b18` risk-forecast ∥ `b19` geozone-risk ∥ `b20` fatigue-chain | b16/b18/b19 🔴 · b17/b20 🔵 |
| 2 Web | `d7` ai-primitives (`SceneContextChip`/`DiscrepancyBadge`/`ForecastSparkline`/`RiskHeatLayer`) | 🔵 Sonnet |
| 3 Tests | `per-feature/`: `tu-scene` ∥ `tu-weather` ∥ `tu-forecast` ∥ `tu-zones` ∥ `tu-fatigue` | 🔵 Sonnet |

Дальше → **Барьер 4.1** (`../barrier-4-1-smart-context/x6-smoke-context-forecast.md`).

> Каждый промпт заканчивается секцией `## Коммит` — merge на барьере берёт только коммиты.
