# tu-enrichment · Unit-тесты enrichment (фича #3, модули b2/b14)

> Трек **Tests** (`feat/tests`, окно 3). Против `00-CONTRACT.md` §2.
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — детерминированная логика против контракта; гейт = pytest.
> **Владеет:** `api/tests/unit/test_enrichment.py`. Инфраструктура (`conftest.py`,
> `requirements-dev.txt`) — из `t1`. Per-feature слой: гонится сразу, как `b2`(+`b14`) лёг на `integration`.
> НЕ редактирует продуктовый код — при найденном баге заводит дефект треку B.

## Цель

Покрыть детерминированную логику обогащения (`api/core/enrichment.py`) быстрыми unit-тестами
(без сети, без поднятого API). Каждая чистая функция — один вход → один выход.

## Состав — `api/tests/unit/test_enrichment.py`

- `risk_score` ∈ [0,100]; монотонность по severity (`critical>high>medium>low` при прочих равных);
  клампы на границах (после `b14`).
- `is_night` истинно для часов [22,06) UTC, ложно иначе.
- `ax` = производная скорости: на росте `ax>0`, на падении `ax<0`, не тождественный ноль.
- `speed_limit_for(code)` по таблице (DMS/городские → 60, иначе 90); дефолт для неизвестного кода.
- `confidence` детерминирован по `id` (один вход → один выход); на `requires_video=false`/нет видео ниже на 10.
- `cameras[]`: статусы online/warning/offline по `download_status`; длина 3 канонических.
- `evidence_summary`/`event_version` непусты для известных `alarm_code`; неизвестный код → дефолт без NULL.

## Check

- `pytest api/tests/unit/test_enrichment.py -q` зелёный; покрытие `api/core/enrichment.py` ≥ 90% (`--cov`).
- Тесты не требуют сети/uvicorn и проходят после `make db`.
- Базовый happy + негатив (неизвестный код, нет видео) закрыты; углубление покрытия — в `w3-3`.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**; незакоммиченная
работа в worktree на барьер не попадёт:

```bash
git add -A && git commit -m "tu-enrichment: <что сделано>"
```
