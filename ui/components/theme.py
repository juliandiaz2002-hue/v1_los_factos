"""Tema premium para Streamlit."""

from __future__ import annotations

import streamlit as st


def apply_global_theme() -> None:
    st.markdown(
        """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
:root {
  --lf-bg: #FAFAFA;
  --lf-card: #FFFFFF;
  --lf-ink: #0A0A0A;
  --lf-muted: #5B5B5B;
  --lf-primary: #0A0A0A;
  --lf-accent: #3B82F6;
  --lf-border: #E5E5E5;
  --lf-radius: 12px;
  --lf-shadow: 0 10px 15px rgba(0, 0, 0, 0.08);
}
html, body, [class*="css"] {
  font-family: 'Manrope', sans-serif;
}
.stApp {
  background:
    radial-gradient(circle at 15% -5%, rgba(99, 102, 241, 0.08), transparent 40%),
    radial-gradient(circle at 95% 5%, rgba(6, 182, 212, 0.07), transparent 35%),
    var(--lf-bg);
  color: var(--lf-ink);
}
.lf-kpi, .lf-insight {
  background: var(--lf-card);
  border: 1px solid var(--lf-border);
  border-radius: var(--lf-radius);
  box-shadow: var(--lf-shadow);
  padding: 14px 16px;
}
.lf-kpi .label {color: var(--lf-muted); font-weight: 600; font-size: 13px;}
.lf-kpi .value {color: var(--lf-ink); font-weight: 800; font-size: 26px; margin-top: 4px;}
.lf-kpi .delta {color: #10B981; font-weight: 700; font-size: 12px; margin-top: 4px;}
.lf-chip-wrap {display: flex; flex-wrap: wrap; gap: 8px; margin: 6px 0 12px;}
.lf-chip {
  border: 1px solid #D4D4D4;
  background: #FFFFFF;
  color: #262626;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 700;
}
h1, h2, h3 {
  letter-spacing: -0.015em;
}
</style>
        """,
        unsafe_allow_html=True,
    )
