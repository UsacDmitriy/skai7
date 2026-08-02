# tu-riskbreakdown · Unit-тесты risk-breakdown (идея #19, модуль b27)

> Трек **Tests** (`feat/tests`, окно 3). Против `00-CONTRACT.md` §8.8 (+ §2).
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — детерминированная декомпозиция против формулы; гейт = pytest.
> **Владеет:** `api/tests/unit/test_risk_breakdown.py`. Инфра — из `t1`. Гонится после `b27`.

## Цель

Гарантировать, что explainability-декомпозиция **точно зеркалит** `risk_score`: сумма вкладов = итог.

## Состав — `api/tests/unit/test_risk_breakdown.py`

- `breakdown(id)`: **сумма** `{severity_w, speed_ratio, night, freq_w, weather_bonus}` == `risk_score` (§2),
  с тем же клампом; на нескольких инцидентах.
- Каждый вклад ≥ 0; `weather_bonus = 0` без кэша погоды (обратная совместимость).
- Детерминизм: один вход → один выход; неизвестный `id` обрабатывается (404 — на уровне роутера в t2).

## Check

- `pytest api/tests/unit/test_risk_breakdown.py -q` зелёный без сети.
- Инвариант «сумма вкладов = risk_score» выполняется для всех тестовых инцидентов; `weather_bonus=0` без кэша.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# параллельно в одном worktree — стейджи только свои файлы (НЕ git add -A)
git add api/tests/unit/test_risk_breakdown.py
git commit -m "tu-riskbreakdown: <что сделано>"
```
