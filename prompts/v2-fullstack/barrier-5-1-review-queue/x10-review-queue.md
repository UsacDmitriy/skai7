# x10 · Review Queue (Волна 5.1) → main

> **Барьер Волны 5.1.** **Владеет:** только запуск/проверки (e2e очереди + полный регресс + продвижение
> `main`). **Модель:** 🔴 Opus — интеграция/приёмка/продвижение `main`.
> Запускать ПОСЛЕ Волны 5.1 (b30, f26, tu-review) и **зелёного x9**.

## Gate: x9 зелёный, main продвинут

`git merge-base --is-ancestor $(git rev-parse main) integration` — и main на финале Волны 4.4;
иначе СТОП (сначала x9).

## Перед стартом — склейка Волны 5.1

В окне `skai_7` на ветке `integration`.

```bash
cd /Users/dimausac/projects/skai_7
git checkout integration

# GUARD: merge берёт только коммиты — стоп при незакоммиченном worktree.
for w in backend web tests; do
  d=".worktrees/$w"; [ -d "$d" ] || continue
  test -z "$(git -C "$d" status --porcelain)" || { echo "❌ $w: незакоммичено — закоммить и повтори барьер"; exit 1; }
done

git merge feat/backend feat/web feat/tests   # 5.1: b30, f26, tu-review
```

## Цель

Подтвердить workflow верификации (#23, §11) сквозь стек: журнал → API → экран `/validation`,
на полном регрессе. Затем продвинуть `main`.

## Шаги (§11)

1. **API (b30):** `GET /api/review-queue` → 200, схема §11.2; сумма `counts` == числу инцидентов;
   `POST .../{id}` validated/dismissed работает; журнал `output/review_queue.csv` растёт append-only.
2. **UI (f26):** `/validation` — живой экран очереди (NAV без бейджа, `COMING_SOON`-ключа нет);
   решение меняет статус/счётчики; клик строки → карточка инцидента; `/response` не тронут.
3. **Статусный словарь (§11.0):** операции ревью НЕ пишут в `actions.csv`; легаси `validate` (§3.4)
   работает как раньше (регресс).
4. **Тесты (tu-review):** `pytest api/tests/unit/test_review.py -q` зелёный.

## Универсальный гейт + негативы Review Queue (обязательно)

Прогнать **полный** [`../barrier-CHECKLIST.md`](../barrier-CHECKLIST.md): `bash scripts/check.sh` целиком
(весь регресс P0/P1/P2/Волн 3–4.4), `make openapi` валиден, в финале — git-пост-условие ff-merge.

Негативы/инварианты (доп.):
```bash
curl -s localhost:8000/api/review-queue | jq -e '.counts.pending + .counts.validated + .counts.dismissed == (.items|length)'
curl -s localhost:8000/api/review-queue | jq -e '.evidence_rate>=0 and .evidence_rate<=1'
test "$(curl -s -o /dev/null -w '%{http_code}' -X POST localhost:8000/api/review-queue/__nope__ \
  -H 'content-type: application/json' -d '{"decision":"validated"}')" = 404
test "$(curl -s -o /dev/null -w '%{http_code}' -X POST localhost:8000/api/review-queue/<id> \
  -H 'content-type: application/json' -d '{"decision":"maybe"}')" = 422
# §11.0: перезапись — последняя запись побеждает
curl -s -X POST localhost:8000/api/review-queue/<id> -H 'content-type: application/json' -d '{"decision":"validated"}' >/dev/null
curl -s -X POST localhost:8000/api/review-queue/<id> -H 'content-type: application/json' -d '{"decision":"dismissed"}' >/dev/null
curl -s "localhost:8000/api/review-queue" | jq -e --arg id "<id>" '.items[]|select(.incident_id==$id)|.status=="dismissed"'
# §11.0: actions.csv не растёт от ревью (снять wc -l до/после POST'ов выше)
```
- Паритет фикстур: экран на живом API **и** `VITE_USE_FIXTURES=true`; loading/empty/error; a11y кнопок.
- Ревизия допущений f22: `/validation` закрыт владельцем (этот барьер); `/quick-report`/`/safety`/
  `/dashboards`/`/response` — владельцы не появились, редиректы/«Будущее» остаются.

## Критерии приёмки

- #23 проходит сквозь стек; перезапись статуса и негативы 404/422 зелёные; журнал append-only.
- **Полный** `scripts/check.sh` зелёный; `actions.csv` изолирован от ревью (§11.0).
- Типы §11.2 совпадают (Pydantic ↔ TS); фронт typecheck зелёный.

## Финализация — продвинуть main

**Только если все критерии зелёные** (паттерн x9):

```bash
git -C /Users/dimausac/projects/skai_7 checkout main
git merge --ff-only integration
# если ff-only падает → git merge --no-ff integration -m "merge integration → main (Волна 5.1 · review queue)"
git checkout integration
```

Красный барьер → **`main` НЕ трогаем**, дефект треку, чиним на `integration`.

## Коммит (обязательно)

```bash
git add -A && git commit -m "x10: Review Queue (Волна 5.1) → main"
```
