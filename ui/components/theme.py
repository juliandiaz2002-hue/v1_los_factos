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
.lf-insight-title-wrap {display:flex; align-items:center; gap:8px;}
.lf-insight-icon {
  font-family: "Material Symbols Outlined";
  font-size: 1.05rem;
  line-height: 1;
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  border: 1px solid #E5E7EB;
  background: #F8FAFC;
  color: #475569;
}
.lf-insight-title {font-weight:800; font-size:15px; line-height:1.25; color:#161616;}
.lf-insight-body {font-size:13px; color:#445555; line-height:1.45;}
.lf-insight-body strong {font-weight:800; color:#0F172A;}
.lf-insight-projection {
  border-color: #C7D2FE;
  background: linear-gradient(180deg, #EEF2FF 0%, #FFFFFF 42%);
}
.lf-insight-projection .lf-insight-icon {
  border-color: #C7D2FE;
  color: #4338CA;
  background: #E0E7FF;
}
.lf-insight-core {
  border-color: #D1FAE5;
  background: linear-gradient(180deg, #ECFDF5 0%, #FFFFFF 46%);
}
.lf-insight-core .lf-insight-icon {
  border-color: #A7F3D0;
  color: #047857;
  background: #D1FAE5;
}
.lf-insight-dynamic {
  border-color: #FCE7F3;
  background: linear-gradient(180deg, #FFF1F2 0%, #FFFFFF 46%);
}
.lf-insight-dynamic .lf-insight-icon {
  border-color: #FBCFE8;
  color: #BE185D;
  background: #FCE7F3;
}
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
.lf-projection-banner {
  border: 1px solid #C7D2FE;
  background: linear-gradient(92deg, #EEF2FF 0%, #ECFEFF 58%, #FFFFFF 100%);
  border-radius: 14px;
  padding: 12px 14px;
  margin: 6px 0 10px 0;
  display: flex;
  align-items: center;
  gap: 10px;
}
.lf-projection-banner .icon {
  font-family: "Material Symbols Outlined";
  font-size: 1.2rem;
  color: #4338CA;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #C7D2FE;
  background: rgba(255,255,255,0.86);
}
.lf-projection-banner .title {font-weight: 800; color: #1F2937; font-size: 0.95rem;}
.lf-projection-banner .copy {font-size: 0.86rem; color: #4B5563;}
.lf-movements-wrap {display:flex; flex-direction:column; gap:10px; margin-top: 8px;}
.lf-mov-row {
  display:grid;
  grid-template-columns: 40px minmax(180px,1fr) 120px;
  gap: 12px;
  align-items:center;
  border: 1px solid #E5E7EB;
  border-radius: 14px;
  background: #FFFFFF;
  padding: 10px 12px;
}
.lf-mov-left {
  width: 36px;
  height: 36px;
  border-radius: 11px;
  display:flex;
  align-items:center;
  justify-content:center;
  border: 1px solid #E5E7EB;
}
.lf-mov-left .icon {
  font-family: "Material Symbols Outlined";
  font-size: 1.05rem;
  line-height: 1;
}
.lf-mov-detail {font-size: 0.95rem; font-weight: 700; color:#111827; line-height:1.25;}
.lf-mov-date {font-size: 0.80rem; color:#6B7280; margin-top:2px;}
.lf-mov-cat {
  font-size: 0.74rem;
  color: #475569;
  margin-top: 2px;
  font-weight: 600;
  letter-spacing: .01em;
}
.lf-mov-amount {font-size: 1rem; font-weight: 800; color:#0F172A; text-align:right;}
.lf-mov-amount.negative {color: #0F172A;}
[data-testid="stButton"] button[kind="secondary"].lf-delete-btn {
  border-radius: 10px;
}
.lf-cat-stat {
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  padding: 12px 14px;
  min-height: 92px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}
.lf-cat-stat .label {
  color: #6B7280;
  font-weight: 600;
  font-size: 0.85rem;
}
.lf-cat-stat .value {
  color: #0F172A;
  font-weight: 800;
  font-size: 1.55rem;
  margin-top: 8px;
  line-height: 1.1;
}
.lf-cat-stat .value.compact {
  font-size: 1.18rem;
}
.lf-cat-form-title {
  font-size: 1rem;
  font-weight: 800;
  color: #111827;
  margin-bottom: 6px;
}
.lf-cat-list-wrap {display:flex; flex-direction:column; gap:8px; margin-top:4px;}
.lf-cat-icon {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  display:flex;
  align-items:center;
  justify-content:center;
  border: 1px solid #E5E7EB;
}
.lf-cat-icon .icon {
  font-family: "Material Symbols Outlined";
  font-size: 1.08rem;
  line-height: 1;
}
.lf-cat-name {
  font-size: 0.97rem;
  font-weight: 700;
  color: #111827;
  line-height: 1.25;
  margin-top: 2px;
}
.lf-cat-meta {
  margin-top: 3px;
}
.lf-cat-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  border: 1px solid #D1D5DB;
  background: #FFFFFF;
  color: #475569;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 2px 8px;
}
.lf-cat-badge-protected {
  border-color: #C7D2FE;
  background: #EEF2FF;
  color: #3730A3;
}
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
