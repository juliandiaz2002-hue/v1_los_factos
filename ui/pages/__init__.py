"""Paginas de la aplicacion."""

from .categorias import render_categorias_page
from .dashboard import render_dashboard_page
from .ingestion import render_ingestion_page
from .mantenimiento import render_mantenimiento_page
from .movimientos import render_movimientos_page

__all__ = [
    "render_categorias_page",
    "render_dashboard_page",
    "render_ingestion_page",
    "render_mantenimiento_page",
    "render_movimientos_page",
]
