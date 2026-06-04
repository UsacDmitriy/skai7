# b9 · NLU-сервис — nlu_service.py

> Трек **Backend/Data**. Против `00-CONTRACT.md` §7.3/§7.5. **Владеет:** `api/services/nlu_service.py`.
> Кодит против контракта. **Зависит от:** b4 (`groq` в `api/requirements.txt`, конфиг `groq_api_key` в `api/core/config.py`). Использует схему `ReportQuery` из b5 (домен `reports`). Параллелится с b7/b8/b11/b12. Потребитель — `reports_service` (b10) и `POST /api/reports/query` (b6+).

## Цель

Превратить свободный текст запроса («Нарушения Иванова за 3 дня», «отчёт по парку за неделю по ТС»)
в структурированный `ReportQuery`. **Основной путь** — Groq API + LLaMA 3.3 70B; **fallback** —
локальный детерминированный regex-парсер. Обе ветки возвращают **одинаковую** `ReportQuery`.

## Контракт результата (§7.5)

```text
ReportQuery { kind: "driver"|"fleet", plate?: str, driver_name?: str, period_days?: int=3, view?: "drivers"|"vehicles" }
```

Импортировать `ReportQuery` из домена b5 (`api/domain/reports.py`), не дублировать модель.

## Модуль `api/services/nlu_service.py`

- Сигнатура (точно по §7.3):
  ```python
  def parse(text: str) -> ReportQuery: ...
  ```
- **Ветка Groq** (`_parse_groq(text) -> ReportQuery`):
  - Активна, если `settings.groq_api_key` задан. Импорт `groq` — внутри функции (ленивость).
  - Structured JSON prompt: системное сообщение описывает поля `ReportQuery` и enum-значения;
    модель `llama-3.3-70b-versatile`; `response_format={"type":"json_object"}`, `temperature=0`.
  - Распарсить JSON → валидировать через `ReportQuery(**data)` (Pydantic нормализует/проверит enum).
  - Любая ошибка (нет ключа, сеть, невалидный JSON, ошибка валидации) → проброс в `parse`,
    который ловит и уходит в fallback.
- **Ветка fallback** (`_parse_regex(text) -> ReportQuery`), детерминированная:
  - Госномер (`plate`) — regex по формату RU/KK номеров; если найден → `kind="driver"`, `plate=...`.
  - ФИО (`driver_name`) — фамилия/И.О. (кириллица с заглавной); если найдено и нет plate → `kind="driver"`.
  - Период (`period_days`) — «за N дней/дня/день», «неделю»→7, «месяц»→30; иначе дефолт `3`.
  - `view` — «по ТС/машинам»→`"vehicles"`, «по водителям»→`"drivers"` (для fleet).
  - Если ни plate, ни ФИО → `kind="fleet"`.
- `parse`: try Groq → except → regex. **Никогда не падает** на пустом/мусорном тексте
  (минимум вернёт `ReportQuery(kind="fleet", period_days=3)`).

## Check

- `from api.services.nlu_service import parse` импортируется без сети и без `groq`-ключа.
- Без `GROQ_API_KEY`: `parse("Нарушения Иванова за 3 дня")` → `kind="driver"`, `driver_name` содержит «Иванов», `period_days=3`.
- `parse("отчёт по парку за неделю по ТС")` → `kind="fleet"`, `period_days=7`, `view="vehicles"`.
- `parse("")` не бросает исключение и возвращает валидный `ReportQuery` (`kind="fleet"`).
- При заданном `GROQ_API_KEY` и недоступной сети `parse` молча уходит в regex (нет необработанного исключения).
- Обе ветки возвращают объект типа `ReportQuery` (одинаковая схема).
