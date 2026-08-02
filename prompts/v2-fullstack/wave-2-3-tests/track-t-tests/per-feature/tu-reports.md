# tu-reports · Unit-тесты правил отчётов (фича #2, модуль b10)

> Трек **Tests** (`feat/tests`, окно 3). Против `00-CONTRACT.md` §7.5.
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — детерминированная логика против контракта; гейт = pytest.
> **Владеет:** `api/tests/unit/test_reports_rules.py`. Инфраструктура — из `t1`.
> Per-feature слой: гонится, как `b10` лёг на `integration`. Баг → дефект треку B.

## Цель

Покрыть детерминированные бизнес-правила отчётов (`b10`): классификация грубых нарушений,
дисциплинарное взыскание и согласованность KPI — без сети и без поднятого API.

## Состав — `api/tests/unit/test_reports_rules.py`

- `is_gross`: true для `severity=critical` и для `alarm_code ∈ {OVERSPEED, DMS_SMOKING}`, иначе false.
- `disciplinary_warning`: true при `gross >= 3` ИЛИ `safety_score < 60`, иначе false; границы (`gross=3`, `score=60`).
- `ReportKPI` суммы согласованы: `total >= video_da`, `total >= telematics`.
- Пустой период (0 нарушений) → валидный отчёт с нулевыми KPI, не падать.

## Check

- `pytest api/tests/unit/test_reports_rules.py -q` зелёный.
- Граничные значения (`gross=3`, `safety_score=60`, пустой период) проверены явно.
- Тесты не требуют сети/uvicorn; углубление — в `w3-3`.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**; незакоммиченная
работа в worktree на барьер не попадёт:

```bash
git add -A && git commit -m "tu-reports: <что сделано>"
```
