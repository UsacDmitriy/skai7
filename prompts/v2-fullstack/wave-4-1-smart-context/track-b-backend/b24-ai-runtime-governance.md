# b24 · AI runtime-governance — флаги, бюджеты, кэш-политика (по research-отчёту)

> Трек **Backend/Data**. Против `00-CONTRACT.md` §8.6. **Владеет:** `api/core/ai_flags.py`,
> `api/core/ai_runtime.py` (обёртка latency/cache); **аддитивная** мета в AI-ответах.
> **Модель:** 🔵 Sonnet — детерминированная конфигурация/обёртка; гейт = тесты.
> **Волна 4.1**, окно 1 (backend). Кросс-режущая основа для b16–b20 (и b21–b23 в 4.2).

## Цель

Сделать AI-слой **управляемым и непрозрачным-устойчивым**: feature-flags на каждую фичу, latency-budget,
offline-cache policy/TTL, единый контракт деградации. Без сети/превышения бюджета — кэш/фолбэк, не падение.

## Состав

- `api/core/ai_flags.py` — флаги `scene/forecast/zones/fatigue/copilot/verdict` (env + дефолты);
  выключенная фича → эндпоинт отдаёт «feature disabled» (HTTP 200 с пустым телом/флагом), не 5xx.
- `api/core/ai_runtime.py` — декоратор/обёртка: измеряет `latency_ms`, применяет `latency_budget_ms`
  (превышение → кэш/деградация), читает кэш `data/ai/*` по TTL-политике. Источник ответа помечается
  `source ∈ {live,cache,fallback}`.
- Мета `AiFeatureState { name, enabled, source, latency_ms }` (§8.6) добавляется в ответы AI-эндпоинтов.

## Зависимости

Без сети/ML. Детерминизм: бюджеты/TTL — из конфига, без `Date.now()` в логике (время латентности — для меты).

## Check

- Флаг `forecast=off` → `/api/reports/forecast/{plate}` отдаёт «disabled» (200), не падает; UI скрывает блок.
- Превышение latency-budget → `source="cache"`/`"fallback"`, ответ не блокируется.
- Нет сети → AI-эндпоинты отдают кэш (`source="cache"`); мета `AiFeatureState` присутствует.
- Существующие AI-фичи продолжают работать с флагом `on` (регресс tu-* зелёный).

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
git add -A && git commit -m "b24: <что сделано>"
```
