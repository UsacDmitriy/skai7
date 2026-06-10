# tu-review · Unit-тесты очереди верификации (фича #23, модуль b30)

> Трек **Tests** (`feat/tests`, окно 3). Против `00-CONTRACT.md` §11.0–§11.4.
> **Модель:** 🔵 Sonnet — детерминированная статусная модель; гейт = pytest.
> **Владеет:** `api/tests/unit/test_review.py`. Инфра — из `t1`. Гонится после `b30`.

## Цель

Закрепить статусную модель §11.0: последняя запись побеждает, единый словарь статусов,
негативы журнала, согласованность counts.

## Состав — `api/tests/unit/test_review.py`

> Журнал — во временной директории: переопредели `settings.output_dir` (tmp_path фикстура) +
> `review_service.reset_state()` между тестами (прецедент `actions_service.reset_overrides`).

- Пустой журнал → все инциденты `pending`; `len(items)` == числу строк `v_incidents`; сумма `counts` == всего.
- `decide(id, 'validated', 'ок')` → строка в CSV, статус `validated`, `note='ок'`, `decided_at` непустой.
- Перезапись: `decide(id,'validated')` затем `decide(id,'dismissed')` → статус `dismissed`,
  в `counts` инцидент один раз (журнал append-only, побеждает последняя).
- Фильтр `status='pending'` отдаёт только pending, а `counts` — по всем (не по фильтру).
- Неизвестный `incident_id` → 404 (API-уровень: `TestClient`); `decision='maybe'` → 422.
- Битая строка в журнале (вручную дописать `"x,y"`) → пропущена, сервис не падает.
- `evidence_rate` в ответе == значению из `consistency_service.report()` (не пересчитан заново).
- Эмиттер метрик замокан исключением → `decide` всё равно записывает решение (no-op деградация §11.1).
- `actions.csv` не появляется/не меняется от операций ревью (единый словарь §11.0).

## Check

- `pytest api/tests/unit/test_review.py -q` зелёный **без сети**; журнал — только в tmp.
- Перезапись/негативы/изоляция от `actions.csv` — покрыты.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# параллельно с f26 в соседнем worktree — стейджи только свои файлы (НЕ git add -A)
git add api/tests/unit/test_review.py
git commit -m "tu-review: юниты очереди верификации — статусы/перезапись/негативы (§11)"
```
