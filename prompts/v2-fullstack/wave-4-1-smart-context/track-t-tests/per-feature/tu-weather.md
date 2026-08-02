# tu-weather · Unit-тесты weather-crosscheck (идея #11, модуль b17)

> Трек **Tests** (`feat/tests`, окно 3). Против `00-CONTRACT.md` §8.1/§8.2.
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — детерминированная логика против контракта; гейт = pytest.
> **Владеет:** `api/tests/unit/test_weather_crosscheck.py`. Инфра — из `t1`. Гонится после `b17`.

## Цель

Покрыть правило расхождения «сцена↔погода» и risk-надбавку без сети (на кэше `weather_cache.json`).

## Состав — `api/tests/unit/test_weather_crosscheck.py`

- `discrepancy`/`discrepancy_kind`: сцена `rain`/`night` vs API `clear`/`day` → `true` + верный `kind`; совпадение → `none`.
- `weather_risk_bonus`: `wet`/`ice`/`poor visibility` дают надбавку > 0; чистое сухое днём → 0.
- Обратная совместимость: без кэша `risk_score` = прежнее значение (регресс по `tu-enrichment`/t1 не падает).
- `incident_weather` = 54 строки; `is_day ∈ {true,false}`.

## Check

- `pytest api/tests/unit/test_weather_crosscheck.py -q` зелёный без сети.
- Кейсы расхождения и совпадения; надбавка монотонна; обратная совместимость подтверждена.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**.
⚠️ **5× tu-* идут параллельно в одном tests-worktree — НЕ `git add -A`**: стейджи только свой тест-файл
(иначе коммит подхватит недописанные тесты соседей).

```bash
git add api/tests/unit/test_weather_crosscheck.py
git commit -m "tu-weather: <что сделано>"
```
