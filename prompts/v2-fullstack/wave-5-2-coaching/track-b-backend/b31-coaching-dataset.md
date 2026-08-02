# b31 · Генератор синтетического датасета обучения (фича #24, §12.1)

> Трек **Backend/Data**. Против `00-CONTRACT.md` §12.0/§12.1. **Владеет:** `api/etl/seed_coaching.py`,
> `data/seed/training_assignments.csv` (коммитится в git, как `driver_reference.csv`), строка в
> `Makefile` цели `seed` (аддитивно). **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — детерминированная генерация по фиксированным
> правилам; гейт = Check + tu-coaching. **Волна 5.2**, окно 1, **первый** (затем b32).
> Зависит от: таблица алармов (b1), `data/seed/driver_reference.csv` (b7).

## Цель

Сгенерировать `data/seed/training_assignments.csv` — детерминированный демо-датасет назначений
обучения по реальным алармам (§12.1). Загрузку делает существующий `_load_seed_csvs` (glob
`data/seed/*.csv` → таблица `training_assignments`) — **ETL-загрузчик не редактируется**.

## Состав

- `api/etl/seed_coaching.py` (паттерн — `api/etl/seed_drivers.py`):
  - читает алармы из `datasets/ready/video_events/selected_video_alarms.csv` и
    `data/seed/driver_reference.csv` (driver_id по `vehicle_plate` ↔ `UnitStateNumber`);
  - на КАЖДЫЙ аларм — одно назначение, правила **дословно §12.1**:
    словарь курсов по `Type` (C-FATIGUE/C-FOCUS/C-SMOOTH/C-SPEED/C-RULES/C-BASE),
    `assigned_at = Begin`, `due_at = +72h`, `test_score = crc32(str(AlarmId)) % 21`,
    `passed = score >= 18`, `completed_at = assigned_at + (crc32 % 48 + 1)h` если `score >= 10` иначе пусто;
  - `repeat_within_30d` — **реальный** расчёт: существует ли другой аларм той же `UnitStateNumber`
    с тем же `Type` в окне ±30 дней от `Begin`;
  - `assignment_id = "TA-" + AlarmId`; сортировка строк по `assignment_id` (стабильный порядок);
  - **никаких** `random`/`datetime.now()` — повторный запуск → байт-идентичный CSV (§12.0).
- `Makefile`: в цель `seed` добавить строку `$(PY) -m api.etl.seed_coaching` (после `seed_drivers`).
- Сгенерировать и **закоммитить** `data/seed/training_assignments.csv`.

Пример строки CSV (формат — ровно такой):

```csv
assignment_id,incident_id,vehicle_plate,driver_id,course_id,course_title_ru,assigned_at,due_at,test_score,passed,completed_at,repeat_within_30d
TA-12345,12345,T780РН198,DRV-4459,C-FATIGUE,Контроль усталости,2026-05-14T08:12:00Z,2026-05-17T08:12:00Z,19,true,2026-05-14T15:12:00Z,true
```

## Check

- `python -m api.etl.seed_coaching` дважды → `diff` CSV пуст (байт-идентичность, §12.0).
- Число строк == числу алармов (не хардкод — сверить запросом).
- `make seed` отрабатывает (drivers + coaching); `make db` → таблица `training_assignments` в DuckDB
  (`_load_seed_csvs` подхватил glob — без правок загрузчика).
- Выборочно: аларм с `Type=DMS_DROWSY` → `C-FATIGUE`; `test_score ∈ [0,20]`; `passed` только при ≥18;
  у `score < 10` поле `completed_at` пустое.
- Существует ≥1 строка с `repeat_within_30d=true` и ≥1 с `false` (реальные повторы в данных есть).
- `pytest api/tests/unit -q` зелёный (регресс не сломан).

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# стейджи только свои файлы (НЕ git add -A)
git add api/etl/seed_coaching.py data/seed/training_assignments.csv Makefile
git commit -m "b31: детерминированный демо-датасет training_assignments (§12.1)"
```
