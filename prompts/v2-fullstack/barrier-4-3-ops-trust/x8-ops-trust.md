# x8 · AI Ops & Trust (Волна 4.3) → main · ФИНАЛ Волны 4

> **Барьер-волна, финал всей Волны 4.** **Владеет:** только запуск/проверки (e2e ops/trust + полный
> регресс + live-smoke + продвижение `main`). Авторство — трек T/Backend. **Модель:** 🔴 Opus — интеграция/
> приёмка/продвижение `main`. Запускать ПОСЛЕ Волны 4.3 (b25, b26, f20, f21, t5, t6) и зелёного x7.

## Перед стартом — склейка Волны 4.3 (main держим стабильным)

В окне `skai_7` на ветке `integration`. **`main` = стабильный P1/P2 — не трогаем**, пока финал не зелёный.

```bash
cd /Users/dimausac/projects/skai_7
git checkout integration

# GUARD: merge берёт только коммиты — стоп при незакоммиченном worktree.
for w in backend web tests; do
  d=".worktrees/$w"; [ -d "$d" ] || continue
  test -z "$(git -C "$d" status --porcelain)" || { echo "❌ $w: незакоммичено — закоммить и повтори барьер"; exit 1; }
done

git merge feat/backend feat/web feat/tests   # 4.3: b25, b26, f20, f21, t5, t6
```

## Проверка предыдущих шагов (x6 + x7 зелёные)

Не начинай финал, пока:
- **x6** (smoke 4.1): `incident_scene`/`incident_weather`/`v_risk_zones` собраны; governance-мета есть.
- **x7** (e2e 4.2): копилот/сцена/прогноз/heatmap/вердикт работают на фолбэке; регресс P0–P2 + Волна 3 зелёный.

## Цель

Закрыть **измеримость (#18), explainability (#19), hardening (#20)** и подтвердить, что весь AI-слой
наблюдаем/защитим/воспроизводим на **живом** API (а не только на фикстурах). Затем продвинуть `main`.

## Шаги (§8.6–§8.9)

1. **Governance (b24, регресс):** флаг `forecast=off` → эндпоинт «disabled» (200), UI скрывает блок;
   превышение latency-budget → `source="cache"/"fallback"`; мета `AiFeatureState` во всех AI-ответах.
2. **Метрики/качество (b25, f21):** `GET /api/metrics/ai` и `GET /api/metrics/data-quality` → 200,
   схемы §8.7; `*_ratio ∈ [0,1]`; экран `/metrics` рисует KPI + data-quality (светофор). Пустые события → дефолты.
3. **Explainability (f20):** `GET /api/incidents/{id}/risk-breakdown` → 200 (§8.8); waterfall на карточке/в
   отчёте, **сумма вкладов = `risk_score`** (зеркалит §2; без кэша погоды вклад weather=0).
4. **Status (t5):** `python scripts/gen_status.py` детерминированно обновляет `CURRENT_STATUS.md`;
   перечень эндпоинтов/таблиц совпадает с фактическими роутерами/`api/sql` (не с README).
5. **CI (t6):** CI-workflow зелёный на чистом checkout (lint/typecheck/test = зеркало `scripts/check.sh`);
   **nightly smoke на ЖИВОМ API** (`VITE_USE_FIXTURES=false`) проходит и краснеет при backend-регрессе.
6. **Security (b26, если `SECURITY_ENABLED=true`):** без токена → 401; мутации пишут `output/audit.csv`;
   throttle на `/copilot/chat`/STT → 429; `docs/SLO.md` существует. В dev (`false`) — всё как раньше.

## Универсальный гейт + негативы ops/trust (обязательно — ФИНАЛ)

Прогнать **полный** [`../barrier-CHECKLIST.md`](../barrier-CHECKLIST.md): `bash scripts/check.sh` целиком
(весь регресс P0/P1/P2/Волна 3/4.1/4.2), `make openapi` валиден, и в финале — git-пост-условие ff-merge.

Негативы/инварианты измеримости и explainability (доп.):
```bash
# §8.8 explainability: сумма вкладов = risk_score (точно)
curl -s localhost:8000/api/incidents/<id>/risk-breakdown \
  | jq -e '([.components[].contribution]|add*100|round) == .total_risk_score'
test "$(curl -s -o /dev/null -w '%{http_code}' localhost:8000/api/incidents/__nope__/risk-breakdown)" = 404
# §8.7 метрики/качество: доли в [0,1], пустые события → дефолты, не 5xx
curl -s localhost:8000/api/metrics/data-quality | jq -e 'to_entries|all(.value>=0 and .value<=1)'
curl -s localhost:8000/api/metrics/ai | jq -e 'type=="object"'
# §8.9 security: dev off — как раньше; on — 401 без токена; throttle → 429
SECURITY_ENABLED=true curl -s -o /dev/null -w '%{http_code}' localhost:8000/api/incidents   # → 401
# live-smoke: НЕ фикстуры
VITE_USE_FIXTURES=false  # nightly-smoke бьёт живой API
```
- Детерминизм: `risk-breakdown`/`metrics` дважды → идентично. `python scripts/gen_status.py` дважды → идентичный `CURRENT_STATUS.md`.

## Критерии приёмки

- Все идеи **#11–#20** проходят сквозь стек; нет сети/ключей — не падает (фолбэк/кэш); негативы 404/401/[0,1] зелёные.
- **Полный** `scripts/check.sh` зелёный; сумма вкладов `risk-breakdown` точно = `risk_score`.
- **Live-API smoke зелёный** (fixtures не маскируют backend-регресс) — ключевая страховка #20.
- Полный регресс зелёный: P0/P1/P2 + Волна 3 (fleet-health/тёмные данные) + Волна 4.1/4.2.
- `risk-breakdown` суммируется в `risk_score`; `metrics`/`data-quality` детерминированы; `CURRENT_STATUS.md` точен.
- Типы §8.4/§8.7/§8.8 совпадают; фронт typecheck зелёный.

## Финализация — продвинуть main (ФИНАЛ Волны 4)

**Только если все критерии зелёные:**

```bash
git -C /Users/dimausac/projects/skai_7 checkout main
git merge --ff-only integration       # main догоняет integration (fast-forward)
# если ff-only падает → git merge --no-ff integration -m "merge integration → main (Волна 4 финал · ops & trust)"
git checkout integration
```

Красный финал → **`main` НЕ трогаем** (остаётся на стабильном P1/P2 + Волна 3), дефект треку, чиним на `integration`.

## Коммит (обязательно)

```bash
git add -A && git commit -m "x8: AI Ops & Trust (Волна 4.3) → main · финал Волны 4"
```
