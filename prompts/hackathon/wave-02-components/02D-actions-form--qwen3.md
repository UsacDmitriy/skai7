Model: qwen/qwen3-coder:free

Agent task: create `app/actions.py` — action form for the Details tab.

The file must contain:

1. `render_action_form(output_dir)` — Streamlit form with row_id input, action selectbox, comment textarea, submit button. Calls save_action() on submit.

Code:

```python
from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.constants import ACTION_TYPES, ACTION_LABELS
from app.data_loader import save_action


def render_action_form(output_dir: Path) -> None:
    """Render action form and handle submission.

    Form fields:
    - row_id: text input (vehicle/driver/alarm ID)
    - action: selectbox from ACTION_TYPES with Russian labels
    - comment: text area for notes
    - submit button: saves to output/actions.csv
    """
    with st.form("action_form", clear_on_submit=True):
        st.subheader("Действие диспетчера")

        row_id = st.text_input(
            "ID записи / ТС / водителя",
            placeholder="Например: AL-10001 или А123ВС77",
        )

        action = st.selectbox(
            "Действие",
            options=ACTION_TYPES,
            format_func=lambda a: ACTION_LABELS.get(a, a),
        )

        comment = st.text_area(
            "Комментарий",
            height=80,
            placeholder="Дополнительная информация...",
        )

        submitted = st.form_submit_button(
            "Сохранить действие",
            type="primary",
        )

    if submitted:
        if not row_id.strip():
            st.error("Укажите ID записи.")
        else:
            save_action(output_dir, row_id=row_id.strip(), action=action, comment=comment.strip())
            st.success(f"Действие сохранено в output/actions.csv")
            st.rerun()


__all__ = ["render_action_form"]
```

Rules:
- Save to `app/actions.py`
- Import ACTION_TYPES, ACTION_LABELS from app.constants
- Import save_action from app.data_loader
- Use clear_on_submit=True for the form
- Validate row_id is not empty before saving
- Show st.success() and st.rerun() after successful save
- Type hints, docstrings in Russian
- Check: `python -c "from app.actions import render_action_form"` must pass

Write the complete file in Russian using the Write tool.
