# Волна 4.3 · AI Ops & Trust — измеримость, explainability, hardening + целостность экранов

Третья под-волна Волны 4 (после барьера 4.2). Не новые AI-фичи, а **слой доверия и эксплуатации**
поверх них: метрики/качество данных (#18), explainability риска (#19), security/CI/статус-баланс (#20),
а также **целостность экранов** (честная навигация, достижимость алерта #5, роль-согласованный NAV).
Кодим против `00-CONTRACT.md` **§8.7/§8.8/§8.9** (+ §8.6 governance из 4.1). Backend ∥ web ∥ tests.

> **Почему отдельная под-волна.** Это кросс-режущие, демо-независимые заботы (можно показывать 4.1+4.2
> без них), со своим гейтом. Вынесение разгружает перегруженный барьер 4.2 и отделяет «работает ли AI»
> от «можно ли это измерить/защитить/задеплоить».

| Окно | Промпты | Модель |
|---|---|---|
| 1 Backend | `b25` ai-metrics + data-quality (`/metrics/*`, `ai_metric_events`) ∥ `b26` security-baseline (auth/audit/throttle, SLO) ∥ `b27` risk-breakdown (`/risk-breakdown`, владелец #19) | b25/b27 🔵 · b26 🔴 |
| 2 Web | `f20` risk-waterfall (`/risk-breakdown` ← b27) ∥ `f21` metrics + data-quality (`/metrics`) ; **целостность экранов:** `f22` нав-интегритет (редиректы дублей + бейджи Скоро/Будущее) ∥ `f23` триггер DispatchAlert `/alert/:id` (идея #5) ∥ `f24` роль-согласованный NAV | 🔵 Sonnet |
| 3 Tests/CI | `t5` CURRENT_STATUS ∥ `t6` remote CI + nightly live-smoke ; **per-feature:** `tu-metrics` (b25) ∥ `tu-security` (b26) ∥ `tu-riskbreakdown` (b27) | t5 🟢 · остальные 🔵 |

> **Зависит от подготовки Волны 3** (`wave-3-backlog/` w3-16…w3-19): `ai_metric_events` DDL, типы/клиент/
> фикстуры (§8.7/§8.8), маршрут `/metrics`, каркас `.github/workflows/` + `scripts/gen_status.py`.
> Эти промпты — **аддитивные** поверх готового каркаса.

Дальше → **Барьер 4.3** (`../barrier-4-3-ops-trust/x8-ops-trust.md`) — e2e ops/trust + регресс всей
Волны 4 + nightly live-smoke → продвигает `main` (финал Волны 4).

> Каждый промпт заканчивается секцией `## Коммит` — merge на барьере берёт только коммиты.
> ⚠ `b25` регистрирует роутер `metrics` в `ALL_ROUTERS`.
