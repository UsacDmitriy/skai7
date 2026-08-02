# tu-forecast · Unit-тесты risk-forecast (идея #12, модуль b18)

> Трек **Tests** (`feat/tests`, окно 3). Против `00-CONTRACT.md` §8.3/§8.4.
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — детерминированная логика против контракта; гейт = pytest.
> **Владеет:** `api/tests/unit/test_forecast.py`. Инфра — из `t1`. Гонится после `b18`.

## Цель

Покрыть форму и детерминизм прогноза/аномалий/рекомендаций без сети.

## Состав — `api/tests/unit/test_forecast.py`

- `forecast(plate)` → `trend` длиной 7, каждый `ci_low ≤ predicted_events ≤ ci_high`.
- Детерминизм: фиксированный `random_state` → один вход → один выход.
- Аномальный всплеск в истории → `anomaly=true`, `anomaly_reason` непуст; ровный ряд → `anomaly=false`.
- Ночные события → `recommendations` содержит коучинг по утренней бдительности.
- Пустая история → валидный нулевой прогноз, не падает; неизвестный plate → обрабатывается (404 на уровне роутера в t2).

## Check

- `pytest api/tests/unit/test_forecast.py -q` зелёный без сети.
- Инварианты коридора, детерминизм, аномалия и рекомендации проверены.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**.
⚠️ **5× tu-* идут параллельно в одном tests-worktree — НЕ `git add -A`**: стейджи только свой тест-файл
(иначе коммит подхватит недописанные тесты соседей).

```bash
git add api/tests/unit/test_forecast.py
git commit -m "tu-forecast: <что сделано>"
```
