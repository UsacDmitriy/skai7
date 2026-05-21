# prompts/hackathon — Плейбук запуска промптов

> 🖥 **Инструмент:** Cherry Studio → OpenRouter (team key)
> 💰 **Бюджет команды:** $50
> 🐍 **Стек:** Python 3.12 · Streamlit 1.44 · Pandas 2.2 · Altair 5.5
> ⏱ **6 часов** · 7 волн · **20 промптов**

---

## 🗺 КАРТА ПАРАЛЛЕЛЬНОГО ЗАПУСКА

```
09:30 ──────────────────── 00 ──── nemotron (1 промпт)
│
09:40 ──────────────────── 00a ─── qwen (4 промпта параллельно)
│         ├─ 00a-A ──→ TECH-DESIGN.md
│         ├─ 00a-B ──→ контракты данных
│         ├─ 00a-C ──→ design tokens
│         └─ 00a-D ──→ csv-samples
│
10:00 ──────────────────── 01 ──── kimi + qwen (4 промпта)
│         ├─ 01A ── data_loader.py (kimi) ──────┐
│         ├─ 01B ── metrics.py (kimi) ──────────┤ параллельно
│         ├─ 01C ── app.py skeleton (qwen) ─────┤
│         └─ 01D ── requirements.txt (qwen) ────┘
│
10:30 ──────────────────── 02 ──── qwen (5 промптов параллельно)
│         ├─ 02A ── risk_table.py
│         ├─ 02B ── charts.py
│         ├─ 02C ── kpi.py
│         ├─ 02D ── actions.py
│         └─ 02E ── data_overview.py
│
11:30 ──────────────────── 03 ──── kimi (3 промпта, последовательно)
│         ├─ 03A ── Data tab ── (первый)
│         ├─ 03B ── Dashboard tab (второй)
│         └─ 03C ── Details tab (третий)
│
13:00 ──────────────────── 04 ──── kimi (1 промпт)
│         └─ финальная сборка app.py
│
13:30 ──────────────────── 05 ──── nemotron + gpt-oss (2 промпта параллельно)
│         ├─ 05A ── smoke-checklist
│         └─ 05B ── demo-script
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
   - `moonshotai/kimi-k2.5` — основной кодинг (~$0.03–0.04/запрос)
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

**Как запускать:** 1 сессия. Скопировать промпт целиком, модель nemotron, Enter. НИЧЕГО дополнительно не передавать — в промпте уже сказано «Прочитай agents.md».

**Чекпоинт 00:** агент правильно назвал 8 CSV-файлов, перечислил 3 вкладки приложения, назвал стек (Python 3.12, Streamlit).

---

## 🌊 ВОЛНА 00A — Архитектура (09:40–10:00)

**Цель:** создать TECH-DESIGN.md, контракты данных, design tokens, разведать CSV.

**Модель:** все 4 промпта — `qwen/qwen3-coder:free` ($0). Все 4 запускаются параллельно.

| # | Промпт | Передать | Выход | Цена |
|---|--------|----------|-------|------|
| 2 | `wave-00a-architecture/00a-A-tech-design--qwen.md` | agents.md (секции Goal, Inputs, Non-goals) | `hackathon/context/TECH-DESIGN.md` | $0 |
| 3 | `wave-00a-architecture/00a-B-data-contract--qwen.md` | agents.md (секция Inputs) | черновик контрактов данных (схемы колонок) | $0 |
| 4 | `wave-00a-architecture/00a-C-design-tokens--qwen.md` | только промпт | черновик темы/цветов/шрифтов | $0 |
| 5 | `wave-00a-architecture/00a-D-csv-samples--qwen.md` | только промпт | samples.csv — по 5 строк из каждого CSV | $0 |

**Чекпоинт 00A:** в проекте есть `hackathon/context/TECH-DESIGN.md`, описаны схемы всех CSV, зафиксированы design tokens.

---

## 🌊 ВОЛНА 01 — Foundation (10:00–10:30)

**Цель:** готовые `data_loader.py`, `metrics.py`, скелет `app.py`, `requirements.txt`.

**Модели:** kimi-k2.5 для основных модулей, qwen:free для скелета и конфига.

### Шаг 1 — Параллельно (4 сессии)

| # | Промпт | Модель | Передать | Выход | Цена |
|---|--------|--------|----------|-------|------|
| 6 | `wave-01-foundation/01A-data-loader--kimi.md` | kimi-k2.5 | TECH-DESIGN.md + csv-samples из 00a-D | `app/data_loader.py` | ~$0.03 |
| 7 | `wave-01-foundation/01B-metrics--kimi.md` | kimi-k2.5 | TECH-DESIGN.md + agents.md (секция Inputs) | `app/metrics.py` | ~$0.03 |
| 8 | `wave-01-foundation/01C-app-skeleton--qwen.md` | qwen:free | TECH-DESIGN.md | `app/app.py` (скелет с 3 вкладками) | $0 |
| 9 | `wave-01-foundation/01D-requirements--qwen.md` | qwen:free | только промпт | `requirements.txt` | $0 |

> ⚠️ Все 4 сессии запускаются одновременно. #6 и #7 используют разных агентов (kimi), #8 и #9 — qwen.

**Чекпоинт 01:** `python app/data_loader.py` — читает CSV без ошибок. `streamlit run app/app.py` — открываются 3 пустые вкладки.

---

## 🌊 ВОЛНА 02 — Python-модули (10:30–11:30)

**Цель:** 5 модулей для вкладок приложения.

**Модель:** все 5 промптов — `qwen/qwen3-coder:free` ($0).

**Передавать с каждым промптом:** `app/data_loader.py` + `app/metrics.py` (оба файла суммарно ~2K токенов).

| # | Промпт | Модуль | Назначение |
|---|--------|--------|-----------|
| 10 | `wave-02-components/02A-risk-table--qwen.md` | `risk_table.py` | Таблица рисков: top-20 строк, сортировка по `risk_score` / `severity` |
| 11 | `wave-02-components/02B-charts--qwen.md` | `charts.py` | Линейный график Altair: выбор оси X и Y среди числовых колонок |
| 12 | `wave-02-components/02C-kpi--qwen.md` | `kpi.py` | 4 KPI-метрики: CSV files, Rows loaded, Candidate events, MVP status |
| 13 | `wave-02-components/02D-actions--qwen.md` | `actions.py` | Форма действия: row_id, action_type, comment → сохранение в `output/actions.csv` |
| 14 | `wave-02-components/02E-data-overview--qwen.md` | `data_overview.py` | Список загруженных CSV (строки × колонки) + превью первых 100 строк |

**Как запускать:** открыть 5 вкладок Cherry Studio, запустить все 5 одновременно. Каждый промпт — независимый модуль.

**Чекпоинт 02:** `ls app/*.py | wc -l` → ≥7 файлов. Каждый модуль импортируется без ошибок.

---

## 🌊 ВОЛНА 03 — Вкладки (11:30–13:00)

**Цель:** собрать модули в три вкладки Streamlit.

**Модель:** kimi-k2.5 (~$0.03–0.04 каждый). Запускать **строго последовательно** — каждая следующая вкладка может ссылаться на предыдущую.

| # | Порядок | Промпт | Вкладка | Передать | Цена |
|---|---------|--------|---------|----------|------|
| 15 | **#1** | `wave-03-screens/03A-data-tab--kimi.md` | **Data tab** — обзор CSV + превью | `data_overview.py` + `data_loader.py` + TECH-DESIGN.md | ~$0.03 |
| 16 | **#2** | `wave-03-screens/03B-dashboard-tab--kimi.md` | **Dashboard tab** — KPI + график | `kpi.py` + `charts.py` + `metrics.py` + TECH-DESIGN.md | ~$0.04 |
| 17 | **#3** | `wave-03-screens/03C-details-tab--kimi.md` | **Details tab** — риски + форма | `risk_table.py` + `actions.py` + `data_loader.py` + TECH-DESIGN.md | ~$0.04 |

> ⚠️ Запускать строго по очереди. Дождаться завершения #15, потом #16, потом #17.

**Чекпоинт 03:** `streamlit run app/app.py` — все три вкладки отображаются, загружают данные, показывают контент.

---

## 🌊 ВОЛНА 04 — Интеграция (13:00–13:30)

**Цель:** собрать три вкладки в финальный `app.py`.

| # | Промпт | Модель | Передать | Цена |
|---|--------|--------|----------|------|
| 18 | `wave-04-routing/04-integration--kimi.md` | kimi-k2.5 | текущий `app.py` + код трёх вкладок (из волны 03) + TECH-DESIGN.md | ~$0.04 |

**Чекпоинт 04:** `streamlit run app/app.py` — приложение запускается, все три вкладки работают как единое целое. Переключение между вкладками без ошибок.

---

## 🌊 ВОЛНА 05 — Полировка (13:30–15:00)

**Цель:** чеклист приёмочного тестирования и демо-сценарий.

| # | Промпт | Модель | Передать | Выход | Цена |
|---|--------|--------|----------|-------|------|
| 19 | `wave-05-polish/05A-smoke-checklist--nemotron.md` | nemotron:free | только промпт | чеклист (текст) | $0 |
| 20 | `wave-05-polish/05B-demo-script--gpt-oss.md` | gpt-oss:free | agents.md (секция Demo script) | `hackathon/DEMO.md` | $0 |

**Запуск:** обе сессии параллельно, модели разные.

**Чекпоинт 05:** Flow 1 работает end-to-end: открыть Data → выбрать датасет → превью. Flow 2: Dashboard → все 4 KPI показывают значения → график строится по выбранным колонкам. Flow 3: Details → таблица рисков отсортирована → заполнить форму → действие записано в `output/actions.csv`.

---

## 🧩 Карта зависимостей

```
ВОЛНА 00 (контекст)
  │
  └─→ ВОЛНА 00A (архитектура) — нужен контекст из волны 00
        │
        └─→ ВОЛНА 01 (foundation) — нужны TECH-DESIGN + контракты из 00a
              │
              ├─ data_loader.py ────┐
              ├─ metrics.py ────────┤
              ├─ app.py skeleton ───┤
              └─ requirements.txt ──┘
              │
              └─→ ВОЛНА 02 (модули) — нужны data_loader + metrics из 01
                    │
                    ├─ risk_table.py ────┐
                    ├─ charts.py ────────┤
                    ├─ kpi.py ───────────┤ все параллельно
                    ├─ actions.py ───────┤
                    └─ data_overview.py ─┘
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
| 00 | 1 | nemotron:free | $0 |
| 00a | 4 | qwen:free ×4 | $0 |
| 01 | 4 | kimi-k2.5 ×2 + qwen:free ×2 | ~$0.06 |
| 02 | 5 | qwen:free ×5 | $0 |
| 03 | 3 | kimi-k2.5 ×3 | ~$0.11 |
| 04 | 1 | kimi-k2.5 ×1 | ~$0.04 |
| 05 | 2 | nemotron:free + gpt-oss:free | $0 |
| **Итого** | **20** | | **~$0.21** |

> Запас: $49.79 из $50. Можно заменить часть qwen:free на kimi-k2.5 для сложных модулей при необходимости.

---

## 🔧 Аварийные ситуации

| Ситуация | Действие |
|----------|----------|
| **429 (rate limit) на qwen:free** | Переключить на `deepseek/deepseek-v4-flash:free`. Если тоже 429 → `deepseek/deepseek-v4-flash` (~$0.04/M input) |
| **kimi-k2.5 ошибка** | Подождать 30 сек, повторить. 3-я ошибка подряд → заменить на `Devstral` (по agents.md) |
| **Все free-модели упали** | Все оставшиеся промпты на `deepseek/deepseek-v4-flash` (~$0.10 за всё) |
| **Python-ошибка после промпта** | Скопировать ТОЛЬКО файл с ошибкой + traceback → qwen:free «Исправь ошибку» |
| **Агент создал не тот файл** | Перезапустить тот же промпт с уточнением «Путь к файлу: [правильный путь]» |
| **Streamlit не запускается** | Проверить `requirements.txt` → `pip install -r requirements.txt` → повторить |
| **Данные не загружаются** | Проверить пути в `data_loader.py` — пути относительны к корню проекта |
| **Агент пишет слишком длинный код** | Остановить, уточнить «Только [имя модуля], не больше 80 строк» |

---

## ✅ Шпаргалка: что передавать с каждым типом промпта

| Тип промпта | Всегда передавать | Никогда не передавать |
|---|---|---|
| Контекст (00) | только промпт | CSV-файлы, agents.md (агент сам прочитает) |
| Архитектура (00a) | agents.md (секции Goal, Inputs, Non-goals) | полный agents.md |
| Foundation — kimi (01A, 01B) | TECH-DESIGN.md + csv-samples | полный текст agents.md |
| Foundation — qwen (01C, 01D) | TECH-DESIGN.md | — |
| Модули (02) | `data_loader.py` + `metrics.py` | полный agents.md |
| Вкладки — kimi (03) | модули волны 02 + TECH-DESIGN.md | — |
| Интеграция (04) | текущий `app.py` + код всех трёх вкладок | — |
| Полировка (05) | только промпт | — |

---

## 📂 Структура выходных файлов (что должно получиться)

```
app/
  __init__.py                    ← уже есть
  data_loader.py                 ← 01A
  metrics.py                     ← 01B
  app.py                         ← 01C → 04 (финальная сборка)
  risk_table.py                  ← 02A
  charts.py                      ← 02B
  kpi.py                         ← 02C
  actions.py                     ← 02D
  data_overview.py               ← 02E
output/
  actions.csv                    ← 02D (форма в Details tab)
requirements.txt                 ← 01D
hackathon/context/
  TECH-DESIGN.md                 ← 00a-A
  DATA-CONTRACT.md               ← 00a-B
  DESIGN-TOKENS.md               ← 00a-C
  csv-samples.csv                ← 00a-D
hackathon/
  DEMO.md                        ← 05B
  SMOKE-CHECKLIST.md             ← 05A
```

---

## 🤖 Рекомендации по моделям (из agents.md)

| Модель | Применение | Цена |
|--------|-----------|------|
| **Kimi K2.5** | Основной кодинг: data_loader, metrics, вкладки, интеграция | ~$0.03–0.04/запрос |
| **Qwen** | Анализ, архитектура, простые модули, декомпозиция | free |
| **Nemotron** | Чтение контекста, чеклисты | free |
| **GPT-OSS** | Драфты, демо-сценарий, простые тексты | free |
| **Devstral** | Резервная модель для кодинга, если Kimi не справляется | ~$0.01–0.02/запрос |

> Не использовать Gemini. Не запускать несколько code-агентов на одном team API key одновременно без явного одобрения.

---

Держи этот файл открытым весь день. Каждый час сверяйся с чекпоинтами.
