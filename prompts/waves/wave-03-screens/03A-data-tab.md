# 03A · Data Tab (app/app.py)
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 3

**Файл:** `app/app.py`

Передать: `app/data_overview.py`, `app/app.py`.

## Задача

Заменить заглушку `render_data_tab` в `app/app.py` на реальную реализацию.

Вкладка Data должна показывать:
1. Обзорную таблицу всех загруженных CSV-файлов (имя файла, количество строк, количество колонок)
2. Селектор датасетов в сайдбаре (selectbox)
3. Превью выбранного датасета (первые 100 строк)

## Промпт

```
Прочитай app/app.py и app/data_overview.py.
Найди в app.py функцию render_data_tab с заглушкой-заголовком.

Добавь в начало app.py импорт:
from app.data_overview import build_dataset_overview, pick_dataset, render_dataset_preview

Замени тело render_data_tab на этот код:

def render_data_tab(datasets: dict[str, pd.DataFrame]) -> None:
    """Data tab: overview of loaded CSV files + preview of selected dataset."""
    st.subheader("Загруженные CSV файлы")

    if not datasets:
        st.warning(
            "CSV файлы не найдены. "
            "Поместите файлы в ./data или скопируйте примеры из ./sample_data."
        )
        return

    # Overview table
    overview = build_dataset_overview(datasets)
    st.dataframe(overview, use_container_width=True, hide_index=True)

    # Dataset picker + preview
    selected, df = pick_dataset(datasets)
    if selected:
        render_dataset_preview(df, selected)
```

Правила:
- Заменить ТОЛЬКО тело render_data_tab
- Добавить импорт в начало файла, в блок существующих импортов
- Остальной код не трогать
- Убедиться: DataOverview содержит импорт `import streamlit as st`

После замены запусти проверку:
streamlit run app/app.py

Вкладка Data должна показывать обзорную таблицу и превью выбранного датасета.
```

## Acceptance criteria
- `render_data_tab` заменён с заглушки на реальную реализацию
- Импорт `from app.data_overview import build_dataset_overview, pick_dataset, render_dataset_preview` добавлен в начало `app.py`
- Остальной код `app.py` не изменён
- `streamlit run app/app.py` запускается без ошибок
- Вкладка Data показывает обзорную таблицу всех CSV и превью выбранного датасета
- При отсутствии датасетов — предупреждение с путём `./data`
