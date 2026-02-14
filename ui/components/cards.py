"""Tarjetas reutilizables para KPI e insights."""

from __future__ import annotations

import streamlit as st


def render_kpi_card(label: str, value: str, delta: str | None = None) -> None:
    delta_html = f'<div class="delta">{delta}</div>' if delta else ""
    st.markdown(
        f"""
<div class="lf-kpi">
  <div class="label">{label}</div>
  <div class="value">{value}</div>
  {delta_html}
</div>
        """,
        unsafe_allow_html=True,
    )


def render_insight_card(title: str, body: str) -> None:
    st.markdown(
        f"""
<div class="lf-insight">
  <div style=\"font-weight:800; font-size:15px; margin-bottom:6px;\">{title}</div>
  <div style=\"font-size:13px; color:#445555;\">{body}</div>
</div>
        """,
        unsafe_allow_html=True,
    )
