# b32 · Coaching-сервис — KPI цикла обучения (фича #24, владелец §12.2)

> Трек **Backend/Data**. Против `00-CONTRACT.md` §12.2/§12.3/§12.4. **Владеет:**
> `api/services/coaching_service.py`, `api/domain/coaching.py`, роутер `api/routers/coaching.py`
> (автодискавери `api/main.py:_discover_routers` — НЕ редактируй общий `api/routers/__init__.py`).
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — детерминированная агрегация против контракта; гейт = Check + tu-coaching.
> **Волна 5.2**, окно 1, **после b31** (нужна таблица `training_assignments`).

## Цель

`GET /api/coaching` (сводка по водителям) и `GET /api/coaching/{plate}` (карточка с назначениями
и KPI) — цикл Оздоева: кто прошёл курс, кто провалил тест, у кого повторные нарушения за 30 дней.

## Состав

- `coaching_service`:
  - `summary() -> list[CoachingSummary]`: агрегат `training_assignments` по `vehicle_plate`
    (+ `driver_id`/`driver_name` из `driver_reference`), сортировка по `repeat_violation_rate` desc;
  - `card(plate) -> CoachingCard`: назначения ТС + KPI; `plate` не из `driver_reference` → 404;
    водитель без назначений → пустой список + нулевые KPI (200, §12.4);
  - `status` назначения вычисляется в сервисе (§12.3): `passed` / `failed` (completed_at есть,
    passed=false) / `incomplete` (completed_at пуст);
  - KPI (§12.3): `completion_rate` = с completed_at/всего; `pass_rate` = passed/завершивших
    (0 завершивших → 0.0); `repeat_violation_rate` = с repeat_within_30d/всего; все ∈ [0,1];
  - поле `synthetic: true` — литерал в `CoachingCard` (честность §12.0); детерминизм (без сети/now()).
- `api/domain/coaching.py` — Pydantic-схемы **дословно §12.3**.
- Роутер `GET /api/coaching`, `GET /api/coaching/{plate}` — модульный `router = APIRouter(...)`.

Пример `CoachingCard` (формат — ровно такой):

```json
{
  "vehicle_plate": "T780РН198", "driver_id": "DRV-4459", "driver_name": "Михайлов Антон Борисович",
  "assignments": [
    { "assignment_id": "TA-12345", "incident_id": "12345", "course_id": "C-FATIGUE",
      "course_title_ru": "Контроль усталости", "assigned_at": "2026-05-14T08:12:00Z",
      "due_at": "2026-05-17T08:12:00Z", "test_score": 19, "status": "passed",
      "completed_at": "2026-05-14T15:12:00Z", "repeat_within_30d": true }
  ],
  "kpi": { "completion_rate": 1.0, "pass_rate": 1.0, "repeat_violation_rate": 1.0 },
  "synthetic": true
}
```

## Check

- `curl -s localhost:8000/api/coaching | jq -e 'length>0 and .[0].kpi.repeat_violation_rate>=.[1].kpi.repeat_violation_rate'` — сводка отсортирована.
- `curl -s localhost:8000/api/coaching/<plate из driver_reference> | jq -e '.synthetic==true and (.assignments|length>=0)'` → 200.
- 404 на `plate=__nope__`; водитель без назначений (если есть) → 200, пустой список, KPI нули.
- Все ratio ∈ [0,1]; `status` у score<10 → `incomplete`, у score 18..20 с completed → `passed`.
- `curl -s localhost:8000/openapi.json | jq -e '.paths."/api/coaching" and .paths."/api/coaching/{plate}"'` — автодискавери.
- Детерминизм: два вызова → идентичные ответы. `pytest api/tests/unit -q` зелёный.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# стейджи только свои файлы (НЕ git add -A)
git add api/services/coaching_service.py api/routers/coaching.py api/domain/coaching.py
git commit -m "b32: coaching-сервис — KPI цикла обучения + /api/coaching (§12)"
```
