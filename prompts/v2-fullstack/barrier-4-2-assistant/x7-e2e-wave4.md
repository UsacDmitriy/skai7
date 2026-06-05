# x7 · e2e AI-слой (Волна 4) → main

> **Барьер-волна, финал Волны 4.** **Владеет:** только запуск/проверки (e2e + регресс). Авторство тестов — трек T.
> **Модель:** 🔴 Opus — интеграция/приёмка/продвижение `main`.
> Запускать ПОСЛЕ Волны 4.2 (b21–b23, f15–f19, tu-copilot, t-wave4-frontend) и зелёного x6.

## Перед стартом — склейка Волны 4.2 (main держим стабильным)

В окне `skai_7` на ветке `integration`. **`main` = стабильный P1/P2 — не трогаем**, пока e2e не зелёный.

```bash
cd /Users/dimausac/projects/skai_7
git checkout integration

# GUARD: merge берёт только коммиты — стоп, если в worktree есть незакоммиченные изменения.
for w in backend web tests; do
  d=".worktrees/$w"; [ -d "$d" ] || continue
  test -z "$(git -C "$d" status --porcelain)" || { echo "❌ $w: незакоммичено — закоммить в worktree и повтори барьер"; exit 1; }
done

git merge feat/backend feat/web feat/tests   # 4.2: b21–b23, f15–f19, tu-copilot, t-wave4-frontend
```

## Проверка предыдущего шага (x6 · умное событие/прогнозы зелёный)

Не начинай e2e, пока x6 (smoke 4.1) не подтверждён: `incident_scene`/`incident_weather` собраны, `/forecast`/`/zones`/`/fatigue` отвечают.

## Цель

End-to-end по всему AI-слою на кэше/фолбэке (офлайн): данные → backend → UI → приёмка.

## Шаги

1. `make db` → `incident_scene`/`incident_weather`=54, `v_risk_zones` непуст.
2. `make api`: `/incidents/{id}/scene`, `/reports/forecast/{plate}`, `/zones`, `/fatigue`,
   `POST /api/copilot/chat` (RU и EN, без ключа → фолбэк) → все 200, схемы §8.4.
3. `pytest api/tests/unit -q` (включая `tu-scene/weather/forecast/zones/fatigue/copilot`) — зелёный; регресс P0/P1/P2 не сломан.
4. `make web` + `npm run typecheck`: карточка показывает сцену+расхождение; отчёт — спарклайн+рекомендации;
   копилот отвечает; монитор — heatmap+зоны (incident/reb); виджет саботажа — умный вердикт. `npm run test` зелёный.

## Критерии приёмки

- Все 6 идей (#11–#16) проходят сквозь стек на офлайн-кэше; нет сети/ключей — не падает (фолбэк).
- Обратная совместимость: P0/P1/P2 регресс зелёный (risk_score/sabotage/отчёты не сломаны).
- Типы §8.4 совпадают; фронт без ошибок typecheck.

## Финализация — продвинуть main

**Только если все критерии зелёные:**

```bash
git -C /Users/dimausac/projects/skai_7 checkout main
git merge --ff-only integration       # main догоняет integration (fast-forward)
# если ff-only падает → git merge --no-ff integration -m "merge integration → main (Волна 4 AI-слой)"
git checkout integration
```

Красный e2e → **`main` НЕ трогаем**, дефект треку, чиним на `integration`.

## Коммит (обязательно)

Барьер фиксирует smoke-правки (если были) в `integration`:

```bash
git add -A && git commit -m "x7: e2e wave 4 (AI-слой) → main"
```
