"""Tarjetas reutilizables para KPI e insights."""

from __future__ import annotations

import html

import streamlit as st


def render_kpi_card(
    label: str,
    value: str,
    delta: str | None = None,
    *,
    icon: str = "",
    icon_color: str = "#737373",
    value_compact: bool = False,
    delta_tone: str = "neutral",
) -> None:
    tone = delta_tone if delta_tone in {"positive", "negative", "neutral"} else "neutral"
    value_class = "value compact" if value_compact else "value"
    if delta:
        delta_html = f'<div class="delta {tone}">{delta}</div>'
    else:
        delta_html = '<div class="delta empty">&nbsp;</div>'
    st.markdown(
        f"""
  <div class="lf-kpi">
  <div class="head">
    <div class="label">{label}</div>
    <div class="icon" style="color:{icon_color};">{icon}</div>
  </div>
  <div class="{value_class}">{value}</div>
  <div class="delta-slot">{delta_html}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_insight_card(title: str, body: str, *, explanation: str | None = None) -> None:
    title_safe = html.escape(title, quote=True)
    body_safe = html.escape(body, quote=True)
    tooltip_html = ""
    if explanation:
        explanation_safe = html.escape(explanation, quote=True)
        tooltip_html = (
            '<span class="lf-insight-help" tabindex="0" aria-label="Como se calcula">'
            "i"
            f'<span class="lf-insight-tip">{explanation_safe}</span>'
            "</span>"
        )
    st.markdown(
        f"""
<div class="lf-insight">
  <div class="lf-insight-head">
    <div class="lf-insight-title">{title_safe}</div>
    {tooltip_html}
  </div>
  <div class="lf-insight-body">{body_safe}</div>
</div>
        """,
        unsafe_allow_html=True,
    )
