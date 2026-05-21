# TECH-DESIGN — SKAI Unified Incident Window

## 1. Дерево модулей Python

```
app/
├── __init__.py
├── app.py              # Точка входа: сайдбар + 3 вкладки
├── constants.py        # Цвета, метки алармов, пороги риска, типы действий
├── data_loader.py      # Загрузка CSV и сохранение actions
├── metrics.py          # KPI-метрики для дашборда
├── charts.py           # Altair-графики (scatter, line, bar)
├── risk_table.py       # Таблица рисков с join-логикой
└── tabs.py             # Рендеринг трёх вкладок Streamlit
```

### `app/constants.py`

**Назначение**: константы приложения — пороги риска, метки типов алармов, цветовая схема, доступные типы действий.

**Экспортируемые объекты**:

```python
# Цветовая схема
COLOR_PALETTE: dict[str, str]           # {"primary": "#1f77b4", "danger": "#d62728", ...}

# Пороги риска
RISK_SPEED_THRESHOLD: int = 40           # скорость (км/ч), выше которой аларм считается высокорисковым
RISK_VIDEO_COUNT_MIN: int = 1            # минимальное кол-во видео для снижения риска «нет доказательств»

# Метки типов алармов (перевод на русский)
ALARM_TYPE_LABELS: dict[str, str]       # {"Distraction": "Отвлечение", "SharpAcceleration": "Резкое ускорение", ...}

# Типы действий
ACTION_TYPES: list[str]                 # ["mark_reviewed", "create_task", "export_report"]
ACTION_TYPE_LABELS: dict[str, str]      # {"mark_reviewed": "Пометить как проверенное", ...}

# Датасеты
DATASET_NAMES: list[str]                # ["selected_video_alarms", "video_files", "vehicles", "track_summary", "track_points", "max_speed_points"]
```

### `app/data_loader.py`

**Назначение**: загрузка всех CSV в `pd.DataFrame`, кеширование через `@st.cache_data`, сохранение действий в `output/actions.csv`.

**Импорты**: `pandas as pd`, `streamlit as st`, `pathlib.Path`, `datetime`.

**Экспортируемые функции**:

```python
@st.cache_data
def load_csv_files(data_dir: str = "data") -> dict[str, pd.DataFrame]:
    """
    Читает все CSV из data/ и возвращает словарь {имя_файла_без_расширения: DataFrame}.
    Ключи:
      - "selected_video_alarms"  (55 строк, 17 колонок)
      - "video_files"            (95 строк, 25 колонок)
      - "vehicles"               (22 строки, 12 колонок)
      - "track_summary"          (55 строк, 19 колонок)
      - "track_points"           (6636 строк, 16 колонок)
      - "max_speed_points"       (81 строка, 10 колонок)
    """

def save_action(
    row_id: str,
    action_type: str,
    comment: str = "",
    output_dir: str = "output"
) -> None:
    """
    Добавляет одну строку в output/actions.csv.
    Если файл не существует — создаёт с заголовками.
    Колонки: timestamp, row_id, action_type, comment.
    """
```

### `app/metrics.py`

**Назначение**: вычисление KPI для вкладки Dashboard из реальных DataFrame.

**Импорты**: `pandas as pd`.

**Экспортируемые функции**:

```python
def build_dashboard_metrics(datasets: dict[str, pd.DataFrame]) -> dict[str, int | float]:
    """
    Возвращает словарь с метриками:
      - "total_alarms"       : len(selected_video_alarms)                       → 55
      - "total_vehicles"     : len(vehicles)                                    → 22
      - "total_video_files"  : len(video_files)                                 → 95
      - "avg_speed"          : selected_video_alarms["Speed"].mean()            → float
      - "alarms_with_video"  : selected_video_alarms["VideoCount"] > 0 → count
      - "total_track_points" : len(track_points)                                → 6636
    """
```

### `app/charts.py`

**Назначение**: построение Altair-графиков по выбору колонок пользователем.

**Импорты**: `altair as alt`, `pandas as pd`.

**Экспортируемые функции**:

