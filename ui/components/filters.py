"""Helpers de visualizacion de filtros."""

from __future__ import annotations

import streamlit as st


def render_filter_chips(labels: list[str]) -> None:
    if not labels:
        st.caption("Sin filtros activos")
        return

    chips = "".join(f'<span class="lf-chip">{label}</span>' for label in labels)
    st.markdown(f'<div class="lf-chip-wrap">{chips}</div>', unsafe_allow_html=True)
