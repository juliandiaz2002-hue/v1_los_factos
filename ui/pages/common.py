"""Componentes compartidos entre paginas."""

from __future__ import annotations

from datetime import date

import streamlit as st

from services.movements_service import MovementFilters

MONTH_NAMES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


def render_movement_filters(
    categories,
    *,
    key_prefix: str,
    show_title: bool = True,
    compact: bool = False,
    show_date_range: bool = True,
) -> tuple[MovementFilters, list[str]]:
    if show_title:
        st.subheader("Filtros")
    col1, col2, col3, col4 = st.columns([2.2, 1.1, 1.1, 1.5] if compact else [1.6, 1, 1, 1.2])

    with col1:
        text_filter = st.text_input(
            "Buscar texto",
            key=f"{key_prefix}_text",
            placeholder="Buscar transaccion...",
            label_visibility="collapsed" if compact else "visible",
        )

    with col2:
        current_month = date.today().month
        month_options = [0] + list(range(1, 13))
        month_choice = st.selectbox(
            "Mes",
            options=month_options,
            index=month_options.index(current_month),
            format_func=lambda value: "Todos" if value == 0 else MONTH_NAMES[value],
            key=f"{key_prefix}_month",
            label_visibility="collapsed" if compact else "visible",
        )

    with col3:
        current_year = date.today().year
        year_choice = st.selectbox(
            "Ano",
            options=[0, current_year - 1, current_year, current_year + 1],
            index=2,
            format_func=lambda value: "Todos" if value == 0 else str(value),
            key=f"{key_prefix}_year",
            label_visibility="collapsed" if compact else "visible",
        )

    with col4:
        category_options = {0: "Todas"}
        for cat in categories:
            category_options[int(cat.id)] = cat.nombre
        category_id = st.selectbox(
            "Categoria",
            options=list(category_options.keys()),
            format_func=lambda value: category_options[value],
            key=f"{key_prefix}_cat",
            label_visibility="collapsed" if compact else "visible",
        )

    if show_date_range:
        date_range = st.date_input(
            "Rango de fechas",
            value=(),
            key=f"{key_prefix}_range",
        )
    else:
        date_range = ()

    date_from = None
    date_to = None
    if isinstance(date_range, tuple) and len(date_range) == 2:
        date_from, date_to = date_range

    filters = MovementFilters(
        text_filter=(text_filter.strip() or None),
        month=month_choice or None,
        year=year_choice or None,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id or None,
    )

    labels: list[str] = []
    if filters.text_filter:
        labels.append(f"Texto: {filters.text_filter}")
    if filters.month:
        labels.append(f"Mes: {MONTH_NAMES[filters.month]}")
    if filters.year:
        labels.append(f"Ano: {filters.year}")
    if filters.category_id:
        labels.append(f"Categoria: {category_options[filters.category_id]}")
    if filters.date_from and filters.date_to:
        labels.append(f"Fechas: {filters.date_from} a {filters.date_to}")

    return filters, labels
