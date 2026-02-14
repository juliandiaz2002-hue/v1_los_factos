"""Entrypoint Streamlit de Los Factos v2."""

from __future__ import annotations

import streamlit as st

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
from utils.errors import to_user_message
from utils.logging import configure_logging, get_logger


st.set_page_config(
    page_title="Los Factos v2",
    page_icon="\U0001F4B8",
    layout="wide",
    initial_sidebar_state="expanded",
)

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("los_factos.app")
apply_global_theme()

page = st.sidebar.radio(
    "Navegacion",
    options=[
        "Dashboard",
        "Carga e ingesta",
        "Movimientos",
        "Categorias",
        "Mantenimiento",
    ],
)
st.sidebar.caption(f"Entorno: {settings.app_env}")

page_handlers = {
    "Dashboard": render_dashboard_page,
    "Carga e ingesta": render_ingestion_page,
    "Movimientos": render_movimientos_page,
    "Categorias": render_categorias_page,
    "Mantenimiento": render_mantenimiento_page,
}

try:
    with session_scope() as session:
        handler = page_handlers[page]
        handler(session)
except Exception as exc:  # noqa: BLE001
    logger.exception("Unhandled exception", extra={"extra": {"page": page}})
    st.error(to_user_message(exc))
