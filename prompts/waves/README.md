# prompts/hackathon — Плейбук запуска промптов

> 🖥 **Инструмент:** Cherry Studio → OpenRouter (team key)
> 💰 **Бюджет команды:** $50
> 🐍 **Стек:** Python 3.12 · Streamlit 1.44 · Pandas 2.2 · Altair 5.5
> ⏱ **6 часов** · 7 волн · **20 промптов** · 09:30–15:30

---

## 🗺 КАРТА ПАРАЛЛЕЛЬНОГО ЗАПУСКА

```
09:30 ──────────────────── 00 ──── nemotron (1 промпт)
│
09:40 ──────────────────── 00a ─── kimi-k2.6 + qwen3 (4 промпта параллельно)
│         ├─ 00a-A ──→ TECH-DESIGN.md          (kimi-k2.6)
│         ├─ 00a-B ──→ контракты данных         (kimi-k2.6)
│         ├─ 00a-C ──→ design tokens           (qwen3)
│         └─ 00a-D ──→ csv-образцы             (qwen3)
│
10:10 ──────────────────── 01 ──── qwen3 (4 промпта параллельно)
│         ├─ 01A ── models.py (dataclasses)   ──────┐
│         ├─ 01B ── constants.py (design tokens) ───┤ все
│         ├─ 01C ── data_loader.py (CSV + save) ────┤ параллельно
│         └─ 01E ── app.py (скелет) + requirements ─┘
│
10:40 ──────────────────── 02 ──── qwen3 (5 промптов параллельно)
│         ├─ 02A ── metrics.py
│         ├─ 02B ── charts.py
│         ├─ 02C ── data_overview.py
│         ├─ 02D ── actions.py
│         └─ 02E ── risk_table.py
│
11:40 ──────────────────── 03 ──── qwen3 (3 промпта, последовательно)
│         ├─ 03A ── Data tab ──── (первый)
│         ├─ 03B ── Dashboard tab (второй)
│         └─ 03C ── Details tab ── (третий)
│
13:10 ──────────────────── 04 ──── qwen3 (1 промпт)
│         └─ проверка интеграции app.py
│
13:40 ──────────────────── 05 ──── nemotron + gpt-oss (2 промпта параллельно)
│         ├─ 05C ── smoke-checklist
│         └─ 05D ── demo-script
```

---

## 🎯 Целевое приложение

Streamlit-приложение на Python с тремя вкладками (tabs):

| Вкладка | Назначение | Ключевые элементы |
|---------|------------|-------------------|
| **Data** | Обзор загруженных данных | Список CSV-файлов (строки, колонки), превью выбранного датасета (первые 100 строк) |
| **Dashboard** | Ключевые метрики и графики | 4 KPI-метрики (CSV files, Rows loaded, Candidate events, MVP status) + линейный график Altair (выбор X/Y среди числовых колонок) |
| **Details** | Риски и действия | Таблица рисков (top-20 строк по risk_score или severity) + форма сохранения действия (row_id, action type, comment) в `output/actions.csv` |

---

## 📊 Данные

CSV-файлы в `data/`:

| Файл | Ключевые колонки |
|------|-----------------|
| `selected_video_alarms.csv` | AlarmId, TelemetryId, UnitId, UnitName, UnitStateNumber, Begin, End, Type, Speed, Latitude, Longitude, VideoCount, CameraIds... |
| `video_files.csv` | alarm_id, video_file_id, channel, media_relative_path, duration_seconds, video_width, video_height, video_codec... |
| `track_summary.csv` | alarm_id, unit_state_number, event_type, total_mileage_km, track_point_count... |
| `track_points.csv` | alarm_id, timestamp_utc, latitude, longitude, speed_kmh, angle, course... |
| `track_periods.csv` | alarm_id, period_index, period_type, period_duration, track_point_count... |
| `max_speed_points.csv` | alarm_id, timestamp_utc, latitude, longitude, speed_kmh... |
| `vehicles.csv` | unit_state_number, alarm_count, alarm_types, downloaded_video_count, track_point_count, total_track_mileage_km... |
| `work_rest_single_vehicle/` | События Drowsiness для одной машины (U126TK124) |

