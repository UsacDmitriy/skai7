# `data/ai/` — оффлайн-кэш AI-слоя (Волна 4, каркас w3-16)

Кэш-файлы предрасчёта AI-слоя (§8 контракта). Рантайм **читает кэш**; нет сети/
ключей или превышен latency-бюджет ⇒ кэш / детерминированный фолбэк (как
`nlu_service`). Без `Date.now()`/`random` в логике.

> **Статус: placeholder Волны 3.** Файлы заполнены детерминированной заглушкой
> (`api/etl/ai_cache_seed.py`). **`b16`/`b17` (Волна 4) перезаписывают** их
> реальными значениями (VLM по кадру / Open-Meteo). До тех пор — корректный
> фолбэк: `weather="unknown"`, `day_night` из часа `ts`, `bonus=0`.

Файлы **коммитятся в git** (в `.gitignore` `data/ai/*.json` не игнорируются) —
демо и тесты работают офлайн без внешних API.

Сгенерировать/обновить placeholder:

```bash
python api/etl/ai_cache_seed.py     # 54 строки в обоих файлах, идемпотентно
```

---

## `scene_labels.json` — `incident_scene` (§8.1)

Источник реальных данных: `api/etl/scene_precompute.py` (VLM по кадру ch1/ch5, `b16`).
SQL-загрузчик: `api/sql/30_incident_scene.sql`. Одна запись = один алярм (54).

| поле              | тип     | домен / значение                              | placeholder |
|-------------------|---------|-----------------------------------------------|-------------|
| `id`              | string  | id алярма из `v_incidents`                    | из данных   |
| `weather`         | string  | `clear` \| `rain` \| `snow` \| `fog`          | `unknown`   |
| `day_night`       | string  | `day` \| `twilight` \| `night`                | из часа `ts`|
| `road_surface`    | string  | `dry` \| `wet` \| `snow` \| `ice` \| `unknown`| `unknown`   |
| `area`            | string  | `urban` \| `highway` \| `unknown`             | `unknown`   |
| `visibility`      | string  | `good` \| `moderate` \| `poor`                | `unknown`   |
| `scene_confidence`| number  | `0..1`                                        | `0.0`       |
| `source`          | string  | `vlm` \| `cache` (b16) / `placeholder` (w3-16)| `placeholder` |

## `weather_cache.json` — `incident_weather` (§8.1)

Источник реальных данных: Open-Meteo historical + sunrise-sunset (`b17`).
SQL-загрузчик: `api/sql/31_incident_weather.sql`. Одна запись = один алярм (54).

| поле                  | тип            | домен / значение                        | placeholder |
|-----------------------|----------------|-----------------------------------------|-------------|
| `id`                  | string         | id алярма из `v_incidents`              | из данных   |
| `ts`                  | string         | метка времени алярма                    | из данных   |
| `lat`                 | number \| null | широта                                  | из данных   |
| `lon`                 | number \| null | долгота                                 | из данных   |
| `api_weather`         | string         | код погоды Open-Meteo                    | `unknown`   |
| `api_precip_mm`       | number \| null | осадки, мм                              | `null`      |
| `api_visibility_m`    | number \| null | видимость, м                            | `null`      |
| `is_day`              | bool           | день ли (по solar elevation)            | `day_night == "day"` |
| `solar_elevation_deg` | number \| null | высота солнца, град.                    | `null`      |
| `discrepancy`         | bool           | расходится ли API с фактом              | `false`     |
| `discrepancy_kind`    | string         | `weather` \| `daynight` \| `none`       | `none`      |

---

## Формат файла

Каждый кэш — JSON-объект с шапкой и массивом записей (DuckDB читает через
`read_json` + `unnest(records)`):

```jsonc
{
  "_comment": "placeholder Волны 3 (w3-16); b16/b17 перезаписывают …",
  "schema_ref": "00-CONTRACT.md §8.1 incident_scene",
  "source": "placeholder",
  "count": 54,
  "records": [ /* … по строке на алярм … */ ]
}
```

`records` отсортированы по `id`, ключи — в фиксированном порядке ⇒ повторная
генерация даёт байт-идентичный файл (идемпотентность, диффы только по сути).
