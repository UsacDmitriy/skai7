# Волна 0 — Прочитать контекст (Nemotron)
> 🤖 **Модель: `nvidia/nemotron-3-super-120b-a12b:free`** | контекст
> 💰 **Бюджет:** читать только файлы · код не писать · файлы не менять
> ⚠️ **Один промпт = одна сессия Cherry Studio.**

## Промпт

Ты — агент-читатель. Твоя задача: прочитать контекст проекта и ответить на вопросы строго по шаблону. **Код не пиши, файлы не создавай и не меняй.**

### Шаг 1. Прочитай файлы

Прочитай **целиком**:
- `AGENTS.md` (в корне проекта)

Прочитай **заголовки + первые 5 строк** из CSV-файлов:
- `data/selected_video_alarms.csv`
- `data/track_points.csv`
- `data/video_files.csv`
- `data/vehicles.csv`
- `data/track_summary.csv` (хотя бы заголовки)

### Шаг 2. Ответь строго по шаблону

```
РЕАЛЬНЫЕ ПОЛЯ CSV (из selected_video_alarms.csv):
  AlarmId, TelemetryId, TerminalId, UnitId, UnitName, UnitStateNumber, Begin, End, Type, Speed, Address, VideoCount, VideoSizeBytes, CameraIds, RequestedCameraIds, Latitude, Longitude

РЕАЛЬНЫЕ ПОЛЯ CSV (из track_points.csv):
  alarm_id, dataset_vehicle_code, unit_id, unit_state_number, event_type, event_begin_utc, period_index, period_type, point_index, timestamp_utc, latitude, longitude, speed_kmh, angle, course, ew

РЕАЛЬНЫЕ ПОЛЯ CSV (из video_files.csv):
  alarm_id, video_file_id, channel, media_relative_path, duration_seconds, video_width, video_height, video_codec, download_status, size_bytes

РЕАЛЬНЫЕ ПОЛЯ CSV (из vehicles.csv):
  dataset_vehicle_code, unit_id, unit_name, unit_state_number, alarm_count, alarm_types, video_metadata_count, downloaded_video_count, track_window_count, track_point_count, total_track_mileage_km

РЕАЛЬНЫЕ ПОЛЯ CSV (из track_summary.csv):
  alarm_id, dataset_vehicle_code, unit_id, unit_name, unit_state_number, event_type, event_begin_utc, event_end_utc, total_parking_duration, total_movement_duration, total_mileage_km, movement_mileage_km, movement_distance_navigation_km, break_distance_navigation_km, distance_odometer_km, track_period_count, track_point_count, max_speed_point_count, raw_track_path

ТЕМА MVP:
  SKAI Unified Incident Window — единое окно видео и телематики. Диспетчер видит событие, трек, контекст, медиа-доказательство и может выполнить быстрое действие. Строим оффлайн-прототип за 8 часов на Python 3.12 + Streamlit.

ЭКРАНЫ (3 вкладки Streamlit):
  1. «Данные» — обзор CSV-файлов: список загруженных таблиц, количество строк и столбцов, превью первых 10 строк по выбранной таблице.
  2. «Дашборд» — KPI-метрики (всего алармов, машин, видеофайлов, средняя скорость) и интерактивный график Altair (распределение алармов по типу, скорости на треке).
  3. «Детали» — риск-таблица: сводка по машинам с флагами риска (превышение скорости, резкое торможение, геозона); форма действий: отметить как проверено, запросить видео, создать отчёт.

АРХИТЕКТУРА ДАННЫХ:
  CSV-файлы → Pandas DataFrame (data_loader.py) → фильтрация и агрегация (metrics.py, risk_table.py) → Streamlit-виджеты (app.py). Связь таблиц: alarm_id — сквозной ключ между selected_video_alarms, track_points, track_summary, video_files. К машинам — через unit_id/unit_state_number/dataset_vehicle_code к vehicles.csv. Медиа — media_relative_path из video_files.csv.

МОДУЛИ PYTHON (5+):
  data_loader.py     — загрузка CSV в DataFrame, кэширование @st.cache_data
  metrics.py         — расчёт KPI: всего алармов, машин, видео, средняя/макс скорость
  charts.py          — графики Altair: столбчатая диаграмма типов алармов, линейный график скорости по треку
  risk_table.py      — построение риск-таблицы: флаги speeding, harsh_braking, geofence
  actions.py         — форма действий: отметить как проверено, запросить видео, создать отчёт
  app.py             — точка входа Streamlit: боковая панель, вкладки, компоновка

СТЕК:
  Python 3.12, Streamlit 1.44, Pandas 2.2, Altair 5.5

ЦВЕТОВАЯ СХЕМА (из AGENTS.md):
  явно не задана — используем стандартную тему Streamlit

ГЛАВНЫЙ РИСК:
  Качество данных и связывание телематики с видео по машине/временному окну. Разные системы (VA и телематика) могут использовать разные идентификаторы машин. Ключ связывания — alarm_id + unit_id + временной допуск. Если alarm_id отсутствует в одной из таблиц или временные метки не совпадают в пределах окна (±N секунд), связь рвётся и инцидент остаётся без видео-доказательства.
```

### Шаг 3. Проверь себя

- [ ] Прочитан AGENTS.md (целиком)
- [ ] Прочитаны заголовки минимум 3 CSV-файлов
- [ ] Тема MVP подтверждена: SKAI Unified Incident Window
- [ ] Названы 3 экрана Streamlit (Данные, Дашборд, Детали)
- [ ] Описана архитектура данных: CSV → DataFrame → Streamlit
- [ ] Перечислены 5+ Python-модулей с назначением каждого
- [ ] Указан стек: Python 3.12, Streamlit 1.44, Pandas 2.2, Altair 5.5
- [ ] Назван главный риск: качество данных и связывание телематики с видео
- [ ] Код не написан, файлы не созданы, файлы не изменены

## Acceptance criteria
- AGENTS.md прочитан.
- Заголовки CSV считаны и перечислены в ответе.
- Тема MVP подтверждена.
- 3 вкладки Streamlit названы и описаны.
- Архитектура «CSV → Pandas → Streamlit» объяснена.
- 5+ модулей перечислены с назначением.
- Стек указан.
- Главный риск сформулирован.
- Код отсутствует в ответе агента.
- Файлы проекта не изменены.