---

## 🚀 Подготовка Cherry Studio (08:45–09:00)

1. Открыть Cherry Studio → Settings → Model Providers → OpenRouter → вставить team key
2. Добавить модели:
   - `moonshotai/kimi-k2.6` — основной кодинг (~$0.03–0.04/запрос)
   - `qwen/qwen3-coder:free` — простые модули, анализ, декомпозиция (бесплатно)
   - `nvidia/nemotron-3-super-120b-a12b:free` — чтение контекста (бесплатно)
   - `openai/gpt-oss-120b:free` — драфты, демо-сценарий (бесплатно)
3. Создать новую сессию (Cmd+N) → выбрать модель → вставить промпт → Enter
4. После каждого ответа агента: скопировать код в проект, проверить `streamlit run app/app.py`

---

## 🌊 ВОЛНА 00 — Контекст (09:30–09:40)

**Цель:** агент читает проект и проверяет понимание.

| # | Промпт | Модель | Передать | Выход | Цена |
|---|--------|--------|----------|-------|------|
| 1 | `wave-00/00-read-context--nemotron.md` | nemotron:free | только промпт | ответ по шаблону | $0 |

**Как запускать:** 1 сессия. Скопировать промпт целиком, модель nemotron, Enter. НИЧЕГО дополнительно не передавать — в промпте уже сказано «Прочитай AGENTS.md».

**Чекпоинт 00:** агент правильно назвал 8 CSV-файлов, перечислил 3 вкладки приложения, назвал стек (Python 3.12, Streamlit).

---

## 🌊 ВОЛНА 00A — Архитектура (09:40–10:10)

**Цель:** создать TECH-DESIGN.md, контракты данных, design tokens, разведать CSV.

**Все 4 промпта запускаются параллельно.**

| # | Промпт | Модель | Передать | Выход | Цена |
|---|--------|--------|----------|-------|------|
| 2 | `wave-00a-architecture/00a-A-tech-design--kimi-k2.6.md` | kimi-k2.6 | AGENTS.md (секции Goal, Inputs, Non-goals) | `hackathon/context/TECH-DESIGN.md` | ~$0.03 |
| 3 | `wave-00a-architecture/00a-B-data-contract--kimi-k2.6.md` | kimi-k2.6 | AGENTS.md (секция Inputs) | черновик контрактов данных (схемы колонок) | ~$0.03 |
| 4 | `wave-00a-architecture/00a-C-design-tokens--qwen3.md` | qwen3:free | только промпт | черновик темы/цветов/шрифтов | $0 |
| 5 | `wave-00a-architecture/00a-D-csv-samples--qwen3.md` | qwen3:free | только промпт | samples.csv — по 5 строк из каждого CSV | $0 |

**Чекпоинт 00A:** в проекте есть `hackathon/context/TECH-DESIGN.md`, описаны схемы всех CSV, зафиксированы design tokens.

---

## 🌊 ВОЛНА 01 — Foundation (10:10–10:40)

**Цель:** модели данных, константы, загрузчик CSV, скелет приложения.

**Модель:** все 4 промпта — `qwen/qwen3-coder:free` ($0). Все 4 запускаются параллельно.

| # | Промпт | Модель | Передать | Выход | Цена |
|---|--------|--------|----------|-------|------|
| 6 | `wave-01-foundation/01A-types--qwen3.md` | qwen3:free | TECH-DESIGN.md + csv-samples из 00a-D | `app/models.py` (dataclasses) | $0 |
| 7 | `wave-01-foundation/01B-constants--qwen3.md` | qwen3:free | TECH-DESIGN.md + design tokens из 00a-C | `app/constants.py` | $0 |
| 8 | `wave-01-foundation/01C-incidents-json--qwen3.md` | qwen3:free | TECH-DESIGN.md + csv-samples из 00a-D | `app/data_loader.py` (CSV loading + save_action) | $0 |
| 9 | `wave-01-foundation/01E-app-infra--qwen3.md` | qwen3:free | TECH-DESIGN.md | `app/app.py` (скелет с 3 вкладками) + `requirements.txt` | $0 |

