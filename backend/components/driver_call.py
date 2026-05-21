from __future__ import annotations

import hashlib
from typing import Optional

import streamlit as st
import pandas as pd


def _generate_phone(unit_state_number: str, seed: str) -> str:
    """Генерирует стабильный моковый номер на основе госномера."""
    h = hashlib.md5(f"{unit_state_number}:{seed}".encode()).hexdigest()
    digits = "".join(c for c in h if c.isdigit())
    # Russian mobile format: +7 (9xx) xxx-xx-xx
    code = int(digits[:3]) % 900 + 100  # 100-999
    part1 = int(digits[3:6]) % 900 + 100
    part2 = int(digits[6:8]) % 90 + 10
    part3 = int(digits[8:10]) % 90 + 10
    return f"+7 ({code}) {part1}-{part2:02d}-{part3:02d}"


def _generate_terminal_number(unit_state_number: str) -> str:
    """Генерирует стабильный номер терминала."""
    h = hashlib.md5(f"term:{unit_state_number}".encode()).hexdigest()
    digits = "".join(c for c in h if c.isdigit())
    # Terminal numbers are typically short
    return f"*{int(digits[:4]) % 9000 + 1000}"


def get_driver_contact(unit_state_number: str, datasets: dict) -> dict[str, str]:
    """Возвращает контакты водителя и терминала."""
    vehicles_df = datasets.get("vehicles")
    if vehicles_df is not None and not vehicles_df.empty:
        if "unit_state_number" in vehicles_df.columns:
            mask = vehicles_df["unit_state_number"] == unit_state_number
            if mask.any():
                row = vehicles_df[mask].iloc[0]
                driver_phone = str(row.get("driver_phone", "")).strip()
                terminal_phone = str(row.get("terminal_phone", "")).strip()
                if driver_phone and driver_phone.lower() != "nan":
                    return {
                        "driver_phone": driver_phone,
                        "terminal_phone": terminal_phone if terminal_phone and terminal_phone.lower() != "nan" else _generate_terminal_number(unit_state_number),
                    }

    # Fallback: generate mock numbers
    return {
        "driver_phone": _generate_phone(unit_state_number, "driver"),
        "terminal_phone": _generate_terminal_number(unit_state_number),
    }


def render_driver_call_button(
    unit_state_number: str,
    datasets: dict,
    key_prefix: str = "",
    use_container_width: bool = True,
) -> None:
    """Рендерит кнопку "Позвонить водителю" с поповером для выбора способа связи."""
    contact = get_driver_contact(unit_state_number, datasets)
    driver_phone = contact["driver_phone"]
    terminal_phone = contact["terminal_phone"]

    popover_key = f"{key_prefix}_call_popover_{unit_state_number}"

    with st.popover("📞 Позвонить водителю", use_container_width=use_container_width):
        st.markdown("**Выберите способ связи**")
        st.caption(f"ТС: `{unit_state_number}`")

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("📱 **Сотовый**")
            st.caption(driver_phone)
            if st.button("Позвонить", key=f"{key_prefix}_call_mobile_{unit_state_number}", use_container_width=True):
                st.markdown(
                    f'<meta http-equiv="refresh" content="0; url=tel:{driver_phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")}" />',
                    unsafe_allow_html=True,
                )
                st.success(f"Звонок на {driver_phone}")

        with col2:
            st.markdown("🎙 **Терминал**")
            st.caption(terminal_phone)
            if st.button("Дозвон", key=f"{key_prefix}_call_terminal_{unit_state_number}", use_container_width=True):
                st.info(f"Дозвон на терминал {terminal_phone}...")
                st.caption("SIP-шлюз: соединение установлено (демо)")

        st.divider()
        st.caption("В демо-режиме звонок открывает нативный диалер устройства.")
