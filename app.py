"""Entrypoint Streamlit de Los Factos v2."""

from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from data.bootstrap import ensure_database_ready
from data.session import session_scope
from ui.components import apply_global_theme
from ui.pages import (
    render_categorias_page,
    render_dashboard_page,
    render_ingestion_page,
    render_mantenimiento_page,
    render_movimientos_page,
)
from utils.config import get_settings
from utils.errors import AppError, to_user_message
from utils.logging import configure_logging, get_logger


st.set_page_config(
    page_title="Los Factos v2",
    page_icon="\U0001F4B8",
    layout="wide",
    initial_sidebar_state="collapsed",
)

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("los_factos.app")
apply_global_theme()

page_handlers = {
    "Dashboard": render_dashboard_page,
    "Carga e ingesta": render_ingestion_page,
    "Movimientos": render_movimientos_page,
    "Categorias": render_categorias_page,
    "Mantenimiento": render_mantenimiento_page,
}


def render_top_navigation() -> str:
    page_order = [
        ("Dashboard", "Dashboard", ":material/insights:"),
        ("Movimientos", "Movimientos", ":material/receipt_long:"),
        ("Carga e ingesta", "Importar CSV", ":material/upload:"),
        ("Categorias", "Categorias", ":material/settings:"),
        ("Mantenimiento", "Exportar", ":material/download:"),
    ]
    if "active_page" not in st.session_state:
        st.session_state.active_page = "Dashboard"

    st.markdown('<div class="lf-header-wrap">', unsafe_allow_html=True)
    left, right = st.columns([2.1, 4.4])
    with left:
        st.markdown(
            """
            <div class="lf-brand">
              <div class="lf-title">Facto$</div>
              <div class="lf-subtitle">Control de gastos personales</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        cols = st.columns(5)
        for idx, (page_id, label, icon) in enumerate(page_order):
            with cols[idx]:
                if st.button(
                    label,
                    key=f"top_nav_{page_id}",
                    type="primary" if st.session_state.active_page == page_id else "secondary",
                    icon=icon,
                    width="stretch",
                ):
                    if st.session_state.active_page != page_id:
                        st.session_state.active_page = page_id
                        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(f'<div class="lf-env-tag">Entorno: {settings.app_env}</div>', unsafe_allow_html=True)
    return str(st.session_state.active_page)


page = "startup"
try:
    ensure_database_ready()
    page = render_top_navigation()
    with session_scope() as session:
        handler = page_handlers[page]
        handler(session)
except Exception as exc:  # noqa: BLE001
    if isinstance(exc, AppError):
        logger.warning("Application error", extra={"extra": {"page": page, "message": str(exc)}})
    else:
        logger.exception("Unhandled exception", extra={"extra": {"page": page}})
    st.error(to_user_message(exc))