> ⚠️ Все 4 сессии запускаются одновременно.

**Чекпоинт 01:** `python -c "from app.models import *"` — импорт без ошибок. `streamlit run app/app.py` — открываются 3 пустые вкладки.

---

## 🌊 ВОЛНА 02 — Python-модули (10:40–11:40)

**Цель:** 5 модулей для вкладок приложения.

**Модель:** все 5 промптов — `qwen/qwen3-coder:free` ($0).

**Передавать с каждым промптом:** `app/data_loader.py` + `app/models.py` + `app/constants.py`.

| # | Промпт | Модель | Выход | Назначение |
|---|--------|--------|-------|-----------|
| 10 | `wave-02-components/02A-metrics--qwen3.md` | qwen3:free | `app/metrics.py` | `build_dashboard_metrics`, `build_risk_table` |
| 11 | `wave-02-components/02B-charts--qwen3.md` | qwen3:free | `app/charts.py` | Линейный график Altair: выбор оси X и Y среди числовых колонок |
| 12 | `wave-02-components/02C-data-overview--qwen3.md` | qwen3:free | `app/data_overview.py` | Список загруженных CSV (строки × колонки) + превью первых 100 строк |
| 13 | `wave-02-components/02D-actions-form--qwen3.md` | qwen3:free | `app/actions.py` | Форма действия: row_id, action_type, comment → сохранение в `output/actions.csv` |
| 14 | `wave-02-components/02E-risk-table--qwen3.md` | qwen3:free | `app/risk_table.py` | Таблица рисков: top-20 строк, русские лейблы, сортировка по risk_score/severity |

**Как запускать:** открыть 5 вкладок Cherry Studio, запустить все 5 одновременно. Каждый промпт — независимый модуль.

**Чекпоинт 02:** `ls app/*.py | wc -l` → ≥9 файлов. Каждый модуль импортируется без ошибок.

---

## 🌊 ВОЛНА 03 — Вкладки (11:40–13:10)

**Цель:** собрать модули в три вкладки Streamlit.

**Модель:** все 3 промпта — `qwen/qwen3-coder:free` ($0). Запускать **строго последовательно** — каждая следующая вкладка может ссылаться на предыдущую.

| # | Порядок | Промпт | Модель | Вкладка | Передать | Цена |
|---|---------|--------|--------|---------|----------|------|
| 15 | **#1** | `wave-03-screens/03A-data-tab--qwen3.md` | qwen3:free | **Data tab** — обзор CSV + превью | `data_overview.py` + `data_loader.py` + TECH-DESIGN.md | $0 |
| 16 | **#2** | `wave-03-screens/03B-dashboard-tab--qwen3.md` | qwen3:free | **Dashboard tab** — KPI + график | `metrics.py` + `charts.py` + TECH-DESIGN.md | $0 |
| 17 | **#3** | `wave-03-screens/03C-details-tab--qwen3.md` | qwen3:free | **Details tab** — риски + форма | `risk_table.py` + `actions.py` + `data_loader.py` + TECH-DESIGN.md | $0 |

> ⚠️ Запускать строго по очереди. Дождаться завершения #15, потом #16, потом #17.

**Чекпоинт 03:** `streamlit run app/app.py` — все три вкладки отображаются, загружают данные, показывают контент.

---

## 🌊 ВОЛНА 04 — Интеграция (13:10–13:40)

**Цель:** проверить, что три вкладки собраны в финальный `app.py` и работают без ошибок.

| # | Промпт | Модель | Передать | Цена |
|---|--------|--------|----------|------|
| 18 | `wave-04-routing/04-routing--qwen3.md` | qwen3:free | текущий `app.py` + код трёх вкладок (из волны 03) + TECH-DESIGN.md | $0 |

**Чекпоинт 04:** `streamlit run app/app.py` — приложение запускается, все три вкладки работают как единое целое. Переключение между вкладками без ошибок.

---

## 🌊 ВОЛНА 05 — Полировка (13:40–15:30)

