# tu-score · Unit-тесты позитивного и единого скоринга (фичи #25/#26, модули b33/b34)

> Трек **Tests** (`feat/tests`, окно 3). Против `00-CONTRACT.md` §13.0–§13.4.
> **Модель:** 🔵 Sonnet — формулы по контракту; гейт = pytest.
> **Владеет:** `api/tests/unit/test_positive_score.py`, `api/tests/unit/test_driver_score.py`.
> Инфра — из `t1`. Гонится после `b34`.

## Цель

Закрепить формулы §13 (веса/пороги/клампы), инварианты бленда, негативы «ТС без алармов»,
стабильность лидерборда.

## Состав — `api/tests/unit/test_positive_score.py`

- Формула на синтетике: ТС с 2 алармами (1 compliant, 1 нет; 1 HARSH) при known total_days →
  ручной расчёт §13.1 == ответ сервиса (включая `positive_score`).
- Пустой знаменатель: все `Speed` пустые → `compliant_events_ratio == 1.0` (не NaN/ZeroDivision).
- ТС без алармов → `clean_days == total_days`, ratios `1.0`, `positive_score == 100`,
  `green_zone is True`.
- `green_zone`: compliant 0.94 → False; 0.95 без critical → True; 1.0 + один critical → False.
- Лимит из enrichment: для `Type='OVERSPEED'` порог == `speed_limit_for('OVERSPEED')` (импорт, не 90-хардкод).
- 404 на неизвестный plate (TestClient); детерминизм.

## Состав — `api/tests/unit/test_driver_score.py`

- Инвариант бленда §13.2 на всём лидерборде:
  `clamp(round(risk_component + positive_component), 0, 100) == unified_score` для каждой строки.
- `risk_component == 0.6·(100 − avg_risk_score)` и `positive_component == 0.4·positive_score`
  (точность 1e-9, float без промежуточных округлений — урок b27).
- Лидерборд: длина == числу ТС в `driver_reference`; сортировка desc; tie-break по plate asc
  (синтетика: два ТС с равным score).
- ТС без алармов: `avg_risk_score == 0.0`, присутствует в лидерборде.
- `positive_score` в строке == ответу `positive_score_service.score(plate)` (вызов, не дубль).
- 404 на неизвестный plate; детерминизм (два вызова — идентичный порядок и значения).

## Check

- `pytest api/tests/unit/test_positive_score.py api/tests/unit/test_driver_score.py -q` зелёный **без сети**.
- Формулы/клампы/негативы §13 закреплены; регресс остальных юнитов не тронут.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# параллельно с f28 в соседнем worktree — стейджи только свои файлы (НЕ git add -A)
git add api/tests/unit/test_positive_score.py api/tests/unit/test_driver_score.py
git commit -m "tu-score: юниты позитивного и единого скоринга (§13)"
```
