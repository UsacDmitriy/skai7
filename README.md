# SKAI

Ветка: `main`.

> **Статус:** UI на Streamlit удалён. Сохранён дата-слой и бизнес-логика (загрузка CSV,
> метрики, чарты, таблица рисков, NL-парсер). Новый бэкенд разрабатывается отдельно
> (см. [prompts/waves/wave-06-sqlite-backend/](prompts/waves/wave-06-sqlite-backend/)).

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
├── data/                  ← CSV-файлы (телеметрия + видео-алармы)
├── sample_data/           ← демо-данные (fallback)
├── output/                ← actions.csv, отчёты (автосоздаётся)
├── datasets/media/        ← MP4-файлы
└── prompts/               ← промпты разработки
```