```python
def build_altair_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    chart_type: str = "scatter",   # "scatter" | "line" | "bar"
    tooltip_cols: list[str] | None = None,
    width: int = 700,
    height: int = 400
) -> alt.Chart:
    """
    Строит Altair-график по двум числовым колонкам.
    - scatter: mark_circle
    - line:    mark_line
    - bar:     mark_bar
    tooltip_cols — список колонок для всплывающей подсказки.
    """

def build_alarm_type_bar_chart(df: pd.DataFrame, width: int = 700, height: int = 400) -> alt.Chart:
    """
    Строит bar chart распределения типов алармов (столбец "Type").
    df — selected_video_alarms.
    X = Type (переведённые метки), Y = count().
    """
```

### `app/risk_table.py`

**Назначение**: формирование таблицы рисков — top-N алармов с join-логикой и расчётом `risk_score`.

**Импорты**: `pandas as pd`, `app.constants`.

**Экспортируемые функции**:

```python
def build_risk_table(
    datasets: dict[str, pd.DataFrame],
    top_n: int = 20,
    sort_by: str = "risk_score"
) -> pd.DataFrame:
    """
    Соединяет alarms + video_files + track_summary + vehicles,
    вычисляет risk_score и возвращает top-N строк.

    Колонки результата:
      - "AlarmId"              — из selected_video_alarms
      - "UnitStateNumber"     — госномер (из alarms или vehicles)
      - "Type"                 — тип аларма
      - "Speed"                — скорость (из alarms)
      - "Begin"                — время начала (из alarms)
      - "Address"              — адрес (из alarms)
      - "VideoCount"           — количество связанных видео
      - "MaxSpeedKmh"          — макс. скорость из max_speed_points
      - "TotalMileageKm"       — пробег из track_summary
      - "AlarmCount"           — общее число алармов по машине (из vehicles)
      - "risk_score"           — составной балл (Speed × вес + VideoCount × вес + ...)

    Join-логика:
      1. alarms LEFT JOIN video_files ON AlarmId = alarm_id → считаем VideoCount
      2. alarms LEFT JOIN max_speed_points ON AlarmId = alarm_id → MaxSpeedKmh
      3. alarms LEFT JOIN track_summary ON AlarmId = alarm_id → TotalMileageKm
      4. alarms LEFT JOIN vehicles ON UnitStateNumber = unit_state_number → AlarmCount
    """

def get_alarm_details(
    alarm_id: str,
    datasets: dict[str, pd.DataFrame]
) -> dict[str, pd.DataFrame]:
    """
    Возвращает детализацию по одному аларму:
      - "alarm"        : строка из selected_video_alarms (1 row)
      - "videos"       : связанные строки из video_files (N rows)
      - "track_points" : связанные точки из track_points (N rows)
      - "max_speeds"   : связанные макс. скорости из max_speed_points (N rows)
      - "vehicle"      : связанная строка из vehicles (1 row)
    """
```

### `app/tabs.py`

**Назначение**: рендеринг трёх вкладок Streamlit. Каждая функция принимает словарь датасетов и рендерит UI.

**Импорты**: `streamlit as st`, `pandas as pd`, `app.constants`, `app.metrics`, `app.charts`, `app.risk_table`, `app.data_loader`.

**Экспортируемые функции**:

```python
def render_data_tab(datasets: dict[str, pd.DataFrame]) -> None:
    """
    Вкладка "Данные".
    - Сводка по каждому датасету: имя, строки, колонки.
    - selectbox с выбором датасета (из DATASET_NAMES).
    - st.dataframe(head(100)) выбранного датасета.
    """

def render_dashboard_tab(datasets: dict[str, pd.DataFrame]) -> None:
    """
    Вкладка "Дашборд".
    - 4 стримлит-метрики (st.metric) из build_dashboard_metrics().
    - Два selectbox для выбора X/Y колонок среди numeric колонок выбранного датасета.
    - st.altair_chart с build_altair_chart().
    - st.altair_chart с build_alarm_type_bar_chart().
    """

def render_details_tab(datasets: dict[str, pd.DataFrame]) -> None:
    """
    Вкладка "Разбор инцидента".
    - build_risk_table() → st.dataframe с top-20 алармов.
    - При выборе строки (st.dataframe on_select или radio/selectbox):
      а) детали аларма через get_alarm_details()
      б) таблица связанных видео (media_relative_path, channel, duration_seconds)
      в) таблица трек-точек (первые 50)
      г) мини-чарт скорости по track_points
    - Форма действий: row_id (авто), action_type (selectbox), comment (text_input) → кнопка → save_action()
    """
```

