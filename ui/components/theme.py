"""Tema premium para Streamlit."""

from __future__ import annotations

import streamlit as st


def apply_global_theme() -> None:
    st.markdown(
        """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,500,0,0" rel="stylesheet">
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
  background: var(--lf-bg);
  color: var(--lf-ink);
}
[data-testid="stSidebar"] {display: none;}
[data-testid="stAppViewContainer"] {padding-top: 0;}
.block-container {
  max-width: 1440px;
  padding-top: 1.1rem;
  padding-left: 1.4rem;
  padding-right: 1.4rem;
  padding-bottom: 1.8rem;
}
.lf-header-wrap {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--lf-bg);
  border-bottom: 1px solid var(--lf-border);
  margin-left: -1.4rem;
  margin-right: -1.4rem;
  padding: 0.9rem 1.4rem 0.95rem 1.4rem;
  margin-bottom: 0.8rem;
}
.lf-brand .lf-title {font-size: 1.92rem; font-weight: 800; letter-spacing: -0.02em; line-height: 1.05;}
.lf-brand .lf-subtitle {font-size: 0.98rem; color: var(--lf-muted); margin-top: 0.08rem;}
.lf-env-tag {font-size: 12px; color: #666; margin-bottom: 0.6rem;}
.stButton > button {
  border-radius: 999px;
  border: 1px solid var(--lf-border);
  background: #F3F3F3;
  color: #111111;
  font-weight: 600;
  min-height: 44px;
}
.stButton > button[kind="primary"] {
  background: #0A0A0A;
  color: #FFFFFF;
  border-color: #0A0A0A;
}
.stButton > button:hover {
  border-color: #D3D3D3;
}
.lf-kpi, .lf-insight {
  background: var(--lf-card);
  border: 1px solid var(--lf-border);
  border-radius: var(--lf-radius);
  box-shadow: 0 1px 2px rgba(0,0,0,0.02);
  padding: 18px 18px;
}
.lf-kpi {height: 198px; display:flex; flex-direction:column; justify-content:flex-start;}
.lf-kpi .head {display:flex; align-items:center; justify-content:space-between; gap:10px; min-height: 28px;}
.lf-kpi .label {color: #666666; font-weight: 600; font-size: 1rem;}
.lf-kpi .icon {
  font-family: "Material Symbols Outlined";
  font-size: 1.25rem;
  line-height: 1;
  color: #737373;
  opacity: .9;
}
.lf-kpi .value {
  color: var(--lf-ink);
  font-weight: 800;
  font-size: 2.12rem;
  letter-spacing:-0.02em;
  margin-top: 10px;
  line-height: 1.1;
  min-height: 74px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.lf-kpi .value.compact {
  font-size: 2.0rem;
  white-space: nowrap;
}
.lf-kpi .delta-slot {margin-top: auto; min-height: 28px; display:flex; align-items:flex-end;}
.lf-kpi .delta {font-weight: 700; font-size: .95rem;}
.lf-kpi .delta.empty {opacity: 0;}
.lf-kpi .delta.positive {color: #10B981;}
.lf-kpi .delta.negative {color: #EF4444;}
.lf-kpi .delta.neutral {color: #737373;}
.lf-insight {min-height: 124px; position: relative; overflow: visible;}
.lf-insight-head {display:flex; align-items:flex-start; justify-content:space-between; gap:8px; margin-bottom:6px;}
.lf-insight-title {font-weight:800; font-size:15px; line-height:1.25; color:#161616;}
.lf-insight-body {font-size:13px; color:#445555; line-height:1.45;}
.lf-insight-help {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 999px;
  border: 1px solid #D5D5D5;
  background: #FFFFFF;
  color: #4B5563;
  font-size: 12px;
  font-weight: 800;
  cursor: help;
  flex-shrink: 0;
}
.lf-insight-tip {
  position: absolute;
  right: 0;
  bottom: calc(100% + 8px);
  width: 260px;
  border: 1px solid #D4D4D4;
  border-radius: 10px;
  background: #111111;
  color: #F8F8F8;
  padding: 8px 10px;
  font-size: 12px;
  line-height: 1.35;
  font-weight: 500;
  box-shadow: 0 10px 24px rgba(0,0,0,0.16);
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  z-index: 30;
  transition: opacity .15s ease;
}
.lf-insight-help:hover .lf-insight-tip,
.lf-insight-help:focus .lf-insight-tip,
.lf-insight-help:focus-visible .lf-insight-tip {
  opacity: 1;
  visibility: visible;
}
.lf-chart-card {
  background: var(--lf-card);
  border: 1px solid var(--lf-border);
  border-radius: var(--lf-radius);
  padding: 18px 18px 8px 18px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}
[data-testid="stVerticalBlockBorderWrapper"] {
  border: 1px solid var(--lf-border) !important;
  border-radius: var(--lf-radius) !important;
  background: #FFFFFF !important;
  box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}
[data-testid="stVerticalBlockBorderWrapper"] > div {
  padding: 1rem 1rem 0.45rem 1rem;
}
.lf-chart-title {font-size: 1.3rem; font-weight: 700; margin-bottom: 0; line-height: 1.25;}
.lf-chart-subtitle {font-size: 0.95rem; color: #666; margin-top: 0.12rem; margin-bottom: 0.7rem;}
.lf-section-title {font-size: 1.48rem; font-weight: 800; margin: 0;}
.lf-section-subtitle {font-size: .96rem; color: #666; margin-top: .2rem; margin-bottom: .8rem;}
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
[data-testid="stMetric"] {background: white; border: 1px solid var(--lf-border); border-radius: 12px; padding: 10px;}
[data-testid="stExpander"] summary p {font-size: 1.02rem; font-weight: 700;}
[data-testid="stExpanderDetails"] label p {font-size: .92rem;}
[data-testid="stSelectbox"] [data-baseweb="select"] {font-size: .95rem;}
</style>
        """,
        unsafe_allow_html=True,
    )
