# SKAI Hackathon MVP — План выполнения в Kilo

Ветка: `main`. Все задачи в одном окне VS Code + Kilo.

## Статус

| Компонент | Файл | Статус |
|-----------|------|--------|
| Константы | `app/constants.py` | Готово |
| Загрузка CSV | `app/data_loader.py` | Готово |
| KPI-метрики | `app/metrics.py` | Готово |
| Чарты Altair | `app/charts.py` | Готово |
| Форма действий | `app/actions.py` | Готово |
| Таблица рисков | `app/risk_table.py` | Готово |
| Обзор данных | `app/data_overview.py` | **Нужно создать** |
| Вкладка Данные | `app/app.py` → render_data_tab | **Заглушка** |
| Вкладка Dashboard | `app/app.py` → render_dashboard_tab | **Заглушка** |
| Вкладка Детали | `app/app.py` → render_details_tab | **Заглушка** |

---

## Порядок выполнения

### Шаг 1. Создать `app/data_overview.py`

**Задача:** создать файл с тремя функциями.

Промпт для Kilo:

```
Прочитай файл prompts/hackathon/wave-02-components/02C-data-overview--qwen3.md
и создай app/data_overview.py следуя инструкции внутри.
После создания проверь: python -c "from app.data_overview import build_dataset_overview, pick_dataset, render_dataset_preview"
```

Функции:
- `build_dataset_overview(datasets)` — таблица: имя файла, строк, колонок
- `pick_dataset(datasets)` — selectbox в сайдбаре, возвращает (name, df)
- `render_dataset_preview(df, name)` — head(100) через st.dataframe

### Шаг 2. Наполнить вкладку «Данные» (03A)

**Задача:** заменить заглушку `render_data_tab` на обзор CSV + превью.

Промпт для Kilo:

```
Прочитай prompts/hackathon/wave-03-screens/03A-data-tab--qwen3.md и app/app.py.
Замени заглушку render_data_tab на реальную реализацию:
- Добавь импорт from data_overview import build_dataset_overview, pick_dataset, render_dataset_preview
- render_data_tab показывает обзорную таблицу всех CSV и превью выбранного датасета
- Остальной код app.py не меняй.
```

### Шаг 3. Наполнить вкладку «Dashboard» (03B)

**Задача:** заменить заглушку `render_dashboard_tab` на KPI + чарты.

Промпт для Kilo:

```
Прочитай prompts/hackathon/wave-03-screens/03B-dashboard-tab--qwen3.md, app/app.py, app/metrics.py, app/charts.py.
Замени заглушку render_dashboard_tab на реальную реализацию:
- Добавь импорты pick_dataset, build_dashboard_metrics, build_scatter_chart, build_speed_chart, build_track_map
- 4 KPI-метрики в ряд
- Выбор датасета в сайдбаре
- Scatter-чарт по двум числовым колонкам
- График скорости (если есть track_points)
- Карта трека (если есть latitude/longitude)
- НЕ создавай data_overview.py — он уже есть с шага 1 (пропусти ШАГ 1 из промпта 03B)
- Остальной код app.py не меняй.
```

### Шаг 4. Наполнить вкладку «Детали» (03C)

**Задача:** заменить заглушку `render_details_tab` на таблицу рисков + форму действий.

Промпт для Kilo:

```
Прочитай prompts/hackathon/wave-03-screens/03C-details-tab--qwen3.md, app/app.py, app/risk_table.py, app/actions.py, app/constants.py.
Замени заглушку render_details_tab на реальную реализацию:
- Добавь импорты OUTPUT_DIR_NAME, render_risk_table, render_action_form
- Добавь OUTPUT_DIR = PROJECT_ROOT / OUTPUT_DIR_NAME
- render_details_tab показывает таблицу рисков + форму действий с сохранением в output/actions.csv
- Остальной код app.py не меняй.
```

### Шаг 5. Проверка

```bash
cd /Users/dimausac/projects/skai_7
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/app.py
```

Чекпоинты:
- [ ] Вкладка «Данные»: обзорная таблица CSV + превью выбранного датасета
- [ ] Вкладка «Dashboard»: 4 KPI + scatter-чарт + карта трека + график скорости
- [ ] Вкладка «Детали»: таблица рисков + форма действий → сохранение в `output/actions.csv`
- [ ] Все три вкладки работают без ошибок

### Шаг 6 (опционально). Полировка (wave 05)

Если останется время — smoke-чеклист и demo-скрипт:
- `prompts/hackathon/wave-05-polish/05C-smoke-checklist--nemotron.md`
- `prompts/hackathon/wave-05-polish/05D-demo-script--gpt-oss.md`

---

## Зависимости

```
02C (data_overview.py)
 │
 ├─→ 03A (Data tab)    ──┐
 ├─→ 03B (Dashboard)   ──┤ все три можно параллельно
 └─→ 03C (Details)     ──┘ НО правят один app.py → последовательно
```

Шаги 2-4 правят один файл `app/app.py` в разных функциях — **делать последовательно** во избежание конфликтов. Суммарное время: ~15 минут.

---

## Запуск

### Через Makefile (рекомендуется)

```bash
cd /Users/dimausac/projects/skai_7
make help        # список всех команд
make install     # установить зависимости (один раз)
make run         # запуск production-режим на http://localhost:8501
make dev         # запуск dev-режим с auto-reload
make clean       # очистить кеш и __pycache__
```

### Вручную

```bash
cd /Users/dimausac/projects/skai_7
source .venv/bin/activate
streamlit run run.py
```

## Структура проекта

```
.
├── Makefile               ← команды запуска
├── agents.md              ← задача хакатона
├── requirements.txt       ← streamlit, pandas, numpy, altair
├── README.md              ← этот файл
├── run.py                 ← точка входа для Streamlit
├── main.py                ← точка входа для прямого запуска
├── backend/
│   ├── app.py             ← основное приложение Streamlit (5 вкладок)
│   ├── constants.py       ← design tokens, метки, конфиг
│   ├── data_loader.py     ← загрузка CSV + save_action
│   ├── metrics.py         ← KPI-метрики + build_risk_table
│   ├── charts.py          ← Altair: scatter, speed, track map
│   ├── actions.py         ← форма действий диспетчера
│   ├── risk_table.py      ← расширенная таблица рисков
│   ├── data_overview.py   ← обзор датасетов + превью
│   └── screens/           ← экраны/вкладки приложения
│       ├── incident.py        ← вкладка «Детали инцидента»
│       ├── monitor.py         ← вкладка «Живой мониторинг»
│       ├── report.py          ← вкладка «Интерактивный отчёт»
│       └── incident_card.py   ← вкладка «Карточка инцидента»
├── data/                  ← CSV-файлы (телеметрия + видео-алармы)
├── sample_data/           ← демо-данные (fallback)
├── output/                ← actions.csv, отчёты (автосоздаётся)
├── datasets/media/        ← MP4-файлы
└── prompts/               ← промпты хакатона
```
