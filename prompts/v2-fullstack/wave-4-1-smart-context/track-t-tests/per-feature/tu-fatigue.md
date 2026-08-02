# tu-fatigue · Unit-тесты fatigue-chain (идея #15, модуль b20)

> Трек **Tests** (`feat/tests`, окно 3). Против `00-CONTRACT.md` §8.3/§8.4.
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — детерминированная логика против контракта; гейт = pytest.
> **Владеет:** `api/tests/unit/test_fatigue.py`. Инфра — из `t1`. Гонится после `b20`.

## Цель

Покрыть оконную логику цепочек усталости без сети и без `datetime.now()`.

## Состав — `api/tests/unit/test_fatigue.py`

- `yawning→drowsy→harsh` в окне `window_min` → одна цепочка с `events` по `ts`; `severity` > одиночного.
- Те же события вне окна → НЕ цепочка; одиночное событие → НЕ цепочка.
- `severity` монотонно растёт с длиной/наличием `DMS_DROWSY`.
- `?plate=` фильтрует; нет цепочек → `[]`. Детерминизм между прогонами.

## Check

- `pytest api/tests/unit/test_fatigue.py -q` зелёный без сети.
- Внутри/вне окна, монотонность severity, фильтр и пустой кейс проверены.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**.
⚠️ **5× tu-* идут параллельно в одном tests-worktree — НЕ `git add -A`**: стейджи только свой тест-файл
(иначе коммит подхватит недописанные тесты соседей).

```bash
git add api/tests/unit/test_fatigue.py
git commit -m "tu-fatigue: <что сделано>"
```
