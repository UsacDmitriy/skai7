# b33 · Позитивный скоринг водителя — green zone (фича #25, владелец §13.1)

> Трек **Backend/Data**. Против `00-CONTRACT.md` §13.0/§13.1/§13.4. **Владеет:**
> `api/services/positive_score_service.py`, `api/domain/positive.py`, роутер
> `api/routers/positive_score.py` (автодискавери — НЕ редактируй `api/routers/__init__.py`).
> **Модель:** 🔵 Sonnet — детерминированная агрегация по зафиксированным формулам; гейт = Check + tu-score.
> **Волна 5.3**, окно 1, **первый** (затем b34). Зависит от: алармы (b1), `driver_reference` (b7),
> `api/core/enrichment.speed_limit_for` (b2).

## Цель

`GET /api/positive-score/{plate}` → `PositiveScore` (§13.1): признание хорошего вождения — чистые
дни, соблюдение лимитов, отсутствие резких манёвров, бейдж «зелёной зоны» Оздоева.

## Состав

- `positive_score_service.score(plate) -> PositiveScore` — формулы **дословно §13.1**, без
  самодеятельности:
  - `total_days` = COUNT(DISTINCT date(`"Begin"`)) по ВСЕМ алармам (не хардкод); `period_days` = то же;
  - `clean_days` = `total_days` − дни с алармами этого ТС (`"UnitStateNumber"` = plate);
  - `compliant_events_ratio`: доля алармов ТС с `Speed ≤ speed_limit_for(Type)` —
    **ИМПОРТ** `from api.core.enrichment import speed_limit_for` (таблицу лимитов НЕ копировать);
    пустая/нечисловая `Speed` → аларм исключается из знаменателя; пустой знаменатель → `1.0`;
  - `harsh_free_ratio` = 1 − доля `HARSH_*`-алармов; 0 алармов → `1.0`;
  - `positive_score = round(100·(0.5·compliant + 0.3·clean_days/total_days + 0.2·harsh_free))`;
  - `green_zone = compliant >= 0.95 и нет critical-алармов ТС` (severity из enrichment-маппинга
    инцидентов — переиспользовать готовое, не изобретать);
  - plate не из `driver_reference` → 404; ТС без алармов → ratios `1.0`, `clean_days=total_days` (§13.4).
- `api/domain/positive.py` — Pydantic `PositiveScore` **дословно §13.1**.
- Роутер `GET /api/positive-score/{plate}` — модульный `router = APIRouter(...)`.

Пример ответа (формат — ровно такой):

```json
{ "vehicle_plate": "T780РН198", "period_days": 2, "total_days": 2, "clean_days": 1,
  "compliant_events_ratio": 0.83, "harsh_free_ratio": 0.67,
  "positive_score": 70, "green_zone": false }
```

## Check

- `curl -s localhost:8000/api/positive-score/<plate с алармами> | jq -e '.positive_score>=0 and .positive_score<=100'`.
- ТС из `driver_reference` без алармов → 200: `clean_days==total_days`, ratios `1.0`,
  `positive_score==100`, `green_zone==true` (нет critical) — не 5xx/NaN.
- 404 на `__nope__`. Формула: пересчитать вручную для одного ТС — сходится с §13.1.
- `grep -n "speed_limit_for" api/services/positive_score_service.py` — импорт из enrichment (не копия).
- `curl -s localhost:8000/openapi.json | jq -e '.paths."/api/positive-score/{plate}"'` — автодискавери.
- Детерминизм: два вызова → идентично. `pytest api/tests/unit -q` зелёный.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# стейджи только свои файлы (НЕ git add -A)
git add api/services/positive_score_service.py api/routers/positive_score.py api/domain/positive.py
git commit -m "b33: позитивный скоринг + green zone — /api/positive-score (§13.1)"
```
