# b25 · AI-метрики + data-quality (по research-отчёту)

> Трек **Backend/Data**. Против `00-CONTRACT.md` §8.7. **Владеет:** `api/services/metrics_service.py`,
> роутер `api/routers/metrics.py` (в `ALL_ROUTERS`), таблица `ai_metric_events`.
> **Модель:** 🔵 Sonnet — детерминированная агрегация/событийная запись; гейт = тесты.
> **Волна 4.3** (AI Ops & Trust), окно 1 (backend). Зависит от: AI-эндпоинты 4.1/4.2 (источники событий),
> enrichment; **таблица `ai_metric_events` создаётся пустой в prep `w3-16`** (этот промпт пишет/агрегирует).

## Цель

Закрыть «измеримость»: `GET /api/metrics/ai` (KPI AI-слоя) и `GET /api/metrics/data-quality` (доверие к
данным) — чтобы фичи можно было защитить перед заказчиком/руководством, а не только показать.

## Состав

- `ai_metric_events` — аддитивная событийная таблица (пишут эндпоинты/UI: показ рекомендации, accept/reject,
  вызов tool копилота, открытие зоны и т.п.).
- `GET /api/metrics/ai` → `AiMetrics` (§8.7): `recommendation_acceptance`, `copilot_tool_success`,
  `weather_mismatch_rate`, `zone_hit_rate`, `avg_time_to_triage`, `forecast_coverage`. Детерминированная агрегация.
- `GET /api/metrics/data-quality` → `DataQuality` (§8.7): `camera_offline_ratio`, `missing_gps_ratio`,
  `missing_media_ratio`, `weather_mismatch_rate`, `incidents_with_video_ratio` — из `v_incidents`/`incident_*`.

## Check

- `GET /api/metrics/ai` → 200 `AiMetrics`; значения детерминированы на тестовом наборе событий.
- `GET /api/metrics/data-quality` → 200 `DataQuality`; `*_ratio ∈ [0,1]`; считается из реальных таблиц.
- Пустые события → нулевые/корректные дефолты, не падает.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
git add -A && git commit -m "b25: <что сделано>"
```
