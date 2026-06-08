# tu-metrics · Unit-тесты метрик/data-quality (идея #18, модуль b25)

> Трек **Tests** (`feat/tests`, окно 3). Против `00-CONTRACT.md` §8.7.
> **Модель:** 🔵 Sonnet — детерминированная агрегация против контракта; гейт = pytest.
> **Владеет:** `api/tests/unit/test_metrics.py`. Инфра — из `t1`. Гонится после `b25`.

## Цель

Покрыть детерминированную агрегацию KPI и качество данных без сети (на тестовых событиях/таблицах).

## Состав — `api/tests/unit/test_metrics.py`

- `AiMetrics`: `recommendation_acceptance`/`copilot_tool_success`/`weather_mismatch_rate`/`zone_hit_rate` —
  считаются детерминированно на наборе `ai_metric_events`; повтор → идентично.
- Пустые события → нулевые/корректные дефолты (не падает, не делит на ноль).
- `DataQuality`: `camera_offline_ratio`/`missing_gps_ratio`/`missing_media_ratio`/`incidents_with_video_ratio`
  ∈ [0,1], считаются из `v_incidents`/`incident_*`.

## Check

- `pytest api/tests/unit/test_metrics.py -q` зелёный без сети.
- Все `*_ratio ∈ [0,1]`; пустой набор событий обработан; детерминизм агрегации.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
git add -A && git commit -m "tu-metrics: <что сделано>"
```
