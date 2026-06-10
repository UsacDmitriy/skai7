# x9 · Data Trust (Волна 4.4) → main

> **Барьер Волны 4.4.** **Владеет:** только запуск/проверки (e2e Data Trust + полный регресс + продвижение
> `main`). Авторство — треки B/F/T. **Модель:** 🔴 Opus — интеграция/приёмка/продвижение `main`.
> Запускать ПОСЛЕ Волны 4.4 (b28, b29, f25, tu-consistency) и **зелёного x8** (`main` уже на финале Волны 4).

## Gate: x8 зелёный, main продвинут

Не начинай, пока x8 (финал Волны 4) не зелёный и `main` не догнал `integration` на финале Волны 4:
`git merge-base --is-ancestor $(git rev-parse main) integration` — иначе СТОП (сначала финал Волны 4).

## Перед стартом — склейка Волны 4.4

В окне `skai_7` на ветке `integration`.

```bash
cd /Users/dimausac/projects/skai_7
git checkout integration

# GUARD: merge берёт только коммиты — стоп при незакоммиченном worktree.
for w in backend web tests; do
  d=".worktrees/$w"; [ -d "$d" ] || continue
  test -z "$(git -C "$d" status --porcelain)" || { echo "❌ $w: незакоммичено — закоммить и повтори барьер"; exit 1; }
done

git merge feat/backend feat/web feat/tests   # 4.4: b28, b29, f25, tu-consistency
```

## Цель

Подтвердить слой доверия к данным (#21 кросс-сверка скоростей, #22 валидатор консистентности, §10)
сквозь стек: DuckDB views → API → UI, на полном регрессе. Затем продвинуть `main`.

## Шаги (§10)

1. **БД:** `make db` → `v_consistency_checks` (7 строк) и `v_speed_check` (строк = алармам) собраны.
2. **API (b28/b29):** `GET /api/consistency` → 200, схема §10.2, 7 проверок; `GET /api/incidents/{id}/speed-check`
   → 200 (`truth_source='gps_track'`); неизвестный id → 404; оба в `openapi.json` (автодискавери).
3. **UI (f25):** карточка инцидента — бейдж сверки скоростей (рядом со scene-чипом f15); `/metrics` —
   панель консистентности (ниже data-quality f21); в UI «GPS-трек», не «CAN» (ASSUMPTION §10.2).
4. **Тесты (tu-consistency):** `pytest api/tests/unit/test_consistency.py api/tests/unit/test_speed_check.py -q` зелёный.

## Универсальный гейт + негативы Data Trust (обязательно)

Прогнать **полный** [`../barrier-CHECKLIST.md`](../barrier-CHECKLIST.md): `bash scripts/check.sh` целиком
(весь регресс P0/P1/P2/Волна 3/4.1/4.2/4.3), `make openapi` валиден, и в финале — git-пост-условие ff-merge.

Негативы/инварианты Data Trust (доп.):
```bash
curl -s localhost:8000/api/consistency | jq -e '.checks|length==7'
curl -s localhost:8000/api/consistency | jq -e '[.checks[].ratio]|all(.>=0 and .<=1)'
curl -s localhost:8000/api/consistency | jq -e '.evidence_rate>=0 and .evidence_rate<=1 and .speed_agreement_rate>=0 and .speed_agreement_rate<=1'
test "$(curl -s -o /dev/null -w '%{http_code}' localhost:8000/api/incidents/__nope__/speed-check)" = 404
curl -s localhost:8000/api/incidents/<id>/speed-check | jq -e '.truth_source=="gps_track"'
# §10.5: детерминизм — повторный вызов байт-идентичен
diff <(curl -s localhost:8000/api/consistency) <(curl -s localhost:8000/api/consistency)
# §10.0: это НЕ AI-фича — ai-меты быть не должно
curl -s localhost:8000/api/consistency | jq -e 'has("state")|not'
```
- Паритет фикстур: бейдж/панель на живом API **и** `VITE_USE_FIXTURES=true` (включая кейсы `major`/`no_data`);
  консоль чистая; светофор читается не только цветом (a11y).
- Ревизия допущений: f22-редиректы (`/safety`,`/dashboards`,`/quick-report`) — владелец-экран не появился?
  Если появился в Волне 5 — завести дефект на снятие редиректа (критерий отката в f22).

## Критерии приёмки

- Фичи #21/#22 проходят сквозь стек; негативы 404/[0,1]/`no_data` зелёные; детерминизм подтверждён.
- **Полный** `scripts/check.sh` зелёный (регресс P0–P2 + Волны 3/4.1/4.2/4.3 не сломан).
- Типы §10.2 совпадают (Pydantic ↔ TS); фронт typecheck зелёный.
- `evidence_rate`/`speed_agreement_rate` согласованы с проверками (инварианты tu-consistency).

## Финализация — продвинуть main

**Только если все критерии зелёные** (тот же паттерн, что x8):

```bash
git -C /Users/dimausac/projects/skai_7 checkout main
git merge --ff-only integration       # main догоняет integration (fast-forward)
# если ff-only падает → git merge --no-ff integration -m "merge integration → main (Волна 4.4 · data trust)"
git checkout integration
```

Красный барьер → **`main` НЕ трогаем** (остаётся на финале Волны 4), дефект треку, чиним на `integration`.

## Коммит (обязательно)

```bash
git add -A && git commit -m "x9: Data Trust (Волна 4.4) → main"
```