**Цель:** чеклист приёмочного тестирования и демо-сценарий.

| # | Промпт | Модель | Передать | Выход | Цена |
|---|--------|--------|----------|-------|------|
| 19 | `wave-05-polish/05C-smoke-checklist--nemotron.md` | nemotron:free | только промпт | `docs/SMOKE_CHECKLIST.md` | $0 |
| 20 | `wave-05-polish/05D-demo-script--gpt-oss.md` | gpt-oss:free | AGENTS.md (секция Demo script) | `hackathon/PITCH.md` | $0 |

**Запуск:** обе сессии параллельно, модели разные.

**Чекпоинт 05:** Flow 1 работает end-to-end: открыть Data → выбрать датасет → превью. Flow 2: Dashboard → все 4 KPI показывают значения → график строится по выбранным колонкам. Flow 3: Details → таблица рисков отсортирована → заполнить форму → действие записано в `output/actions.csv`.

---

## 🧩 Карта зависимостей

```
ВОЛНА 00 (контекст)
  │
  └─→ ВОЛНА 00A (архитектура) — нужен контекст из волны 00
        │
        ├─ TECH-DESIGN.md ────────────────┐
        ├─ контракты данных ──────────────┤
        ├─ design tokens ─────────────────┤
        └─ csv-образцы ───────────────────┘
        │
        └─→ ВОЛНА 01 (foundation) — нужны TECH-DESIGN + design tokens из 00a
              │
              ├─ models.py ───────────────┐
              ├─ constants.py ────────────┤ все параллельно
              ├─ data_loader.py ──────────┤
              └─ app.py (скелет) ─────────┘
              │
              └─→ ВОЛНА 02 (модули) — нужны data_loader + models + constants из 01
                    │
                    ├─ metrics.py ────────────┐
                    ├─ charts.py ─────────────┤ все параллельно
                    ├─ data_overview.py ──────┤
                    ├─ actions.py ────────────┤
                    └─ risk_table.py ─────────┘
                    │
                    └─→ ВОЛНА 03 (вкладки) — нужны модули из 02
                          │
                          ├─ 03A Data tab ──→ 03B Dashboard tab ──→ 03C Details tab
                          │
                          └─→ ВОЛНА 04 (интеграция) — нужны все три вкладки из 03
                                │
                                └─→ ВОЛНА 05 (полировка) — нужно работающее приложение из 04
```

---

## 💰 Бюджет по волнам

| Волна | Промптов | Модели | Цена |
|-------|---------|--------|------|
| 00 | 1 | nemotron:free ×1 | $0 |
| 00a | 4 | kimi-k2.6 ×2 + qwen3:free ×2 | ~$0.06 |
| 01 | 4 | qwen3:free ×4 | $0 |
| 02 | 5 | qwen3:free ×5 | $0 |
| 03 | 3 | qwen3:free ×3 | $0 |
| 04 | 1 | qwen3:free ×1 | $0 |
| 05 | 2 | nemotron:free + gpt-oss:free | $0 |
| **Итого** | **20** | | **~$0.06** |

> Запас: $49.94 из $50. Можно заменить часть qwen3:free на kimi-k2.6 для сложных модулей при необходимости.

---

## 🔧 Аварийные ситуации

| Ситуация | Действие |
|----------|----------|
| **429 (rate limit) на qwen3:free** | Переключить на `deepseek/deepseek-v4-flash:free`. Если тоже 429 → `deepseek/deepseek-v4-flash` (~$0.04/M input) |
| **kimi-k2.6 ошибка** | Подождать 30 сек, повторить. 3-я ошибка подряд → заменить на Devstral (по AGENTS.md) |
| **qwen3:free выдаёт бред** | Переключить промпт на `moonshotai/kimi-k2.6` (~$0.03/запрос) |
| **Все free-модели упали** | Все оставшиеся промпты на `deepseek/deepseek-v4-flash` (~$0.10 за всё) |
| **Python-ошибка после промпта** | Скопировать ТОЛЬКО файл с ошибкой + traceback → qwen3:free «Исправь ошибку» |
| **Агент создал не тот файл** | Перезапустить тот же промпт с уточнением «Путь к файлу: [правильный путь]» |
| **Streamlit не запускается** | Проверить `requirements.txt` → `pip install -r requirements.txt` → повторить |
| **Данные не загружаются** | Проверить пути в `data_loader.py` — пути относительны к корню проекта |
| **Агент пишет слишком длинный код** | Остановить, уточнить «Только [имя модуля], не больше 80 строк» |

