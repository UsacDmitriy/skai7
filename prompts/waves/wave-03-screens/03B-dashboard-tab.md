# 03B · Вкладка Dashboard (app/app.py)
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–5 файлов · не читать `./data`, `.venv` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 3

**Файл:** `app/app.py` (заменить тело `render_dashboard_tab`)

Передать модели файлы: `app/app.py`, `app/metrics.py`, `app/charts.py`, `app/data_loader.py`, `app/constants.py`.

## Промпт

```
Прочитай AGENTS.md и файлы:
  - app/app.py (текущее состояние — заглушки)
  - app/metrics.py (функция build_dashboard_metrics)
  - app/charts.py (build_scatter_chart, build_speed_chart, build_track_map)
  - app/data_loader.py (load_csv_files)
  - app/constants.py (константы)

ЗАДАЧА: реализовать вкладку Dashboard в app/app.py, заменив заглушку render_dashboard_tab.

────────────────────────────────────────────

ШАГ 1. Функция pick_dataset УЖЕ существует в app/data_overview.py (создана в wave 02C и переиспользована в wave 03A).
НЕ создавай этот файл заново. Просто импортируй pick_dataset из готового модуля:

```python
from app.data_overview import pick_dataset
```

────────────────────────────────────────────

ШАГ 2. В app/app.py:
  - ДОБАВЬ импорты вверху (после импорта из constants):

```python
from app.data_overview import pick_dataset
from app.metrics import build_dashboard_metrics
from app.charts import build_scatter_chart, build_speed_chart, build_track_map
```

  - ЗАМЕНИ тело функции render_dashboard_tab (строки 28–30) на:

```python
def render_dashboard_tab(datasets: dict[str, pd.DataFrame]) -> None:
    """Dashboard tab: KPI metrics + Altair charts."""
    st.subheader("Дашборд")

    # KPI metrics
    metrics = build_dashboard_metrics(datasets)
    cols = st.columns(4)
    for col, item in zip(cols, metrics):
        col.metric(item["label"], item["value"], item.get("delta"))

    # Dataset picker
    selected, df = pick_dataset(datasets)
    if not selected or df.empty:
        st.info("Добавьте данные чтобы увидеть графики.")
        return

    # Generic scatter chart
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if len(numeric_cols) >= 2:
        col1, col2 = st.columns(2)
        with col1:
            x_col = st.selectbox("Ось X", numeric_cols, index=0, key="dash_x")
        with col2:
            y_col = st.selectbox("Ось Y", numeric_cols, index=min(1, len(numeric_cols) - 1), key="dash_y")
        chart = build_scatter_chart(df, x_col, y_col)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Нужно минимум две числовые колонки для графика.")

    # Speed chart (if track_points data)
    speed_chart = build_speed_chart(df)
    if speed_chart:
        st.altair_chart(speed_chart, use_container_width=True)

    # Track map (if lat/lon data)
    track_map = build_track_map(df)
    if track_map:
        st.altair_chart(track_map, use_container_width=True)
```

  - НЕ меняй больше ничего. render_data_tab, render_details_tab, main() — не трогай.

────────────────────────────────────────────

ШАГ 3. Проверка: запусти `streamlit run app/app.py` и убедись, что:
  - Нет ошибок импорта
  - Вкладка «Dashboard» показывает 4 KPI-карточки (обычно: "CSV файлов", "Строк загружено", "Событий-кандидатов", "Статус MVP")
  - При выборе датасета в сайдбаре появляется scatter-чарт если есть ≥2 числовых колонки
  - Если датасет содержит latitude + longitude — показывается карта трека
  - Если датасет содержит timestamp_utc + speed_kmh — показывается график скорости
  - Остальные вкладки (Данные, Детали) по-прежнему показывают плейсхолдеры
```

## Acceptance criteria
- `pick_dataset` импортируется из существующего `app.data_overview` (создан в wave 02C), файл НЕ пересоздаётся.
- В `app/app.py` добавлены импорты: `from app.data_overview import pick_dataset`, `from app.metrics import build_dashboard_metrics`, `from app.charts import build_scatter_chart, build_speed_chart, build_track_map`.
- Функция `render_dashboard_tab` заменена на рабочую реализацию (не заглушка).
- Никакой другой код в `app/app.py` не изменён.
- `streamlit run app/app.py` запускается без ошибок импорта.
- Вкладка Dashboard показывает 4 KPI-метрики в ряд.
- При выборе датасета — scatter-чарт, опционально карта трека и график скорости.
