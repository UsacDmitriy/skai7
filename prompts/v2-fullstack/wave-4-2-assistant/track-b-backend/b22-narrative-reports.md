# b22 · Narrative reports — нарратив + коучинг (идеи #12/#13)

> Трек **Backend/Data**. Против `00-CONTRACT.md` §8.3/§8.4. **Владеет:** `api/services/narrative_service.py`;
> **аддитивно** дополняет `reports_service`/`forecast_service` (логика) **и** `api/domain/reports.py`
> (поле `narrative` в Pydantic-схемах `DriverReport`/`FleetReport` — иначе FastAPI отбросит его из ответа).
> **Модель:** 🔵 Sonnet — генерация текста по шаблону + опц. LLM; гейт = тесты.
> **Волна 4.2**, окно 1 (backend). Зависит от: b18 (`RiskForecast`), reports (`DriverReport`/`FleetReport`).

## Цель

Из структурных данных отчёта/прогноза собрать **читаемый нарратив** (резюме + анализ причин + 3 коучинг-
пункта + признание) — для В-1/В-2 и копилота. Детерминированный шаблон, опц. усиление LLM (Groq).

## Состав

- `narrative_service.narrate(report|forecast, lang?) -> str`:
  - **Шаблон-ветка** (всегда доступна, без сети): структурированные правила → связный текст RU/EN.
  - **LLM-ветка** (опц., Groq): тот же контент «дороже»; ошибка/нет ключа → шаблон.
  - Без выдумок: только факты из данных (no hallucination — числа из payload).
- Поле `narrative: str | None = None` объявляется в Pydantic-схемах `DriverReport`/`FleetReport`
  (`api/domain/reports.py`) и `RiskForecast` (`forecast_service.py` — поле уже есть), затем наполняется
  в сервисах. Аддитивно (default `None`) — не ломает схему/обратную совместимость.

## Детерминизм и персистентность narrative (доспецификация, аудит 2026-06-10)

> Код уже выполнен в `feat/backend` (29404ff) — секция фиксирует требования; красный x7 чинить по ней.

- `narrative` вычисляется **per-request** и НЕ персистится (никаких записей в DuckDB/файлы).
- Шаблон-ветка **байт-идентична** на одинаковом payload: без `Date.now()`/random/недетерминированного
  порядка dict — ключи и списки сортировать явно.
- Шаблон-ветка **никогда не возвращает `None`** и не бросает: пустой отчёт → фиксированная строка
  «нет нарушений за период»; ошибка/таймаут LLM-ветки → тихий фолбэк в шаблон (без исключения).
- Поле остаётся `narrative: str | None = None` в Pydantic-схеме (обратная совместимость), но сервис
  обязан заполнить его в каждом успешном ответе `/reports/driver|fleet` и `/reports/forecast/{plate}`.

## Check

- `narrate(driver_report)` без сети → непустой осмысленный текст; числа совпадают с payload.
- RU/EN по `lang`; пустой отчёт → корректный «нет нарушений за период».
- LLM-ветка падает/нет ключа → шаблон (без исключения). Детерминизм шаблона.
- Два одинаковых запроса без `GROQ_API_KEY` → побайтно идентичный `narrative` (diff пуст).
- `narrative` не `null` ни в одном успешном ответе `/reports/driver|fleet` и `/reports/forecast/{plate}`.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# параллельно в одном worktree — стейджи только свои файлы (НЕ git add -A)
git add api/services/narrative_service.py api/services/reports_service.py api/services/forecast_service.py api/domain/reports.py
git commit -m "b22: <что сделано>"
```
