# b27 · Risk-breakdown endpoint (идея #19, владелец §8.8)

> Трек **Backend/Data**. Против `00-CONTRACT.md` §8.8 (+ §2 формула risk_score). **Владеет:**
> `api/services/risk_breakdown_service.py`, роутер `api/routers/risk_breakdown.py` (в `ALL_ROUTERS`).
> **Модель:** 🔵 Sonnet — детерминированная декомпозиция формулы; гейт = тесты.
> **Волна 4.3**, окно 1 (backend). Зависит от: `enrichment.py` (risk_score, §2), b17 (`weather_bonus`, §8.2).
> Потребитель — `f20` risk-waterfall. **Закрывает «висящий» эндпоинт #19** (раньше владельца не было).

## Цель

Дать backend для explainability: `GET /api/incidents/{id}/risk-breakdown` → `RiskBreakdown` (§8.8) —
вклад каждого слагаемого `risk_score`, чтобы фронт (`f20`) нарисовал waterfall. **Сумма вкладов = risk_score.**

## Состав

- `risk_breakdown_service.breakdown(id) -> RiskBreakdown`:
  - Зеркалит формулу §2/§8.2: `severity_w` (0.45·sev_w), `speed_ratio` (0.25·…), `night` (0.15·…),
    `freq_w` (0.15·…), `weather_bonus` (надбавка b17, §8.2) — каждый как **абсолютный вклад в 0..100**.
  - `total` = сумма вкладов = `risk_score` инцидента (клампится так же).
  - Без кэша погоды → `weather_bonus = 0` (обратная совместимость, как enrichment).
  - Детерминированно (без ML/сети), чисто из enrichment.
- Роутер `GET /api/incidents/{id}/risk-breakdown`; неизвестный `id` → 404.

## Check

- `GET /api/incidents/{id}/risk-breakdown` → 200 `RiskBreakdown`; **сумма вкладов == `risk_score`** того же инцидента.
- Каждый вклад ≥ 0; `weather_bonus = 0` без кэша; детерминизм (один вход → один выход).
- Неизвестный `id` → 404. Регресс enrichment/`tu-enrichment` зелёный (не меняем формулу, только раскладываем).

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
git add -A && git commit -m "b27: <что сделано>"
```
