# b17 · Weather cross-check + risk-надбавка (идея #11)

> Трек **Backend/Data**. Против `00-CONTRACT.md` §8.1/§8.2/§8.4. **Владеет:** `api/etl/weather_precompute.py`,
> `api/sql/31_incident_weather.sql`, `data/ai/weather_cache.json`; **аддитивная** правка `api/core/enrichment.py`.
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — детерминированный фетч+кэш+правило; гейт = тесты.
> **Волна 4.1**, окно 1 (backend). Зависит от: b3 (`v_incidents` `ts`/`lat`/`lon`), b16 (`incident_scene`).

## Цель

Оффлайн-кросс-проверка «камера ↔ внешние данные»: по `ts`+`lat/lon` каждого алярма получить погоду
(Open-Meteo historical) и день/ночь (sunrise-sunset / solar elevation), сравнить со сценой b16 и
выставить **флаг расхождения**. Питает `risk_score`.

## Состав

1. `api/etl/weather_precompute.py` — батч по 54 алярмам: Open-Meteo historical (`precipitation`,
   `visibility`, `weather_code` → `api_weather`), solar elevation (sunrise-sunset.org или расчёт) → `is_day`.
   Кэш `data/ai/weather_cache.json` (детерминированный, сорт по `id`). Нет сети → читать существующий кэш.
2. `api/sql/31_incident_weather.sql` — таблица `incident_weather` из кэша; вычислить `discrepancy`/
   `discrepancy_kind`: `weather` если `scene.weather`≠`api_weather` (rain↔clear), `daynight` если
   `scene.day_night`(night)≠`is_day`(true); иначе `none`.
3. `api/core/enrichment.py` (**аддитивно**): `weather_risk_bonus(scene, weather) -> float` —
   детерминированная надбавка к `risk_score` (`wet/ice`+0.1, `poor visibility`+0.1, `night`+уже учтён).
   Без кэша — bonus=0 (обратная совместимость; существующие тесты b2/t1 не падают).

## Check

- `python -m api.etl.weather_precompute` создаёт `data/ai/weather_cache.json` (54) детерминированно; без сети читает кэш.
- `make db` → `incident_weather`=54; `discrepancy ∈ {true,false}`, `discrepancy_kind` из enum.
- Кейс «сцена: дождь/ночь, API: ясно/день» → `discrepancy=true`, корректный `discrepancy_kind`.
- `risk_score` с надбавкой ≥ без надбавки; без кэша поведение прежнее (регресс t1 зелёный).

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**.
⚠️ Стейджи только свои файлы (**не `git add -A`** — в backend-worktree параллельно идут другие промпты
Волны 4.1); правка `enrichment.py` — аддитивная, включена сознательно. Доп. свои файлы — добавь явно.

```bash
git add api/etl/weather_precompute.py api/sql/31_incident_weather.sql data/ai/weather_cache.json api/core/enrichment.py
git commit -m "b17: <что сделано>"
```