### `app/app.py`

**Назначение**: точка входа Streamlit. Загружает данные, рендерит сайдбар и переключает вкладки.

**Импорты**: `streamlit as st`, `app.data_loader`, `app.tabs`.

**Логика**:

```python
def main():
    st.set_page_config(page_title="SKAI Unified Incident Window", layout="wide")
    st.sidebar.title("SKAI — Единое окно")

    datasets = data_loader.load_csv_files()

    tab1, tab2, tab3 = st.tabs(["📊 Данные", "📈 Дашборд", "🔍 Разбор инцидента"])
    with tab1:
        tabs.render_data_tab(datasets)
    with tab2:
        tabs.render_dashboard_tab(datasets)
    with tab3:
        tabs.render_details_tab(datasets)
```

---

## 2. Поток данных (Data Flow)

```
┌──────────────────────────────────────────────────────────────────────┐
│                        data/ (файловая система)                       │
│                                                                       │
│  selected_video_alarms.csv   video_files.csv   vehicles.csv           │
│  track_summary.csv           track_points.csv  max_speed_points.csv   │
└───────────────┬───────────────┬───────────────┬───────────────────────┘
                │               │               │
                └───────────────┼───────────────┘
                                │
                    ┌───────────▼───────────┐
                    │  data_loader.py       │
                    │  load_csv_files()     │
                    │  @st.cache_data       │
                    └───────────┬───────────┘
                                │
                  dict[str, pd.DataFrame]
                  ┌─────────────┼─────────────┐
                  │             │             │
          ┌───────▼──┐  ┌──────▼──────┐  ┌───▼────────────┐
          │ Tab 1    │  │ Tab 2       │  │ Tab 3          │
          │ "Данные" │  │ "Дашборд"   │  │ "Разбор"       │
          │           │  │             │  │                 │
          │ data_     │  │ metrics.py  │  │ risk_table.py   │
          │ preview   │  │ charts.py   │  │ data_loader.py  │
          └───────────┘  └─────────────┘  └───────┬─────────┘
                                                  │
                                    save_action() │ st.button
                                                  │
                                        ┌─────────▼──────────┐
                                        │  output/actions.csv │
                                        │                     │
                                        │  timestamp, row_id, │
                                        │  action_type,       │
                                        │  comment            │
                                        └────────────────────┘
```

Поток неизменяемый: данные загружаются один раз при старте, кешируются через `@st.cache_data`, все вкладки читают из одного и того же словаря `datasets`. Единственная запись — `save_action()` в `output/actions.csv`.

---

## 3. Спецификация вкладок

### Tab 1 — «📊 Данные»

| Элемент | Описание |
|---------|----------|
| Сводка | Таблица: имя файла → (строк, колонок). Источник: `datasets.keys()` |
| sidebar selectbox | Выбор датасета из `DATASET_NAMES` → сохраняется в `st.session_state["selected_dataset"]` |
| Превью | `st.dataframe(datasets[selected].head(100))`, `use_container_width=True` |
| Колонки | `st.write(f"Колонки: {', '.join(df.columns)}")` |

### Tab 2 — «📈 Дашборд»

| Элемент | Описание |
|---------|----------|
| KPI-карточки | 4 колонки `st.columns(4)` → `st.metric` с вызовом `build_dashboard_metrics()` |
| KPI 1 | `Всего алармов` = `len(selected_video_alarms)` |
| KPI 2 | `Всего машин` = `len(vehicles)` |
| KPI 3 | `Всего видеофайлов` = `len(video_files)` |
| KPI 4 | `Средняя скорость` = `round(Speed.mean(), 1) км/ч` |
| Выбор датасета для чарта | `st.selectbox` в sidebar → `selected_dataset` |
| Выбор осей | Два `st.selectbox`: X и Y из `df.select_dtypes(include="number").columns` |
| Тип графика | `st.radio`: scatter / line / bar |
| Первый график | `st.altair_chart(build_altair_chart(...))` |
| Второй график | `st.altair_chart(build_alarm_type_bar_chart(...))` — фиксированный bar chart типов алармов |

