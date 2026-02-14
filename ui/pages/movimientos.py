"""Pagina de tabla editable, guardado masivo y acciones por fila."""

from __future__ import annotations

from datetime import date, datetime

import streamlit as st

from data.repositories.categorias_repo import CategoriaRepository
from services.movements_service import MovementsService
from ui.components import render_filter_chips
from ui.pages.common import render_movement_filters


def render_movimientos_page(session) -> None:
    st.title("Movimientos")
    st.caption("Registro manual, sugerencias, edicion masiva, tombstones e ignorados")

    category_repo = CategoriaRepository(session)
    categories = category_repo.list_active()
    service = MovementsService(session)

    category_name_by_id = {int(cat.id): cat.nombre for cat in categories}
    category_id_by_name = {name: cid for cid, name in category_name_by_id.items()}

    st.subheader("Registro manual rapido")
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

    st.subheader("Sugerencias de categoria pendientes")
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

    editable_df = df[["id", "fecha", "detalle", "monto_ui", "categoria_id", "categoria", "nota_usuario", "unique_key"]].copy()
    editable_df["categoria"] = editable_df["categoria_id"].map(category_name_by_id)
    editable_df["eliminar"] = False
    st.caption("Puedes editar monto/categoria/nota y marcar `eliminar` para crear tombstone por fila.")

    edited = st.data_editor(
        editable_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn(disabled=True),
            "fecha": st.column_config.DateColumn("Fecha", disabled=True),
            "detalle": st.column_config.TextColumn("Detalle", disabled=True),
            "monto_ui": st.column_config.NumberColumn("Monto CLP"),
            "categoria": st.column_config.SelectboxColumn("Categoria", options=list(category_id_by_name.keys())),
            "categoria_id": st.column_config.NumberColumn("Categoria ID", disabled=True),
            "nota_usuario": st.column_config.TextColumn("Nota"),
            "unique_key": st.column_config.TextColumn("Unique key", disabled=True),
            "eliminar": st.column_config.CheckboxColumn("Eliminar"),
        },
        key="movimientos_data_editor",
    )

    edited_records = edited.to_dict("records")
    original_by_id = {int(row["id"]): row for row in editable_df.to_dict("records")}
    updates = []
    delete_keys: list[str] = []

    for row in edited_records:
        rid = int(row["id"])
        if bool(row.get("eliminar")):
            delete_keys.append(str(row["unique_key"]))
            continue

        original = original_by_id[rid]
        if (
            row["monto_ui"] != original["monto_ui"]
            or row["categoria"] != original["categoria"]
            or (row.get("nota_usuario") or "") != (original.get("nota_usuario") or "")
        ):
            updates.append(
                {
                    "id": rid,
                    "monto_ui": row["monto_ui"],
                    "categoria_id": category_id_by_name[row["categoria"]],
                    "nota_usuario": row.get("nota_usuario"),
                }
            )

    col_save, col_dl = st.columns([1, 1])
    with col_save:
        if st.button("Aplicar cambios", type="primary", disabled=(len(updates) == 0 and len(delete_keys) == 0)):
            updated_count = service.bulk_save(updates) if updates else 0
            deleted_count = sum(1 for key in delete_keys if service.delete_one(key))
            st.success(f"Actualizados: {updated_count} | Eliminados (tombstone): {deleted_count}")

    with col_dl:
        csv_bytes = service.export_filtered_csv(filters)
        filename = f"movimientos_enriquecido_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        st.download_button(
            "Descargar CSV enriquecido",
            data=csv_bytes,
            file_name=filename,
            mime="text/csv",
            disabled=(len(csv_bytes) == 0),
        )

    keys = list(df["unique_key"].astype(str).tolist())
    selected_for_ignore = st.multiselect("Selecciona movimientos a ignorar", options=keys)
    if st.button("Ignorar seleccionados"):
        done = sum(1 for k in selected_for_ignore if service.ignore_one(k))
        st.success(f"Movimientos ignorados: {done}")
