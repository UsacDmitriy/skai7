# 03C · Details Tab (app/app.py)
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 3

**Файл:** `app/app.py`

Передать: `app/app.py`, `app/constants.py`, `app/risk_table.py`, `app/actions.py`.

## Задача

Заменить заглушку `render_details_tab` в `app/app.py` на реальную реализацию.

Вкладка «Детали» должна показывать:
1. Таблицу рисков (топ-20 по `risk_score`, с русскими метками)
2. Форму действий: поле `row_id`, selectbox с русскими метками (`mark_reviewed`/`create_task`/`export_report`), поле комментария, кнопка отправки
3. При отправке: сохранение в `output/actions.csv`, сообщение об успехе

## Промпт

```
Прочитай app/app.py, app/constants.py, app/risk_table.py и app/actions.py.

Найди в app.py функцию render_details_tab с заглушкой.

Добавь в блок импортов app.py:
  from constants import OUTPUT_DIR_NAME
  from risk_table import render_risk_table
  from actions import render_action_form

После блока импортов (после строчек c DATA_DIR и SAMPLE_DATA_DIR) добавь:
  OUTPUT_DIR = PROJECT_ROOT / OUTPUT_DIR_NAME

Замени тело render_details_tab на этот код:

def render_details_tab(datasets: dict[str, pd.DataFrame]) -> None:
    """Details tab: risk table + action form."""
    st.subheader("Детали и действия")

    # Risk table (top-20 by risk_score, Russian labels)
    render_risk_table(datasets)

    st.divider()

    # Action form (row_id + action selectbox + comment + submit)
    render_action_form(OUTPUT_DIR)

Правила:
- Заменить ТОЛЬКО тело render_details_tab
- Добавить импорты в начало файла, в блок существующих импортов
- Добавить OUTPUT_DIR = PROJECT_ROOT / OUTPUT_DIR_NAME после SAMPLE_DATA_DIR
- OUTPUT_DIR_NAME уже определён в constants.py — импортировать его
- Остальной код app.py не трогать
- render_data_tab и render_dashboard_tab оставить без изменений
- Не менять main()

После замены запусти проверку:
  streamlit run app/app.py

Вкладка «Детали» должна отображать таблицу рисков и форму действий. При заполнении формы и отправке в output/actions.csv должна появиться новая запись.
```

## Acceptance criteria
- `render_details_tab` заменён с заглушки на реальную реализацию
- Импорт `from risk_table import render_risk_table` и `from actions import render_action_form` добавлен в `app.py`
- Импорт `from constants import OUTPUT_DIR_NAME` добавлен в `app.py`
- `OUTPUT_DIR = PROJECT_ROOT / OUTPUT_DIR_NAME` добавлен после `SAMPLE_DATA_DIR`
- Остальной код `app.py` не изменён
- `streamlit run app/app.py` запускается без ошибок
- Вкладка «Детали» показывает таблицу рисков (топ-20 с русскими метками) и форму действий
- При отправке формы действие сохраняется в `output/actions.csv`
- После успешной отправки отображается `st.success("Действие сохранено в output/actions.csv")`
