# b27 · Risk-breakdown endpoint (идея #19, владелец §8.8)

> Трек **Backend/Data**. Против `00-CONTRACT.md` §8.8 (+ §2 формула risk_score). **Владеет:**
> `api/services/risk_breakdown_service.py`, роутер `api/routers/risk_breakdown.py` (автодискавери `api/main.py:_discover_routers` — НЕ редактируй общий `api/routers/__init__.py`).
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — детерминированная декомпозиция формулы; гейт = тесты.
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
  - **Схема ответа — ПЛОСКАЯ** (§8.8 + prep-тип `RiskBreakdown`, `web/src/api/types.ts:738`):
    `{ id, severity_w, speed_ratio, night, freq_w, weather_bonus, total_risk_score }` — НЕ массив `components[]`.
  - `weather_bonus` — в **очках score**: enrichment `weather_risk_bonus()` возвращает сырой коэффициент
    {0, 0.1, 0.2} ДО умножения на 100 → конвертировать `·100`.
  - Правило округления для точного равенства: вклады — float; `total_risk_score = кламп(round(сумма))`
    и ДОЛЖЕН равняться `risk_score` того же инцидента из `/api/incidents/{id}`.
  - **Источник истины — `api/core/enrichment.py` (функция `risk_score`, ~строка 231): ИМПОРТИРОВАТЬ
    веса/функции, не копировать константы** (дрейф формулы ловит tu-riskbreakdown).
  - Без кэша погоды → `weather_bonus = 0` (обратная совместимость, как enrichment).
  - Детерминированно (без ML/сети), чисто из enrichment.
- Роутер `GET /api/incidents/{id}/risk-breakdown`; неизвестный `id` → 404.

## Check

- `GET /api/incidents/{id}/risk-breakdown` → 200 `RiskBreakdown`; **сумма вкладов == `risk_score`** того же инцидента.
- Каждый вклад ≥ 0; `weather_bonus = 0` без кэша; детерминизм (один вход → один выход).
- Неизвестный `id` → 404. Регресс enrichment/`tu-enrichment` зелёный (не меняем формулу, только раскладываем).
- `curl -s localhost:8000/openapi.json | jq -e '.paths."/api/incidents/{id}/risk-breakdown"'` — роутер подхвачен автодискавери.
- Инвариант на **всех 55** инцидентах: `round(severity_w+speed_ratio+night+freq_w+weather_bonus)
  == total_risk_score == risk_score` (закрепляется в tu-riskbreakdown).

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# параллельно в одном worktree — стейджи только свои файлы (НЕ git add -A)
git add api/services/risk_breakdown_service.py api/routers/risk_breakdown.py
git commit -m "b27: <что сделано>"
```