### Tab 3 — «🔍 Разбор инцидента»

| Элемент | Описание |
|---------|----------|
| Риск-таблица | `build_risk_table(datasets, top_n=20)` → `st.dataframe` |
| Колонки таблицы | AlarmId, UnitStateNumber, Type, Speed, Begin, Address, VideoCount, MaxSpeedKmh, TotalMileageKm, AlarmCount, risk_score |
| Выбор аларма | `st.selectbox` с AlarmId из риск-таблицы → сохраняется в `st.session_state["selected_alarm_id"]` |
| Блок деталей | `get_alarm_details(selected_alarm_id, datasets)` → 4 подблока: |
| — Аларм | `st.json(alarm.to_dict())` или карточка с ключевыми полями |
| — Видео | `st.dataframe` колонок: `channel`, `media_relative_path`, `duration_seconds`, `video_width`, `video_height`, `video_codec` |
| — Трек | `st.dataframe` первых 50 трек-точек: `timestamp_utc`, `latitude`, `longitude`, `speed_kmh` |
| — График скорости | `st.altair_chart`: line chart `speed_kmh` vs `timestamp_utc` из track_points |
| Форма действий | `st.form`: `action_type` (selectbox из `ACTION_TYPES`), `comment` (text_input), `st.form_submit_button("Сохранить")` → `save_action()` |
| Обратная связь | `st.success("Действие сохранено в output/actions.csv")` |

---

## 4. Управление состоянием

Streamlit-состояние хранится только в `st.session_state`:

| Ключ | Тип | Назначение |
|------|-----|------------|
| `datasets` | `dict[str, pd.DataFrame]` | Результат `load_csv_files()`. Инициализируется при первом обращении. |
| `selected_dataset` | `str` | Имя выбранного датасета в Tab 1 / Tab 2. По умолчанию `"selected_video_alarms"`. |
| `selected_alarm_id` | `str \| None` | Выбранный AlarmId в Tab 3. |
| `chart_x` | `str` | Выбранная колонка для оси X. |
| `chart_y` | `str` | Выбранная колонка для оси Y. |
| `chart_type` | `str` | Тип графика: `"scatter"`, `"line"`, `"bar"`. |

**Правила**:
- `datasets` получается вызовом `load_csv_files()` один раз при старте `app.py`.
- `load_csv_files()` обёрнута в `@st.cache_data` — Streamlit кеширует результат, повторные вызовы не перечитывают CSV.
- Все остальные ключи инициализируются через `if "key" not in st.session_state: st.session_state["key"] = default`.
- Никакого `st.cache_resource` не используется — все данные помещаются в память без проблем (суммарно < 5MB).

---

## 5. Стратегия соединения (Join Strategy)

Центральная сущность — **alarm** (`selected_video_alarms`). Все связи идут через неё.

```
selected_video_alarms (55)
│
│  AlarmId ─────────── video_files.alarm_id          (1 : N, 55 → 95)
│  AlarmId ─────────── track_summary.alarm_id        (1 : 1, 55 → 55)
│  AlarmId ─────────── track_points.alarm_id         (1 : N, 55 → 6636)
│  AlarmId ─────────── max_speed_points.alarm_id     (1 : N, 55 → 81)
│
│  UnitStateNumber ─── vehicles.unit_state_number    (N : 1, 55 → 22)
```

**Реализация** (в `risk_table.py`):

```python
# Шаг 1: считаем VideoCount через groupby
video_counts = video_files.groupby("alarm_id").size().reset_index(name="VideoCount")

# Шаг 2: LEFT JOIN alarms ← video_counts
alarms = alarms.merge(video_counts, left_on="AlarmId", right_on="alarm_id", how="left")

# Шаг 3: LEFT JOIN alarms ← max_speed (аггрегируем max speed)
max_speed_agg = max_speed_points.groupby("alarm_id")["speed_kmh"].max().reset_index(name="MaxSpeedKmh")
alarms = alarms.merge(max_speed_agg, left_on="AlarmId", right_on="alarm_id", how="left")

# Шаг 4: LEFT JOIN alarms ← track_summary (mileage)
alarms = alarms.merge(track_summary[["alarm_id", "total_mileage_km"]], left_on="AlarmId", right_on="alarm_id", how="left")

# Шаг 5: LEFT JOIN alarms ← vehicles
alarms = alarms.merge(vehicles[["unit_state_number", "alarm_count"]], left_on="UnitStateNumber", right_on="unit_state_number", how="left")

# Шаг 6: вычисляем risk_score
alarms["risk_score"] = (
    alarms["Speed"].fillna(0) * 0.4 +
    alarms["VideoCount"].fillna(0) * -0.3 +     # обратная зависимость: больше видео = меньше риск неопределённости
    alarms["MaxSpeedKmh"].fillna(0) * 0.2 +
    alarms["AlarmCount"].fillna(0) * 0.1
)
```

