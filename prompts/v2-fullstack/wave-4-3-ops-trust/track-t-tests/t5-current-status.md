# t5 · CURRENT_STATUS — единый источник истины (по research-отчёту)

> Трек **Tests/Chores** (`feat/tests`, окно 3). Против `00-CONTRACT.md` §8.9. **Владеет:** `CURRENT_STATUS.md`,
> `scripts/gen_status.py`.
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — механическая генерация документа из тестов/контракта; гейт структурный.
> **Волна 4.3** (AI Ops & Trust), окно 3. Закрывает дрейф README↔RUNBOOK↔contract.
> **Скелет `scripts/gen_status.py` создаётся в prep `w3-19`** (этот промпт расширяет его до полной генерации).

## Цель

Один источник истины о **фактическом** статусе реализации (а не маркетинг README): «реализовано vs план»,
авто/полу-авто из результатов тестов + перечня эндпоинтов/таблиц контракта.

## Состав

- `scripts/gen_status.py` — собирает: список эндпоинтов (из роутеров/OpenAPI), таблиц (из `api/sql`),
  прохождение `pytest`/`vitest` (последний прогон), и пишет `CURRENT_STATUS.md` секциями
  (P0/P1/P2/Wave-4 · ✅ done / 🟡 partial / ⬜ planned). Детерминированный вывод (сорт по id).
- `CURRENT_STATUS.md` — генерируемый; в шапке «не редактировать вручную, источник — `gen_status.py`».

## Check

- `python scripts/gen_status.py` создаёт `CURRENT_STATUS.md` детерминированно (повтор → идентично).
- Перечень эндпоинтов/таблиц совпадает с фактическими роутерами/`api/sql` (не с README).
- Статусы согласованы с последним прогоном тестов.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# параллельно в одном worktree — стейджи только свои файлы (НЕ git add -A)
git add CURRENT_STATUS.md scripts/gen_status.py
git commit -m "t5: <что сделано>"
```
