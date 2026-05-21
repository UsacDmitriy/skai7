from __future__ import annotations

from pathlib import Path

import streamlit as st

from constants import ACTION_LABELS, ACTION_TYPES
from data_loader import save_action


def render_action_form(output_dir: Path) -> None:
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
            st.success("Действие сохранено в output/actions.csv")
            st.rerun()


__all__ = ["render_action_form"]