Все JOIN — **LEFT**, чтобы не терять алармы без видео или без трека.

---

## 6. Реальные CSV-колонки

### `selected_video_alarms.csv` — 55 строк × 17 колонок

| Колонка | Тип | Описание |
|---------|-----|----------|
| `dataset_vehicle_code` | str | Код ТС в датасете (напр. `T780RN198`) |
| `AlarmId` | str (UUID) | Уникальный идентификатор аларма |
| `TelemetryId` | str (UUID) | ID телеметрической сессии |
| `TerminalId` | str (UUID) | ID терминала |
| `UnitId` | str (UUID) | ID юнита (ТС) |
| `UnitName` | str | Имя юнита (напр. `Т 780 РН 198  15133`) |
| `UnitStateNumber` | str | Госномер (напр. `Т780РН198`) |
| `Begin` | str (ISO 8601) | Время начала аларма |
| `End` | str (ISO 8601) | Время окончания аларма |
| `Type` | str | Тип аларма (Distraction, SharpAcceleration, Drowsiness, ...) |
| `Speed` | float | Скорость в момент аларма, км/ч |
| `Address` | str | Адрес (часто пустой) |
| `VideoCount` | int | Количество связанных видеофайлов |
| `VideoSizeBytes` | int | Суммарный размер видео, байт |
| `CameraIds` | str (JSON-массив) | ID камер (напр. `[1, 2]`) |
| `RequestedCameraIds` | str (JSON-массив) | Запрошенные ID камер |
| `Latitude` | float | Широта (часто пустая) |
| `Longitude` | float | Долгота (часто пустая) |

### `video_files.csv` — 95 строк × 25 колонок

| Колонка | Тип | Описание |
|---------|-----|----------|
| `dataset_vehicle_code` | str | Код ТС |
| `alarm_id` | str (UUID) | ID аларма (внешний ключ) |
| `telemetry_id` | str (UUID) | ID телеметрии |
| `video_file_id` | str (UUID) | Уникальный ID видеофайла |
| `channel` | int | Номер канала камеры (1, 2, 3) |
| `created_at_utc` | str (ISO 8601) | Время создания записи |
| `event_type` | str | Тип события (Yawning, Drowsiness, ...) |
| `event_begin_utc` | str (ISO 8601) | Начало события |
| `event_end_utc` | str (ISO 8601) | Конец события |
| `unit_id` | str (UUID) | ID юнита |
| `unit_name` | str | Имя юнита |
| `unit_state_number` | str | Госномер |
| `expected_size_from_alarm_bytes` | int | Ожидаемый размер, байт |
| `download_endpoint_attempted` | str | URL попытки скачивания |
| `local_path` | str | Локальный путь при скачивании |
| `download_status` | str | Статус скачивания (`downloaded`) |
| `size_bytes` | int | Фактический размер, байт |
| `download_http_status` | int | HTTP-статус скачивания |
| `content_type` | str | MIME-тип (`video/mp4`) |
| `server_filename` | str | Имя файла на сервере |
| `media_filename` | str | Локальное имя медиафайла |
| `media_relative_path` | str | Относительный путь к MP4 |
| `duration_seconds` | float | Длительность, сек |
| `video_width` | int | Ширина видео, px |
| `video_height` | int | Высота видео, px |
| `video_codec` | str | Кодек (`h264`) |

### `vehicles.csv` — 22 строки × 12 колонок