---

## ✅ Шпаргалка: что передавать с каждым типом промпта

| Волна / промпт | Всегда передавать | Никогда не передавать |
|---|---|---|
| 00 (контекст) | только промпт | CSV-файлы, AGENTS.md (агент сам прочитает) |
| 00a-A, 00a-B (kimi) | AGENTS.md (секции Goal, Inputs, Non-goals) | полный AGENTS.md |
| 00a-C, 00a-D (qwen3) | только промпт | — |
| 01A, 01B, 01C (qwen3) | TECH-DESIGN.md + csv-образцы | полный AGENTS.md |
| 01E (qwen3) | TECH-DESIGN.md | — |
| 02 (все модули) | `data_loader.py` + `models.py` + `constants.py` | полный AGENTS.md |
| 03A (Data tab) | `data_overview.py` + `data_loader.py` + TECH-DESIGN.md | — |
| 03B (Dashboard tab) | `metrics.py` + `charts.py` + TECH-DESIGN.md | — |
| 03C (Details tab) | `risk_table.py` + `actions.py` + `data_loader.py` + TECH-DESIGN.md | — |
| 04 (интеграция) | текущий `app.py` + код всех трёх вкладок + TECH-DESIGN.md | — |
| 05C, 05D (полировка) | только промпт (05D: + секция Demo script из AGENTS.md) | — |

---

## 📂 Структура выходных файлов (что должно получиться)

```
app/
  __init__.py                    ← уже есть (пустой)
  models.py                      ← 01A — dataclasses
  constants.py                   ← 01B — design tokens
  data_loader.py                 ← 01C — CSV loading + save_action
  app.py                         ← 01E → 04 — скелет → финальная сборка
  metrics.py                     ← 02A — build_dashboard_metrics, build_risk_table
  charts.py                      ← 02B — Altair charts
  data_overview.py               ← 02C — dataset overview/preview helpers
  actions.py                     ← 02D — action form
  risk_table.py                  ← 02E — enhanced risk table (русские лейблы)
output/
  actions.csv                    ← запись действий из формы (02D/03C)
requirements.txt                 ← 01E
hackathon/context/
  TECH-DESIGN.md                 ← 00a-A
  DATA-CONTRACT.md               ← 00a-B
  DESIGN-TOKENS.md               ← 00a-C
  csv-samples.csv                ← 00a-D
docs/
  SMOKE_CHECKLIST.md             ← 05C
hackathon/
  PITCH.md                       ← 05D
```

---

## 🤖 Модели

| Модель | Роль | Файлы | Цена |
|--------|------|-------|------|
| **Kimi K2.5 / K2.6** (`moonshotai/kimi-k2.6`) | Основной кодинг: Tech Design, контракты данных | 00a-A, 00a-B | ~$0.03/запрос |
| **Qwen3** (`qwen/qwen3-coder:free`) | Анализ, простые модули, вкладки, сборка | 00a-C, 00a-D, вся волна 01, 02, 03, 04 | free |
| **Nemotron** (`nvidia/nemotron-3-super-120b-a12b:free`) | Чтение контекста, чеклисты | 00, 05C | free |
| **GPT-OSS** (`openai/gpt-oss-120b:free`) | Драфты, демо-сценарий | 05D | free |
| **Devstral** | Резервная модель для кодинга, если Kimi не справляется | — | ~$0.01–0.02/запрос |

> Не использовать Gemini. Не запускать несколько code-агентов на одном team API key одновременно без явного одобрения.

---

Держи этот файл открытым весь день. Каждый час сверяйся с чекпоинтами.
