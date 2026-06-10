# tu-consistency · Unit-тесты Data Trust (фичи #21/#22, модули b28/b29)

> Трек **Tests** (`feat/tests`, окно 3). Против `00-CONTRACT.md` §10.2/§10.3/§10.5.
> **Модель:** 🔵 Sonnet — детерминированная логика против контракта; гейт = pytest.
> **Владеет:** `api/tests/unit/test_consistency.py`, `api/tests/unit/test_speed_check.py`.
> Инфра — из `t1`. Гонится после `b29` (нужны оба view/сервиса).

## Цель

Закрепить контракт §10: пороги статусов, диапазоны ratio, детерминизм, негативы `no_data`,
инварианты сводных метрик.

## Состав — `api/tests/unit/test_consistency.py`

- `/api/consistency` → 200; `len(checks) == 7`; все `check_id` из §10.3 присутствуют (множество, не порядок).
- Каждая проверка: `0 <= ratio <= 1`; `affected_count <= total`; `len(sample_ids) <= 5`.
- Классификация статусов — **табличный** тест границ (через сервисную функцию):
  `(affected,total)` → `(0,10)='ok'`, `(1,10)='warn'`, `(2,10)='warn'` (0.2 НЕ fail), `(3,10)='fail'`, `(0,0)='ok'`.
- Инвариант: `evidence_rate == 1 - ratio(incident_no_video)` и `speed_agreement_rate == 1 - ratio(speed_disagreement)` (с точностью 1e-9).
- `coordinate_sanity.affected_count > 0` — пустые координаты в alarms реально существуют (фиксируем датасет-факт).
- Детерминизм: два вызова сервиса → равные объекты.

## Состав — `api/tests/unit/test_speed_check.py`

- Известный аларм → 200, `truth_source == 'gps_track'`; неизвестный id → 404.
- Выбор ближайшей точки: на синтетических строках точка в 9 с от `event_begin_utc` берётся,
  в 11 с — игнорируется (`no_data`, окно ±10 с §10.2).
- Пороги agreement — табличный тест: `delta` 0→`ok`, 5→`ok`, 5.1→`minor`, 15→`minor`, 15.1→`major`.
- `no_data`: `event_speed_kmh is None` или нет точки в окне → `agreement='no_data'`, `delta_kmh is None`, ответ 200.
- Детерминизм: два вызова → идентичный `SpeedCheck`.

## Check

- `pytest api/tests/unit/test_consistency.py api/tests/unit/test_speed_check.py -q` зелёный **без сети**.
- Пороги/окно/инварианты §10.2 закреплены; регресс остальных юнитов не тронут.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# параллельно с f25 в соседнем worktree — стейджи только свои файлы (НЕ git add -A)
git add api/tests/unit/test_consistency.py api/tests/unit/test_speed_check.py
git commit -m "tu-consistency: юниты Data Trust — пороги/окно/детерминизм/негативы (§10)"
```
