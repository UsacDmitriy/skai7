# W3-16 · AI-фундамент: ML-зависимости + `data/ai/`-кэш + `ai_metric_events` (подготовка Волны 4)

> Волна 3 · бэклог (**подготовка под Волну 4**). Трек **Backend/Data**. Против `00-CONTRACT.md` §8.0/§8.1/§8.7.
> **Модель:** 🔵 Sonnet — детерминированный каркас против контракта; гейт = секция Check.
> **Владеет:** `api/requirements.txt` (добавки), `data/ai/` (каталог + схема + placeholder),
> `api/etl/ai_cache_seed.py`, `api/sql/33_ai_metric_events.sql`. **Не блокирует** P0/P1/P2.
> Разблокирует **b16,b17,b18,b19,b20,b23,b25** (Волна 4) — даёт каркас, который они **дополняют**, не пересоздают.

## Контекст (подтверждённые блокеры)

- В `api/requirements.txt` нет ML-стека → `b18` (наивный фолбэк всё равно нужен, но IsolationForest-ветка),
  `b19` (DBSCAN) не импортируются.
- Нет каталога `data/ai/` (кэш сцены/погоды §8.1) → SQL-загрузчики `b16`/`b17` и фолбэк-путь негде запустить.
- Нет таблицы `ai_metric_events` (§8.7) → `b25` (метрики) и `b24` (мета-источник) некуда писать события.
- **Данные:** алярмы за 2 дня (§8.0) → кэш сцены/погоды держим как **детерминированный placeholder**
  (`b16`/`b17` перезаписывают реальными значениями; без них — корректный фолбэк, `bonus=0`).

## Что сделать

1. **ML-зависимости** (`api/requirements.txt`, дисциплина lazy-import как `groq` в `nlu_service`):
   `scikit-learn` (DBSCAN/IsolationForest), `statsmodels` (ARIMA-ветка b18, мёртвая на этих данных, но
   импорт не должен падать). Пометить комментарием «lazy: используется при наличии данных, иначе fallback».
2. **Каталог `data/ai/`**: `data/ai/.gitkeep` + `data/ai/README.md` со **схемой кэша** (§8.1: `scene_labels.json`,
   `weather_cache.json` — поля 1:1 контракту). В `.gitignore` `data/ai/*.json` **не** игнорировать (placeholder коммитим).
3. **Детерминированный placeholder-генератор** `api/etl/ai_cache_seed.py`: по 54 инцидентам из `v_incidents`
   пишет `data/ai/scene_labels.json` (`weather="unknown"`, `day_night` из часа `ts`, `road_surface/area/visibility="unknown"`,
   `scene_confidence=0.0`, `source="placeholder"`) и `data/ai/weather_cache.json` (`api_weather="unknown"`,
   `is_day` из часа, `discrepancy=false`, `discrepancy_kind="none"`). Без `Date.now()`/`random`. Идемпотентно.
   **Шапка файлов:** «placeholder Волны 3; b16/b17 перезаписывают VLM/Open-Meteo».
4. **`api/sql/33_ai_metric_events.sql`** — пустая таблица `ai_metric_events` (§8.7): `id, ts, feature_name,
   incident_id, plate, latency_ms, source ∈ {live,cache,fallback}, success, error_detail`. Идемпотентно
   (`CREATE TABLE IF NOT EXISTS`). `b25` пишет/агрегирует; `b24` помечает `source`.
5. **Толерантность сборки**: `make db` не падает при отсутствии/пустом `data/ai/*.json` (фолбэк-ветка §8.2).
   Если `30_/31_*.sql` ещё не созданы (b16/b17) — `33_*.sql` грузится независимо (лексикографически).

## Check

- `pip install -r api/requirements.txt` ставит `scikit-learn`/`statsmodels`; `python -c "import sklearn, statsmodels"` ок.
- `python api/etl/ai_cache_seed.py` создаёт `data/ai/scene_labels.json` и `weather_cache.json` по **54** строки,
  валидный JSON, схема §8.1; повтор → идентично (детерминизм).
- `make db` зелёный; `SELECT count(*) FROM ai_metric_events` = 0 (таблица есть, пустая); сборка не падает без кэша.
- `data/ai/README.md` описывает схему обоих кэшей; placeholder помечен «b16/b17 перезаписывают».

## Коммит (обязательно)

```bash
git add -A && git commit -m "w3-16: AI-фундамент (ML-deps + data/ai placeholder + ai_metric_events DDL)"
```
