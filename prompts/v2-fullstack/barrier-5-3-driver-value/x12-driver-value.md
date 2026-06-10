# x12 · Driver Value (Волна 5.3) → main · ФИНАЛ Волны 5

> **Барьер Волны 5.3, финал Волны 5.** **Владеет:** только запуск/проверки (e2e скоринга + полный
> регресс + продвижение `main`). **Модель:** 🔴 Opus — интеграция/приёмка/продвижение `main`.
> Запускать ПОСЛЕ Волны 5.3 (b33, b34, f28, tu-score) и **зелёного x11**.

## Gate: x11 зелёный, main продвинут

`git merge-base --is-ancestor $(git rev-parse main) integration` — и main на Волне 5.2;
иначе СТОП (сначала x11).

## Перед стартом — склейка Волны 5.3

```bash
cd /Users/dimausac/projects/skai_7
git checkout integration

# GUARD: merge берёт только коммиты — стоп при незакоммиченном worktree.
for w in backend web tests; do
  d=".worktrees/$w"; [ -d "$d" ] || continue
  test -z "$(git -C "$d" status --porcelain)" || { echo "❌ $w: незакоммичено — закоммить и повтори барьер"; exit 1; }
done

git merge feat/backend feat/web feat/tests   # 5.3: b33, b34, f28, tu-score
```

## Цель

Подтвердить скоринговый слой (#25 позитив/green-zone, #26 единый рейтинг, §13) сквозь стек на
полном регрессе. Затем продвинуть `main` — финал Волны 5.

## Шаги (§13)

1. **API (b33):** `GET /api/positive-score/{plate}` → 200, схема §13.1; ТС без алармов →
   `positive_score=100`, не 5xx; 404 на неизвестный plate.
2. **API (b34):** `GET /api/driver-score` → строк == ТС в `driver_reference`, сортировка desc,
   tie-break по plate; инвариант бленда (см. негативы).
3. **UI (f28):** `/leaderboard` в NAV, таблица с дисклеймером периода и green-zone бейджами;
   блок «Позитивное вождение» в отчёте ПОСЛЕ секции обучения; клик лидерборда → отчёт водителя.
4. **Тесты (tu-score):** `pytest api/tests/unit/test_positive_score.py api/tests/unit/test_driver_score.py -q` зелёный.

## Универсальный гейт + негативы Driver Value (обязательно)

Прогнать **полный** [`../barrier-CHECKLIST.md`](../barrier-CHECKLIST.md): `bash scripts/check.sh` целиком
(весь регресс P0/P1/P2/Волн 3–5.2), `make openapi` валиден, в финале — git-пост-условие ff-merge.

Негативы/инварианты (доп.):
```bash
curl -s localhost:8000/api/driver-score | jq -e '[.[].unified_score]|. == (sort|reverse)'
curl -s localhost:8000/api/driver-score | jq -e \
  '.[]|((.risk_component+.positive_component)|round|if .>100 then 100 elif .<0 then 0 else . end) == .unified_score'
curl -s localhost:8000/api/driver-score | jq -e '.[]|select(.avg_risk_score==0)|.unified_score>=40'  # ТС без алармов в рейтинге, не NaN
test "$(curl -s -o /dev/null -w '%{http_code}' localhost:8000/api/positive-score/__nope__)" = 404
test "$(curl -s -o /dev/null -w '%{http_code}' localhost:8000/api/driver-score/__nope__)" = 404
curl -s localhost:8000/api/positive-score/<plate> | jq -e '[.compliant_events_ratio,.harsh_free_ratio]|all(.>=0 and .<=1)'
# детерминизм
diff <(curl -s localhost:8000/api/driver-score) <(curl -s localhost:8000/api/driver-score)
```
- Паритет фикстур: лидерборд и блок позитива на живом API **и** `VITE_USE_FIXTURES=true`;
  консоль чистая; green-zone/место — не только цветом (a11y).
- Дисклеймер «за период N дн.» виден на лидерборде и в блоке позитива (§13.0) — без него красный.
- Формула §2 не задета: `tu-enrichment` и регресс рисков зелёные (b34 импортирует, не копирует).

## Критерии приёмки

- #25/#26 проходят сквозь стек; инвариант бленда и сортировка зелёные; негативы 404/[0,1] зелёные.
- **Полный** `scripts/check.sh` зелёный; типы §13 совпадают; typecheck зелёный.
- Честность: дисклеймеры периода на месте; ТС без алармов корректен (не NaN).

## Финализация — продвинуть main (финал Волны 5)

**Только если все критерии зелёные:**

```bash
git -C /Users/dimausac/projects/skai_7 checkout main
git merge --ff-only integration
# если ff-only падает → git merge --no-ff integration -m "merge integration → main (Волна 5 финал · driver value)"
git checkout integration
```

Красный барьер → **`main` НЕ трогаем**, дефект треку, чиним на `integration`.

## Коммит (обязательно)

```bash
git add -A && git commit -m "x12: Driver Value (Волна 5.3) → main · финал Волны 5"
```
