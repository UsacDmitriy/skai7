# x11 · Coaching Loop (Волна 5.2) → main

> **Барьер Волны 5.2.** **Владеет:** только запуск/проверки (e2e цикла обучения + полный регресс +
> продвижение `main`). **Модель:** 🔴 Opus — интеграция/приёмка/продвижение `main`.
> Запускать ПОСЛЕ Волны 5.2 (b31, b32, f27, tu-coaching) и **зелёного x10**.

## Gate: x10 зелёный, main продвинут

`git merge-base --is-ancestor $(git rev-parse main) integration` — и main на Волне 5.1;
иначе СТОП (сначала x10).

## Перед стартом — склейка Волны 5.2

```bash
cd /Users/dimausac/projects/skai_7
git checkout integration

# GUARD: merge берёт только коммиты — стоп при незакоммиченном worktree.
for w in backend web tests; do
  d=".worktrees/$w"; [ -d "$d" ] || continue
  test -z "$(git -C "$d" status --porcelain)" || { echo "❌ $w: незакоммичено — закоммить и повтори барьер"; exit 1; }
done

git merge feat/backend feat/web feat/tests   # 5.2: b31, b32, f27, tu-coaching
```

## Цель

Подтвердить цикл обучения (#24, §12) сквозь стек: детерминированная синтетика → API → секция
отчёта с честным бейджем. Затем продвинуть `main`.

## Шаги (§12)

1. **Датасет (b31):** `make seed` → `data/seed/training_assignments.csv` байт-идентичен закоммиченному
   (`git diff --exit-code data/seed/`); `make db` → таблица `training_assignments` есть, строк == алармам.
2. **API (b32):** `GET /api/coaching` → 200, сортировка по `repeat_violation_rate`; `GET /api/coaching/{plate}`
   → 200, `synthetic==true`; KPI ∈ [0,1]; 404 на неизвестный plate.
3. **UI (f27):** в отчёте водителя — секция обучения с **бейджем «синтетические данные (демо)»**,
   KPI-чипами и таблицей; переход на карточку инцидента работает; пустой кейс — «обучение не назначалось».
4. **Тесты (tu-coaching):** `pytest api/tests/unit/test_coaching.py -q` зелёный.

## Универсальный гейт + негативы Coaching (обязательно)

Прогнать **полный** [`../barrier-CHECKLIST.md`](../barrier-CHECKLIST.md): `bash scripts/check.sh` целиком
(весь регресс P0/P1/P2/Волн 3–5.1), `make openapi` валиден, в финале — git-пост-условие ff-merge.

Негативы/инварианты (доп.):
```bash
curl -s localhost:8000/api/coaching/<plate> | jq -e '.synthetic==true'
curl -s localhost:8000/api/coaching/<plate> | jq -e '[.kpi.completion_rate,.kpi.pass_rate,.kpi.repeat_violation_rate]|all(.>=0 and .<=1)'
test "$(curl -s -o /dev/null -w '%{http_code}' localhost:8000/api/coaching/__nope__)" = 404
# §12.0: детерминизм генератора — повторная генерация не меняет закоммиченный CSV
python -m api.etl.seed_coaching && git diff --exit-code data/seed/training_assignments.csv
# детерминизм API
diff <(curl -s localhost:8000/api/coaching) <(curl -s localhost:8000/api/coaching)
```
- Паритет фикстур: секция на живом API **и** `VITE_USE_FIXTURES=true` (три статуса + повтор-флажок);
  консоль чистая; статусы читаются не только цветом (a11y).
- Бейдж синтетики ОБЯЗАТЕЛЕН на экране (§12.0) — без него барьер красный (честность данных).

## Критерии приёмки

- #24 проходит сквозь стек; генератор байт-стабилен; KPI-инварианты и негативы зелёные.
- **Полный** `scripts/check.sh` зелёный; типы §12.3 совпадают; typecheck зелёный.
- UI честен: бейдж «синтетические данные (демо)» виден.

## Финализация — продвинуть main

**Только если все критерии зелёные** (паттерн x9/x10):

```bash
git -C /Users/dimausac/projects/skai_7 checkout main
git merge --ff-only integration
# если ff-only падает → git merge --no-ff integration -m "merge integration → main (Волна 5.2 · coaching)"
git checkout integration
```

Красный барьер → **`main` НЕ трогаем**, дефект треку, чиним на `integration`.

## Коммит (обязательно)

```bash
git add -A && git commit -m "x11: Coaching Loop (Волна 5.2) → main"
```