| Колонка | Тип | Описание |
|---------|-----|----------|
| `dataset_vehicle_code` | str | Код ТС |
| `unit_id` | str (UUID) | ID юнита |
| `unit_name` | str | Имя юнита |
| `unit_state_number` | str | Госномер |
| `alarm_count` | int | Общее количество алармов |
| `alarm_types` | str | Типы алармов через `\|` |
| `video_metadata_count` | int | Количество записей о видео |
| `downloaded_video_count` | int | Количество скачанных видео |
| `track_window_count` | int | Количество трек-окон |
| `track_point_count` | int | Количество трек-точек |
| `total_track_mileage_km` | float | Общий пробег, км |
| `downloaded_video_bytes` | int | Объём скачанных видео, байт |
| `downloaded_video_duration_seconds` | float | Длительность скачанных видео, сек |

### `track_summary.csv` — 55 строк × 19 колонок

| Колонка | Тип | Описание |
|---------|-----|----------|
| `alarm_id` | str (UUID) | ID аларма (внешний ключ) |
| `dataset_vehicle_code` | str | Код ТС |
| `unit_id` | str (UUID) | ID юнита |
| `unit_name` | str | Имя юнита |
| `unit_state_number` | str | Госномер |
| `event_type` | str | Тип события |
| `event_begin_utc` | str (ISO 8601) | Начало события |
| `event_end_utc` | str (ISO 8601) | Конец события |
| `total_parking_duration` | str (HH:MM:SS) | Длительность стоянки |
| `total_movement_duration` | str (HH:MM:SS) | Длительность движения |
| `total_mileage_km` | float | Общий пробег, км |
| `movement_mileage_km` | float | Пробег в движении, км |
| `movement_distance_navigation_km` | float | Дистанция по навигации, км |
| `break_distance_navigation_km` | float | Дистанция перерывов, км |
| `distance_odometer_km` | float | Пробег по одометру, км |
| `track_period_count` | int | Количество трек-периодов |
| `track_point_count` | int | Количество трек-точек |
| `max_speed_point_count` | int | Количество точек макс. скорости |
| `raw_track_path` | str | Путь к raw JSON трека |

### `track_points.csv` — 6636 строк × 16 колонок

| Колонка | Тип | Описание |
|---------|-----|----------|
| `alarm_id` | str (UUID) | ID аларма (внешний ключ) |
| `dataset_vehicle_code` | str | Код ТС |
| `unit_id` | str (UUID) | ID юнита |
| `unit_state_number` | str | Госномер |
| `event_type` | str | Тип события |
| `event_begin_utc` | str (ISO 8601) | Начало события |
| `period_index` | int | Индекс периода |
| `period_type` | int | Тип периода (2=движение, 3=стоянка) |
| `point_index` | int | Индекс точки внутри периода |
| `timestamp_utc` | str (ISO 8601) | Время точки |
| `latitude` | float | Широта |
| `longitude` | float | Долгота |
| `speed_kmh` | float | Скорость, км/ч |
| `angle` | float | Угол направления |
| `course` | float | Курс |
| `ew` | bool | Признак «восток-запад»? (True/False) |

### `max_speed_points.csv` — 81 строка × 10 колонок

| Колонка | Тип | Описание |
|---------|-----|----------|
| `alarm_id` | str (UUID) | ID аларма (внешний ключ) |
| `dataset_vehicle_code` | str | Код ТС |
| `event_type` | str | Тип события |
| `point_index` | int | Индекс точки |
| `timestamp_utc` | str (ISO 8601) | Время точки |
| `latitude` | float | Широта |
| `longitude` | float | Долгота |
| `speed_kmh` | float | Максимальная скорость, км/ч |
| `angle` | float | Угол направления |
| `course` | float | Курс |
| `ew` | bool | Признак «восток-запад»? |

### `track_periods.csv` — 113 строк × 7 колонок

| Колонка | Тип | Описание |
|---------|-----|----------|
| `alarm_id` | str (UUID) | ID аларма (внешний ключ) |
| `dataset_vehicle_code` | str | Код ТС |
| `unit_id` | str (UUID) | ID юнита |
| `event_type` | str | Тип события |
| `period_index` | int | Индекс периода |
| `period_type` | int | Тип периода (2/3) |
| `period_duration` | str (HH:MM:SS) | Длительность периода |
| `track_point_count` | int | Количество точек в периоде |
