"""Pagina principal de insights."""

from __future__ import annotations

from datetime import date

import streamlit as st

from charts import (
    category_distribution_chart,
    category_frequency_chart,
    monthly_trend_chart,
    projection_chart,
    weekday_chart,
)
from services.dashboard_service import DashboardFilters, DashboardService
from ui.components import render_filter_chips, render_insight_card, render_kpi_card
from ui.pages.common import render_movement_filters
from utils.formatting import format_clp


def render_dashboard_page(session) -> None:
    st.title("Los Factos v2")
    st.caption("Dashboard de gastos personales con foco en decisiones accionables")

    service = DashboardService(session)
    categories = service.list_categories()
    filters, active_filters = render_movement_filters(categories, key_prefix="dashboard")
    render_filter_chips(active_filters)

    dash_filters = DashboardFilters(
        text_filter=filters.text_filter,
        month=filters.month,
        year=filters.year,
        date_from=filters.date_from,
        date_to=filters.date_to,
        category_id=filters.category_id,
    )
    df = service.get_movements_df(dash_filters)

    kpis = service.get_kpis(df)
    selected_year = filters.year or date.today().year
    selected_month = filters.month or date.today().month
    comparison = service.get_month_comparison(year=selected_year, month=selected_month)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_kpi_card("Gasto total", format_clp(-kpis["total_gasto"]), delta=f"Mes {selected_month:02d}")
    with col2:
        render_kpi_card("Ingresos", format_clp(kpis["total_ingresos"]))
    with col3:
        render_kpi_card("Movimientos", f"{kpis['cantidad_movimientos']}")
    with col4:
        render_kpi_card("Ticket promedio", format_clp(-kpis["ticket_promedio"]))

    variation_sign = "+" if comparison["variation_pct"] > 0 else ""
    insight_cols = st.columns(2)
    with insight_cols[0]:
        render_insight_card(
            "Comparacion mes actual vs anterior",
            f"Actual: {format_clp(-comparison['current'])} | Anterior: {format_clp(-comparison['previous'])} | Variacion: {variation_sign}{comparison['variation_pct']:.1f}%",
        )
    with insight_cols[1]:
        projection_df = service.get_projection_by_stable_categories(
            df,
            year=selected_year,
            month=selected_month,
        )
        if projection_df.empty:
            body = "Aun no hay categorias estables suficientes para proyectar."
        else:
            top = projection_df.iloc[0]
            body = f"Categoria mas proyectada: {top['categoria']} ({format_clp(-top['proyeccion'])})."
        render_insight_card("Proyeccion mensual", body)

    if df.empty:
        st.info("No hay movimientos para los filtros seleccionados.")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(category_distribution_chart(df), use_container_width=True)
    with c2:
        st.plotly_chart(category_frequency_chart(df), use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(weekday_chart(df), use_container_width=True)
    with c4:
        st.plotly_chart(monthly_trend_chart(df), use_container_width=True)

    st.plotly_chart(projection_chart(projection_df), use_container_width=True)
