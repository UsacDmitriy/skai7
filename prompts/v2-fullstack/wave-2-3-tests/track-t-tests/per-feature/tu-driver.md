# tu-driver · Unit-тесты справочника водителей (фича #2, модуль b7)

> Трек **Tests** (`feat/tests`, окно 3). Против `00-CONTRACT.md` §7.1.
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — детерминированная логика против контракта; гейт = pytest.
> **Владеет:** `api/tests/unit/test_seed_drivers.py`. Инфраструктура — из `t1`.
> Per-feature слой: гонится, как `b7` лёг на `integration`. Баг → дефект треку B, не правится здесь.

## Цель

Покрыть детерминированный сидинг `driver_reference`/`driver_trips` (`b7`): идемпотентность и
структурные инварианты — без сети и без поднятого API.

## Состав — `api/tests/unit/test_seed_drivers.py`

- `seed_drivers` идемпотентен: два запуска → идентичный CSV (один вход → один выход).
- `driver_reference`: ровно 1 строка на `vehicle_plate`; `safety_score` ∈ [0,100];
  пул ФИО ≥ 20, регионов ≥ 5.
- `driver_trips`: 1–2 водителя на ТС, ровно один `role="main"`.

## Check

- `pytest api/tests/unit/test_seed_drivers.py -q` зелёный.
- Тесты не требуют сети/uvicorn; проходят после `make db`.
- Структурные инварианты (1 строка/plate, ровно один main) проверены явно; углубление — в `w3-3`.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**; незакоммиченная
работа в worktree на барьер не попадёт:

```bash
git add -A && git commit -m "tu-driver: <что сделано>"
```
