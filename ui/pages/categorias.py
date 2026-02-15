"""Pagina de gestion de categorias."""

from __future__ import annotations

import html

import streamlit as st

from services.categories_service import CategoriesService
from utils.constants import DEFAULT_CATEGORY_NAME
from utils.category_icons import get_category_icon


def render_categorias_page(session) -> None:
    st.title("Categorias")
    st.caption("Gestion visual de categorias con iconografia, renombrado rapido y eliminacion segura.")

    service = CategoriesService(session)
    categories = service.list_active()

    categories = sorted(categories, key=lambda c: str(c.nombre).lower())
    total_active = len(categories)
    protected = [c for c in categories if str(c.nombre) == DEFAULT_CATEGORY_NAME]
    deletable = [c for c in categories if str(c.nombre) != DEFAULT_CATEGORY_NAME]

    stats1, stats2, stats3 = st.columns(3)
    with stats1:
        st.markdown(
            f"""
<div class="lf-cat-stat">
  <div class="label">Categorias activas</div>
  <div class="value">{total_active}</div>
</div>
            """,
            unsafe_allow_html=True,
        )
    with stats2:
        st.markdown(
            f"""
<div class="lf-cat-stat">
  <div class="label">Editables / eliminables</div>
  <div class="value">{len(deletable)}</div>
</div>
            """,
            unsafe_allow_html=True,
        )
    with stats3:
        default_name = html.escape(protected[0].nombre) if protected else DEFAULT_CATEGORY_NAME
        st.markdown(
            f"""
<div class="lf-cat-stat">
  <div class="label">Categoria base protegida</div>
  <div class="value compact">{default_name}</div>
</div>
            """,
            unsafe_allow_html=True,
        )

    with st.container(border=True):
        st.markdown('<div class="lf-cat-form-title">Nueva categoria</div>', unsafe_allow_html=True)
        with st.form("add_category_form", clear_on_submit=True):
            in1, in2 = st.columns([3.2, 1.0])
            with in1:
                new_name = st.text_input("Nombre de categoria")
            with in2:
                submitted = st.form_submit_button("Agregar", use_container_width=True, type="primary")
            if submitted:
                clean_name = (new_name or "").strip()
                if not clean_name:
                    st.warning("Ingresa un nombre valido.")
                else:
                    service.add(clean_name)
                    session.commit()
                    st.success(f"Categoria creada: {clean_name}")
                    st.rerun()

    st.subheader("Listado de categorias")
    st.caption("Icono + nombre + acciones por fila. Eliminar reasigna movimientos a Sin categoria.")

    if not categories:
        st.info("No hay categorias activas.")
        return

    st.markdown('<div class="lf-cat-list-wrap">', unsafe_allow_html=True)
    for category in categories:
        category_name = str(category.nombre)
        category_safe = html.escape(category_name)
        is_default = category_name == DEFAULT_CATEGORY_NAME
        icon_name, icon_color, icon_bg = get_category_icon(category_name)

        row1, row2, row3, row4 = st.columns([0.65, 3.2, 1.4, 1.4])
        with row1:
            st.markdown(
                (
                    f'<div class="lf-cat-icon" style="border-color:{icon_color}40;background:{icon_bg};">'
                    f'<span class="icon" style="color:{icon_color};">{icon_name}</span>'
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
        with row2:
            badge = (
                '<span class="lf-cat-badge lf-cat-badge-protected">Protegida</span>'
                if is_default
                else '<span class="lf-cat-badge">Activa</span>'
            )
            st.markdown(
                (
                    f'<div class="lf-cat-name">{category_safe}</div>'
                    f'<div class="lf-cat-meta">{badge}</div>'
                ),
                unsafe_allow_html=True,
            )
        with row3:
            with st.popover("Renombrar", icon=":material/edit:", use_container_width=True):
                new_label = st.text_input(
                    "Nuevo nombre",
                    value=category_name,
                    key=f"cat_rename_{category.id}",
                )
                if st.button(
                    "Guardar nombre",
                    key=f"cat_rename_btn_{category.id}",
                    type="primary",
                    use_container_width=True,
                ):
                    clean_new = (new_label or "").strip()
                    if not clean_new:
                        st.warning("Ingresa un nombre valido.")
                    elif clean_new == category_name:
                        st.info("No hay cambios en el nombre.")
                    else:
                        service.rename(int(category.id), clean_new)
                        session.commit()
                        st.success("Categoria renombrada.")
                        st.rerun()
        with row4:
            if is_default:
                st.caption("No eliminable")
            else:
                with st.popover("Eliminar", icon=":material/delete:", use_container_width=True):
                    st.warning(f"Se reasignaran movimientos a {DEFAULT_CATEGORY_NAME}.")
                    confirm = st.checkbox("Confirmo eliminacion", key=f"cat_delete_confirm_{category.id}")
                    if st.button(
                        "Eliminar categoria",
                        key=f"cat_delete_btn_{category.id}",
                        type="primary",
                        use_container_width=True,
                    ):
                        if not confirm:
                            st.warning("Debes confirmar antes de eliminar.")
                        else:
                            service.delete(int(category.id))
                            session.commit()
                            st.success("Categoria eliminada y movimientos reasignados.")
                            st.rerun()

        st.markdown("<hr style='border:none;border-top:1px solid #F3F4F6;margin:8px 0 4px 0;'>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
