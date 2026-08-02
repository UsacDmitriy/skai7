# b21 · Fleet Copilot — разговорный ассистент (идея #13)

> Трек **Backend/Data**. Против `00-CONTRACT.md` §8.3/§8.4. **Владеет:** `api/services/copilot_service.py`,
> роутер `api/routers/copilot.py` (автодискавери `api/main.py:_discover_routers` — НЕ редактируй общий `api/routers/__init__.py`). Расширяет паттерн `nlu_service`.
> **Исполнение:** owner-only gate — Claude/Codex; ClinePass excluded from shared contracts, integration, deterministic acceptance, and commit — оркестрация LLM tool-use, надёжный фолбэк, двуязычность.
> **Волна 4.2**, окно 1 (backend). Зависит от: существующие сервисы (incidents/reports/forecast/zones/fatigue/sabotage);
> **b24** (Волна 4.1, выполнен) — флаг `copilot` и мета `AiFeatureState` из `api/core/ai_flags.py`/`ai_runtime.py`.

## Цель

`POST /api/copilot/chat` → `CopilotMessage` (§8.4): свободный запрос (RU/EN) → LLM выбирает инструмент
из данных SKAI → ответ + данные. «Кто в группе риска сегодня?», «сравни Иванова и Петрова»,
«почему у этого ТС высокий риск?».

## Состав

- `copilot_service.chat(text, lang?) -> CopilotMessage`:
  - **Tools** (вызовы существующих сервисов, без дублирования логики): `list_incidents`, `driver_report`,
    `fleet_report`, `forecast`, `zones`, `fatigue`, `sabotage`. Каждый tool — тонкая обёртка над сервисом.
  - **Ветка Groq** (`settings.groq_api_key`): function-calling/structured tool-selection (модель из конфига,
    `temperature=0`), затем нарратив ответа (через b22).
  - **Фолбэк** (детерминированный, без сети/ключа): правила-роутинг по ключевым словам RU/EN →
    тот же tool → шаблонный ответ. **Никогда не падает** (минимум — вежливый «уточните запрос»).
  - `lang` определяется по тексту (кириллица→ru); ответ на языке запроса.
- Роутер `POST /api/copilot/chat`.
- **Governance/доверие (по research-отчёту, §8.6/§8.7/§8.9):**
  - **Цитирование фактов:** в ответе ссылаться на источник из системы (id инцидента/отчёта/зоны), не выдумывать числа.
  - **Feature-flag** `copilot` (b24) + **latency-budget** (превышение → краткий фолбэк), мета `AiFeatureState`.
  - **Audit-trail** (b26): каждый вызов tool пишется в `output/audit.csv`; событие `copilot_tool_success` → метрики (b25).

## Tool-схема и фолбэк-маршрутизация (доспецификация, аудит 2026-06-10)

> Код уже выполнен в `feat/backend` (73bd1d8) — секция фиксирует обязательный формат как источник истины.
> Красный x7 по маршрутизации/схеме → дефект чинится по этой секции.

**Формат tool-определения — Groq function-calling (OpenAI-совместимый), пример `list_incidents`:**

```json
{
  "type": "function",
  "function": {
    "name": "list_incidents",
    "description": "Список инцидентов с фильтрами (severity/plate/limit)",
    "parameters": {
      "type": "object",
      "properties": {
        "severity": {"type": "string", "enum": ["critical", "warning", "info"]},
        "vehicle_plate": {"type": "string", "description": "госномер ТС"},
        "limit": {"type": "integer", "default": 10}
      },
      "required": []
    }
  }
}
```

**Таблица маршрутизации фраза → tool (фолбэк-regex, RU/EN, без сети):**

| Паттерн (regex, флаг i) | Tool(s) | Пример фразы |
|---|---|---|
| `групп[ае] риска \| кто рискует \| high.?risk \| risky` | `forecast` + `zones` | «кто в группе риска сегодня?» |
| `сравни \| compare` | `driver_report` ×2 (оба имени) | «сравни Иванова и Петрова» |
| `почему.*(риск\|score) \| why.*(risk\|score)` | `list_incidents` + объяснение risk | «почему у этого ТС высокий риск?» |
| `саботаж \| tamper \| sabotage` | `sabotage` | «show sabotage events» |
| `устал \| сонлив \| drowsy \| fatigue \| yawn` | `fatigue` | «кто устал за рулём?» |
| `инцидент \| событи \| incident \| event` | `list_incidents` | «события за сегодня» |
| `отч[её]т \| парк \| fleet \| report` | `fleet_report` | «отчёт по парку» |
| — нет совпадений — | без tool | вежливое «уточните запрос» |

Правила:
- Фолбэк зовёт **те же** tool-функции, что и Groq-ветка (никакого дублирования логики).
- В обеих ветках выбранные инструменты отражаются в `tool_calls: {name,args}[]` ответа (§8.4) —
  по ним проверяется маршрутизация (tu-copilot, x7).

## Check

- `from api.services.copilot_service import chat` импортируется без сети и без `groq`.
- Без `GROQ_API_KEY`: `chat("кто в группе риска сегодня?")` → валидный `CopilotMessage`, вызван `forecast`/`zones`, `lang="ru"`.
- `chat("compare drivers ...")` (EN) → `lang="en"`, осмысленный ответ.
- Мусор/пустой ввод → не бросает, вежливый дефолт.
- При заданном ключе и нет сети — молчаливый уход в фолбэк (как nlu).
- `chat("сравни Иванова и Петрова")` → в `tool_calls` есть `driver_report`; `chat("show sabotage events")` → `sabotage`.
- Каждая строка таблицы маршрутизации → объявленный tool в `tool_calls` (параметризованные кейсы — tu-copilot).

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# параллельно в одном worktree — стейджи только свои файлы (НЕ git add -A)
git add api/services/copilot_service.py api/routers/copilot.py
git commit -m "b21: <что сделано>"
```
