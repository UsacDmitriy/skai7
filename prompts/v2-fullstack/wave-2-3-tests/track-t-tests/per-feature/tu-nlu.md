# tu-nlu · Unit-тесты NLU regex-fallback (фича #2, модуль b9)

> Трек **Tests** (`feat/tests`, окно 3). Против `00-CONTRACT.md` §7.3/§7.5.
> **Модель:** 🔵 Sonnet — детерминированная логика против контракта; гейт = pytest.
> **Владеет:** `api/tests/unit/test_nlu_fallback.py`. Инфраструктура — из `t1`.
> Тестируем **детерминированную regex-ветку** `b9` (без сети, без `GROQ_API_KEY`). Баг → дефект треку B.

## Цель

Покрыть `nlu_service.parse` в режиме fallback: свободный текст → корректный `ReportQuery` без
обращения к Groq. Проверяем именно детерминированную ветку (Groq-ветка — не unit-уровень).

## Состав — `api/tests/unit/test_nlu_fallback.py`

- `parse("Нарушения Иванова за 3 дня")` (без ключа) → `kind="driver"`, `driver_name` содержит «Иванов», `period_days=3`.
- `parse("отчёт по парку за неделю по ТС")` → `kind="fleet"`, `period_days=7`, `view="vehicles"`.
- Госномер в тексте → `kind="driver"`, `plate` распарсен; «месяц» → `period_days=30`.
- `parse("")` и мусор-текст → не бросает, возвращает валидный дефолт `ReportQuery(kind="fleet", period_days=3)`.
- Обе ветки возвращают объект типа `ReportQuery` (схема одинакова).

## Check

- `pytest api/tests/unit/test_nlu_fallback.py -q` зелёный **без сети и без `GROQ_API_KEY`**.
- Ни один кейс не падает на пустом/мусорном вводе (graceful default).
- Углубление покрытия nlu — в `w3-3`.
