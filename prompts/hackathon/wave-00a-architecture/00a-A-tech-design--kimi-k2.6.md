# Волна 00a-A — Техническая архитектура (Streamlit)
> 🤖 **Модель: `moonshotai/kimi-k2.6`** | архитектура Streamlit-приложения
> 💰 **Контекст: AGENTS.md (секции 1, 5, 6) + скриншоты** (~5K токенов, ~$0.04)
> ❌ НЕ читать: code/clade_design/*.html (1.7–1.9MB = $0.31+ за чтение!)
> ⚠️ Один промпт = одна сессия · результат → `hackathon/context/TECH-DESIGN.md`

## Что передать в сессию

1. **Секции 1, 5, 6 из AGENTS.md** (скопировать текстом — ~2K токенов)
2. **Прикрепить скриншоты как images**:
   - `code/clade_design/Интерактивнй отчет/verify-standalone.jpg`
   - `code/clade_design/Интерактивнй отчет/scenario-unified-window.jpg` (если есть)
   - `code/clade_design/Интерактивнй отчет/scenario-event-history.jpg` (если есть)

> Почему jpg, а не html?
> HTML-файлы — 1.7–1.9MB, 425–478K токенов, $0.31 только на чтение.
> JPG-скриншоты — 10–50KB, Kimi видит дизайн визуально, стоит <$0.01.

---

## Промпт

```
Ты — ведущий архитектор Streamlit-приложений. Контекст продукта: [секции AGENTS.md].
На изображениях — скриншоты экранов SKAI (Интерактивный отчёт).

Задача: спроектировать архитектуру Streamlit-приложения на Python 3.12.
Напиши файл `hackathon/context/TECH-DESIGN.md` со следующими разделами:

## 1. Дерево модулей (Python-модули, НЕ React-компоненты)

Только эти модули в `app/`:
```
app/
├── __init__.py
├── app.py              # Точка входа Streamlit: сайдбар + 3 вкладки (Data / Dashboard / Details)
├── data_loader.py      # load_csv_files() → dict[str, DataFrame]; save_action() → запись в output/
├── metrics.py          # build_dashboard_metrics(df) → dict[str, float] для st.metric()
├── charts.py           # build_altair_chart(df, x_col, y_col) → alt.Chart (scatter/line)
├── risk_table.py       # build_risk_table(df) → top-N DataFrame по risk_score / severity
├── tabs.py             # render_data_tab(), render_dashboard_tab(), render_details_tab()
└── actions.py          # save_action(row_id, action_type, comment) → append в output/actions.csv
```

Для каждого модуля:
- Назначение (одна фраза)
- Что импортирует
- Что экспортирует (имя функции и сигнатура с типами)
- Откуда данные: из какого CSV-файла

## 2. Поток данных (Data Flow)

Схема:
```
data/ (CSV-файлы)
  │
  ├─ selected_video_alarms.csv ─┐
  ├─ video_files.csv           ─┤
  ├─ track_summary.csv         ─┤
  ├─ track_points.csv          ─┤
  ├─ vehicles.csv              ─┤
  └─ max_speed_points.csv      ─┤
                                 ▼
                    data_loader.load_csv_files()
                                 │
                                 ▼
                       dict[str, pd.DataFrame]
                       ("alarms", "videos", "track_summary", "track_points", "vehicles", "max_speed")
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
               Data tab    Dashboard tab  Details tab
              (превьюшки)   (KPI + чарты)  (risk-таблица + форма действий)
                                 │
                                 ▼
                         actions.save_action()
                                 │
                                 ▼
                         output/actions.csv
```

Описать:
- Как data_loader.load_csv_files() читает все CSV из data/ и возвращает словарь
- Как словарь datasets передаётся аргументом в каждый tab-рендерер
- Как sidebar.dataset_selector влияет на отображаемый DataFrame
- Как st.form в Details tab вызывает save_action()

## 3. Спецификация вкладок

### Tab 1 — Data (render_data_tab)
- Сводная таблица: имя файла, кол-во строк, кол-во колонок (st.dataframe)
- Выбор датасета через `st.sidebar.selectbox("Датасет", list(datasets.keys()))`
- Превью выбранного датасета: `st.dataframe(df.head(100))`
- Колонки выбранного датасета: `st.write(list(df.columns))`

### Tab 2 — Dashboard (render_dashboard_tab)
- 4 карточки KPI через `st.metric()`:
  - Всего алармов (из `selected_video_alarms`)
  - Всего машин (из `vehicles`)
  - Всего видеофайлов (из `video_files`)
  - Средняя скорость (из `selected_video_alarms`, колонка Speed)
- Переключатель датасета для чарта: `st.sidebar.selectbox("Датасет для чарта", ...)`
- Два `st.selectbox("X", columns)` и `st.selectbox("Y", columns)` — выбор числовых колонок
- Altair-чарт (`alt.Chart(df).mark_point()` или `.mark_line()`) с tooltip
- Параметры чарта: width=700, height=400

### Tab 3 — Details (render_details_tab)
- Risk-таблица: top-20 строк из `selected_video_alarms`, отсортированных по `risk_score` (если нет — по `Speed` убыванию)
- Колонки: AlarmId, UnitStateNumber, Type, Speed, Begin, Latitude, Longitude, VideoCount
- Строки кликабельны: выбор строки через `st.dataframe(use_container_width=True)` + `st.session_state.selected_row`
- Под таблицей — детали выбранного аларма:
  - Связанные видео: `video_files[video_files.alarm_id == selected.AlarmId]`
  - Связанные треки: `track_points[track_points.alarm_id == selected.AlarmId]`
  - Мини-чарт трека (скорость по времени)
- Форма действий: `st.form("action_form")` с полями:
  - `row_id` (автозаполнен из selected_row)
  - `action_type` = `st.selectbox("Действие", ["checked", "request_video", "create_report", "escalate"])`
  - `comment` = `st.text_area("Комментарий")`
  - Кнопка «Сохранить» → вызывает `save_action(row_id, action_type, comment)`
- После сохранения: `st.success()` + перезапись `output/actions.csv`

## 4. Управление состоянием (State Management)

- Только `st.session_state` — никаких внешних менеджеров состояния.
- Ключи session_state:
  - `datasets`: dict[str, pd.DataFrame] — загруженные данные (заполняется один раз в app.py)
  - `selected_dataset`: str — выбранный датасет в сайдбаре
  - `selected_row`: int | None — выбранная строка в risk-таблице
  - `chart_x`, `chart_y`: str — выбранные колонки для чарта
- Все данные передаются через аргументы функций. Никакого React Context, Redux, Zustand.
- `load_csv_files()` вызывается ОДИН раз при старте с `@st.cache_data`.
- `save_action()` пишет напрямую в CSV, не держит состояние.

## 5. Реальные CSV-колонки

Использовать ТОЛЬКО эти имена полей из `data/`:

**selected_video_alarms.csv:**
`AlarmId, UnitStateNumber, Type, Speed, Begin, End, Latitude, Longitude, VideoCount`

**video_files.csv:**
`alarm_id, video_file_id, channel, media_relative_path, size_bytes, duration_seconds`

**track_summary.csv:**
`alarm_id, unit_state_number, event_type, total_mileage_km, track_point_count`

**track_points.csv:**
`alarm_id, timestamp_utc, latitude, longitude, speed_kmh`

**vehicles.csv:**
`unit_state_number, alarm_count, alarm_types, downloaded_video_count`

**max_speed_points.csv:**
`alarm_id, timestamp_utc, latitude, longitude, max_speed_kmh`

ВАЖНО: НЕ придумывать поля. НЕ использовать имена из data/mock/*.json.
Все поля из секции Inputs AGENTS.md — их достаточно.

## 6. Стратегия соединения данных (Join Strategy)

Описать правила соединения для Details tab:
- `selected_video_alarms.AlarmId` ↔ `video_files.alarm_id` (один аларм → много видео)
- `selected_video_alarms.AlarmId` ↔ `track_points.alarm_id` (один аларм → много точек трека)
- `selected_video_alarms.UnitStateNumber` ↔ `vehicles.unit_state_number` (машина → сводка)
- `selected_video_alarms.AlarmId` ↔ `track_summary.alarm_id` (один аларм → одна сводка трека)
- Временное окно для трека: Begin ± 5 минут (если нужно отфильтровать точки)

Только текст файла TECH-DESIGN.md на русском языке. Без объяснений вокруг, без «вот результат», без markdown-обёртки вне файла. Результат должен быть готовым документом, который читают разработчики перед началом кодинга.
```

## Acceptance criteria

- Описаны все 7 модулей из дерева `app/`
- Data Flow содержит все 6 CSV → словарь → 3 вкладки → output
- Все 3 вкладки специфицированы с реальными именами колонок из CSV
- State management использует только st.session_state с перечисленными ключами
- Перечислены ТОЛЬКО реальные колонки CSV (без выдуманных)
- Стратегия соединения покрывает все 4 связи таблиц
- Файл создан как `hackathon/context/TECH-DESIGN.md`
- Размер файла: 5–10KB
- Язык: русский
- НИ одного React-компонента, НИ одного JS/TS-фрагмента — только Python + Streamlit
