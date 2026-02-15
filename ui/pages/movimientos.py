"""Pagina de tabla editable, guardado masivo y acciones por fila."""

from __future__ import annotations

import html
from datetime import date, datetime

import streamlit as st

from data.repositories.categorias_repo import CategoriaRepository
from services.movements_service import MovementsService
from ui.components import render_filter_chips
from ui.pages.common import render_movement_filters
from utils.category_icons import get_category_icon
from utils.formatting import format_clp, format_date_display


def render_movimientos_page(session) -> None:
    st.title("Movimientos")
    st.caption("Vista simplificada de transacciones con eliminacion segura e iconografia por categoria.")

    category_repo = CategoriaRepository(session)
    categories = category_repo.list_active()
    service = MovementsService(session)

    category_id_by_name = {cat.nombre: int(cat.id) for cat in categories}
    category_names = sorted(category_id_by_name.keys(), key=lambda value: value.lower())

    with st.expander("Registro manual rapido", expanded=False):
        with st.form("manual_movement_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([1, 2, 1])
            with c1:
                manual_date = st.date_input("Fecha", value=date.today())
            with c2:
                manual_detail = st.text_input("Detalle")
            with c3:
                manual_amount = st.number_input("Monto CLP", value=-1000, step=500)

            c4, c5 = st.columns([1, 2])
            with c4:
                manual_category_name = st.selectbox("Categoria", options=list(category_id_by_name.keys()))
            with c5:
                manual_note = st.text_input("Nota (opcional)")

            submitted = st.form_submit_button("Agregar movimiento")
            if submitted:
                unique_key = service.add_manual_entry(
                    fecha=manual_date,
                    detalle=manual_detail,
                    monto_ui=manual_amount,
                    categoria_id=category_id_by_name[manual_category_name],
                    nota_usuario=manual_note,
                )
                st.success(f"Movimiento agregado: {unique_key}")

    with st.expander("Sugerencias de categoria pendientes", expanded=False):
        pending_df = service.list_pending_suggestions(limit=120)
        if pending_df.empty:
            st.caption("No hay sugerencias pendientes.")
        else:
            if "manual_mode_keys" not in st.session_state:
                st.session_state.manual_mode_keys = []
            manual_mode_keys: set[str] = set(st.session_state.manual_mode_keys)
            pending_keys = set(pending_df["unique_key"].astype(str).tolist())
            manual_mode_keys = manual_mode_keys.intersection(pending_keys)
            st.session_state.manual_mode_keys = sorted(manual_mode_keys)

            st.caption(
                "Marca Aceptar para aplicar y sacar de la lista al instante. "
                "Si no te gusta, usa Rechazar y asigna categoria manual por fila."
            )

            resolved_now: set[str] = set()
            success_count = 0
            for row in pending_df.to_dict("records"):
                unique_key = str(row["unique_key"])
                if unique_key in resolved_now:
                    continue

                is_manual_mode = unique_key in manual_mode_keys

                c0, c1, c2, c3, c4, c5 = st.columns([0.8, 3.2, 1.5, 1.6, 1.8, 1.4])
                with c0:
                    accept_checked = st.checkbox(
                        "Aceptar",
                        key=f"accept_suggestion_{unique_key}",
                        value=False,
                        label_visibility="collapsed",
                        help="Aceptar sugerencia",
                    )
                    if accept_checked:
                        if service.resolve_suggestion(unique_key, "ACEPTAR"):
                            success_count += 1
                            resolved_now.add(unique_key)
                            manual_mode_keys.discard(unique_key)
                            st.session_state.manual_mode_keys = sorted(manual_mode_keys)
                            st.session_state.pop(f"accept_suggestion_{unique_key}", None)
                        else:
                            st.error(f"No fue posible aceptar {unique_key}")
                        continue

                with c1:
                    st.markdown(f"**{row['detalle']}**  \n{row['fecha']} | {int(row['monto_ui'])} CLP")
                with c2:
                    st.caption("Sugerida")
                    st.write(row["categoria_sugerida"] or "Sin sugerencia")
                with c3:
                    st.caption("Confianza / Fuente")
                    st.write(f"{row['confianza']:.2f} · {row['fuente_sugerencia']}")

                if not is_manual_mode:
                    with c4:
                        if st.button("Rechazar", key=f"reject_suggestion_{unique_key}"):
                            manual_mode_keys.add(unique_key)
                            st.session_state.manual_mode_keys = sorted(manual_mode_keys)
                            is_manual_mode = True

                if is_manual_mode:
                    with c4:
                        manual_name = st.selectbox(
                            "Categoria manual",
                            options=list(category_id_by_name.keys()),
                            key=f"manual_category_{unique_key}",
                            label_visibility="collapsed",
                        )
                    with c5:
                        if st.button("Guardar manual", key=f"save_manual_{unique_key}"):
                            saved = service.resolve_suggestion(
                                unique_key,
                                "MANUAL",
                                manual_category_id=category_id_by_name[manual_name],
                            )
                            if saved:
                                success_count += 1
                                resolved_now.add(unique_key)
                                manual_mode_keys.discard(unique_key)
                                st.session_state.manual_mode_keys = sorted(manual_mode_keys)
                                st.session_state.pop(f"manual_category_{unique_key}", None)
                            else:
                                st.error(f"No fue posible guardar categoria manual para {unique_key}")
                else:
                    with c5:
                        st.write("")

            if success_count > 0:
                st.success(f"Sugerencias aplicadas: {success_count}")

    filters, active_filters = render_movement_filters(categories, key_prefix="movimientos")
    render_filter_chips(active_filters)

    df = service.list_for_table(filters)
    if df.empty:
        st.info("No hay movimientos para los filtros activos.")
        return

    display_df = df[["fecha", "detalle", "monto_ui", "categoria", "unique_key"]].copy()
    display_df = display_df.sort_values(by=["fecha", "detalle"], ascending=[False, True]).reset_index(drop=True)
    display_df["fecha"] = display_df["fecha"].apply(format_date_display)

    if "pending_delete_key" not in st.session_state:
        st.session_state.pending_delete_key = None
    pending_delete_key = st.session_state.pending_delete_key

    header_left, header_right = st.columns([2.5, 1.2])
    with header_left:
        st.subheader("Transacciones")
        st.caption("Solo nombre, fecha y monto. Usa el icono de categoria para reasignar y el de basura para eliminar.")
    with header_right:
        csv_bytes = service.export_filtered_csv(filters)
        filename = f"movimientos_enriquecido_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        st.download_button(
            "Exportar CSV",
            data=csv_bytes,
            file_name=filename,
            mime="text/csv",
            disabled=(len(csv_bytes) == 0),
            use_container_width=True,
        )

    st.markdown('<div class="lf-movements-wrap">', unsafe_allow_html=True)
    for row in display_df.to_dict("records"):
        unique_key = str(row["unique_key"])
        icon_name, _, _ = get_category_icon(row.get("categoria"))
        detail = html.escape(str(row["detalle"]))
        date_display = str(row["fecha"])
        category_name = str(row.get("categoria") or "Sin categoria")
        category_display = html.escape(category_name)
        amount_value = float(row["monto_ui"])
        amount_display = format_clp(amount_value, signed=True)
        amount_class = "negative" if amount_value < 0 else ""

        c1, c2, c3, c4 = st.columns([0.55, 4.2, 1.35, 0.65])
        with c1:
            with st.popover(
                " ",
                icon=f":material/{icon_name}:",
                help=f"Cambiar categoria (actual: {category_name})",
                use_container_width=True,
            ):
                st.caption(f"Categoria actual: {category_name}")
                selected_category = st.selectbox(
                    "Nueva categoria",
                    options=category_names,
                    index=category_names.index(category_name) if category_name in category_names else 0,
                    key=f"change_category_{unique_key}",
                )
                if st.button(
                    "Guardar categoria",
                    key=f"save_changed_category_{unique_key}",
                    type="primary",
                    use_container_width=True,
                ):
                    if selected_category == category_name:
                        st.info("La categoria ya es la misma.")
                    else:
                        changed = service.reassign_category(unique_key, category_id_by_name[selected_category])
                        if changed:
                            st.success(f"Categoria actualizada a {selected_category}.")
                            st.rerun()
                        st.error("No fue posible cambiar la categoria.")
        with c2:
            st.markdown(
                (
                    f'<div class="lf-mov-detail">{detail}</div>'
                    f'<div class="lf-mov-date">{date_display}</div>'
                    f'<div class="lf-mov-cat">{category_display}</div>'
                ),
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f'<div class="lf-mov-amount {amount_class}">{amount_display}</div>',
                unsafe_allow_html=True,
            )
        with c4:
            if st.button("🗑", key=f"delete_icon_{unique_key}", help="Eliminar movimiento"):
                st.session_state.pending_delete_key = unique_key
                st.rerun()

        if pending_delete_key == unique_key:
            confirm_c1, confirm_c2, confirm_c3 = st.columns([3.2, 1.1, 1.1])
            with confirm_c1:
                st.warning("Estas seguro? Esta accion crea tombstone y bloquea reimportes de este movimiento.")
            with confirm_c2:
                if st.button("Confirmar", key=f"confirm_delete_{unique_key}", type="primary"):
                    deleted = service.delete_one(unique_key)
                    st.session_state.pending_delete_key = None
                    if deleted:
                        st.success("Movimiento eliminado.")
                    else:
                        st.error("No fue posible eliminar el movimiento.")
                    st.rerun()
            with confirm_c3:
                if st.button("Cancelar", key=f"cancel_delete_{unique_key}"):
                    st.session_state.pending_delete_key = None
                    st.rerun()

        st.markdown("<hr style='border:none;border-top:1px solid #F3F4F6;margin:6px 0 2px 0;'>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
