# f20 · Risk-cause waterfall — explainability (по research-отчёту)

> Трек **Frontend**. Против `00-CONTRACT.md` §8.8. **Владеет:** `web/src/components/ai/RiskWaterfall.tsx`;
> **аддитивная** правка `IncidentCard.tsx`/`Report.tsx`. Использует f2-клиент.
> **Модель:** 🔵 Sonnet — вёрстка визуализации против контракта; гейт = typecheck.
> **Волна 4.3** (AI Ops & Trust), окно 2 (web). Зависит от: `GET /api/incidents/{id}/risk-breakdown`
> (детерминированно из enrichment, §8.3/§8.8); типы/клиент/фикстуры — из prep `w3-17`.

## Цель

Показать **почему** у инцидента такой `risk_score`: waterfall-разложение по вкладам (severity / speed /
night / weather / freq). Чистая explainability — повышает доверие к скорингу, ничего не «магического».

## Состав

- f2-клиент: `getRiskBreakdown(id) → RiskBreakdown` (§8.8).
- `RiskWaterfall.tsx` — горизонтальный waterfall: базовый вклад severity → +speed → +night → +weather →
  +freq → итог `risk_score`; подписи и `tabular-nums`; цвет вклада по знаку/величине.
- Встроить в карточку инцидента (раскрывашка «Почему такой риск») и в строку отчёта.

## Check

- На карточке/в отчёте waterfall показывает вклады, сумма = `risk_score` (совпадает с API).
- Нет `weather_bonus` (без кэша) → вклад 0, не ломается. `npm run typecheck` зелёный.
- Регрессий по f14/f16 нет (блок аддитивный, раскрывашка).

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
git add -A && git commit -m "f20: <что сделано>"
```
