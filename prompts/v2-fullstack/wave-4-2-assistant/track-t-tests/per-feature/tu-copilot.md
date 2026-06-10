# tu-copilot · Unit-тесты копилота (идея #13, модуль b21)

> Трек **Tests** (`feat/tests`, окно 3). Против `00-CONTRACT.md` §8.3/§8.4.
> **Модель:** 🔵 Sonnet — детерминированная логика против контракта; гейт = pytest.
> **Владеет:** `api/tests/unit/test_copilot.py`. Инфра — из `t1`. Гонится после `b21`.

## Цель

Покрыть детерминированную **фолбэк-ветку** копилота (без сети/ключа): роутинг в нужный tool и язык.

## Состав — `api/tests/unit/test_copilot.py`

- `chat("кто в группе риска сегодня?")` без ключа → `lang="ru"`, выбран `forecast`/`zones`, валидный `CopilotMessage`.
- `chat("show sabotage events")` (EN) → `lang="en"`, выбран `sabotage`.
- Мусор/пустой ввод → не бросает, вежливый дефолт.
- Детерминизм фолбэка (один вход → один выход); определение языка по кириллице.
- **Маршрутизация по таблице b21 (`@pytest.mark.parametrize`, ассерт по `tool_calls[].name`, §8.4):**
  - RU: «кто в группе риска сегодня?» → `forecast`/`zones`; «сравни Иванова и Петрова» → `driver_report`;
    «почему у этого ТС высокий риск?» → `list_incidents`; «саботаж за неделю» → `sabotage`;
    «кто устал за рулём?» → `fatigue`.
  - EN: "compare Ivanov and Petrov" → `driver_report`; "sabotage events" → `sabotage`;
    "fleet report" → `fleet_report`.
- Детерминизм ответа целиком: один и тот же текст дважды → идентичный `CopilotMessage` (поля и порядок).

## Check

- `pytest api/tests/unit/test_copilot.py -q` зелёный **без сети и без `GROQ_API_KEY`**.
- Роутинг в tools, язык, graceful default — проверены.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# параллельно в одном worktree — стейджи только свои файлы (НЕ git add -A)
git add api/tests/unit/test_copilot.py
git commit -m "tu-copilot: <что сделано>"
```
