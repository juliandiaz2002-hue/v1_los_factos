"""Pagina de gestion de categorias."""

from __future__ import annotations

import streamlit as st

from services.categories_service import CategoriesService
from utils.constants import DEFAULT_CATEGORY_NAME


def render_categorias_page(session) -> None:
    st.title("Categorias")
    st.caption("Agregar, renombrar, eliminar (reasignando a Sin categoria)")

    service = CategoriesService(session)
    categories = service.list_active()

    st.subheader("Listado")
    st.dataframe(
        [{"id": c.id, "nombre": c.nombre, "activa": c.activa} for c in categories],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Agregar categoria")
    with st.form("add_category_form"):
        new_name = st.text_input("Nombre")
        submitted = st.form_submit_button("Agregar")
        if submitted:
            service.add(new_name)
            st.success("Categoria creada")

    st.subheader("Renombrar categoria")
    rename_options = {int(c.id): c.nombre for c in categories}
    with st.form("rename_category_form"):
        category_id = st.selectbox("Categoria", options=list(rename_options.keys()), format_func=lambda x: rename_options[x])
        renamed = st.text_input("Nuevo nombre")
        submitted = st.form_submit_button("Renombrar")
        if submitted:
            service.rename(category_id, renamed)
            st.success("Categoria renombrada")

    st.subheader("Eliminar categoria")
    delete_options = {
        int(c.id): c.nombre
        for c in categories
        if c.nombre != DEFAULT_CATEGORY_NAME
    }
    if not delete_options:
        st.info("No hay categorias eliminables.")
        return

    with st.form("delete_category_form"):
        category_id = st.selectbox("Categoria a eliminar", options=list(delete_options.keys()), format_func=lambda x: delete_options[x])
        confirm = st.checkbox("Confirmo que quiero reasignar sus movimientos a Sin categoria")
        submitted = st.form_submit_button("Eliminar")
        if submitted and confirm:
            service.delete(category_id)
            st.success("Categoria eliminada y movimientos reasignados")
        elif submitted:
            st.warning("Debes confirmar para eliminar")
