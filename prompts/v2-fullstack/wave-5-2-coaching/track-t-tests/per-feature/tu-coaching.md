# tu-coaching · Unit-тесты цикла обучения (фича #24, модули b31/b32)

> Трек **Tests** (`feat/tests`, окно 3). Против `00-CONTRACT.md` §12.0–§12.4.
> **Модель:** 🔵 Sonnet — детерминированная генерация/агрегация; гейт = pytest.
> **Владеет:** `api/tests/unit/test_coaching.py`. Инфра — из `t1`. Гонится после `b32`.

## Цель

Закрепить §12: детерминизм генератора, правила курсов/порогов, реальность `repeat_within_30d`,
KPI-инварианты, негативы.

## Состав — `api/tests/unit/test_coaching.py`

**Генератор (b31):**
- Запуск дважды (в tmp-путь) → байт-идентичные файлы (§12.0).
- Число строк == числу алармов источника; `assignment_id` уникальны и отсортированы.
- Табличный тест словаря курсов: `DMS_DROWSY→C-FATIGUE`, `HARSH_BRAKING→C-SMOOTH`,
  `OVERSPEED→C-SPEED`, `CAMERA_TAMPER→C-RULES`, неизвестный код → `C-BASE`.
- Пороги: `passed` ⟺ `test_score>=18`; `completed_at` пуст ⟺ `test_score<10`.
- `repeat_within_30d` на синтетических алармах: два аларма той же plate/Type с разницей 10 дней →
  true; 40 дней → false; разные Type → false.

**Сервис (b32):**
- `card(plate)`: `status` — табличный тест (`score=19,completed → passed`; `score=12,completed →
  failed`; `score=5,нет completed → incomplete`).
- KPI-инварианты: все ∈ [0,1]; `pass_rate` при 0 завершивших == 0.0 (не деление на ноль);
  KPI согласованы со списком назначений (пересчёт в тесте).
- `summary()` отсортирован по `repeat_violation_rate` desc; `synthetic == True` в карточке.
- 404 на неизвестный plate (TestClient); водитель без назначений → 200, нулевые KPI.
- Детерминизм: два вызова → равные объекты.

## Check

- `pytest api/tests/unit/test_coaching.py -q` зелёный **без сети**.
- Генератор/правила/KPI/негативы §12 закреплены; регресс остальных юнитов не тронут.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# параллельно с f27 в соседнем worktree — стейджи только свои файлы (НЕ git add -A)
git add api/tests/unit/test_coaching.py
git commit -m "tu-coaching: юниты цикла обучения — генератор/статусы/KPI (§12)"
```
