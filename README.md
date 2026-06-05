# SKAI

Ветка: `main`.

> **Статус:** UI на Streamlit удалён. Сохранён дата-слой и бизнес-логика (загрузка CSV,
> метрики, чарты, таблица рисков, NL-парсер) — будет портирован в новый стек.
> Действующий план разработки (DuckDB + FastAPI + React) — в
> [prompts/v2-fullstack/](prompts/v2-fullstack/) (источник истины — `00-CONTRACT.md`).

## Сохранённые модули

| Модуль | Файл | Назначение |
|--------|------|------------|
| Константы | [backend/constants.py](backend/constants.py) | метки, конфиг, design tokens |
| Загрузка CSV | [backend/data_loader.py](backend/data_loader.py) | чтение CSV + `save_action` |
| Модели | [backend/models.py](backend/models.py) | dataclass-модели данных |
| KPI-метрики | [backend/metrics.py](backend/metrics.py) | расчёт метрик по алармам |
| Чарты | [backend/charts.py](backend/charts.py) | Altair: scatter, speed, track map |
| Таблица рисков | [backend/risk_table.py](backend/risk_table.py) | расширенная таблица рисков |
| NL-парсер | [backend/nl_parser.py](backend/nl_parser.py) | разбор запросов на естественном языке |
| Пресеты аналитики | [backend/analytics_presets.py](backend/analytics_presets.py) | готовые срезы аналитики |

## Зависимости

```
pandas, numpy, altair
```

Установка:

```bash
cd /Users/dimausac/projects/skai_7
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Переменные окружения

Скопируй шаблон и при необходимости заполни значения (Groq-ключ, флаги фронта):

```bash
cp .env.example .env
```

Состав переменных и значения по умолчанию — в [.env.example](.env.example).

## Структура проекта

```
.
├── agents.md              ← описание задачи
├── requirements.txt       ← pandas, numpy, altair
├── README.md              ← этот файл
├── backend/               ← дата-слой и бизнес-логика
│   ├── constants.py
│   ├── data_loader.py
│   ├── models.py
│   ├── metrics.py
│   ├── charts.py
│   ├── risk_table.py
│   ├── nl_parser.py
│   └── analytics_presets.py
├── data/                  ← alarm_types.json + mock-эталоны структуры; БД skai.duckdb (gen)
├── datasets/ready/        ← канонические CSV (источник истины: video_events, fuel, sensors…)
├── sample_data/           ← демо-данные (fallback)
├── output/                ← actions.csv, отчёты (автосоздаётся)
├── datasets/media/        ← MP4-файлы
└── prompts/               ← промпты разработки
```
