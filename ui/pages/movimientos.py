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
        st.dataframe(pending_df, use_container_width=True, hide_index=True)

        suggestion_keys = pending_df["unique_key"].astype(str).tolist()
        selected_key = st.selectbox("Selecciona una sugerencia", options=suggestion_keys)
        selected_row = pending_df[pending_df["unique_key"] == selected_key].iloc[0]
        st.caption(
            f"Sugerida: {selected_row['categoria_sugerida']} | Fuente: {selected_row['fuente_sugerencia']} | Confianza: {selected_row['confianza']:.2f}"
        )

        manual_category = st.selectbox(
            "Categoria manual",
            options=list(category_id_by_name.keys()),
            key="suggestion_manual_category",
        )

        a, b, c = st.columns(3)
        with a:
            if st.button("Aceptar sugerencia", key="accept_suggestion_btn"):
                service.resolve_suggestion(selected_key, "ACEPTAR")
                st.success("Sugerencia aceptada")
        with b:
            if st.button("Rechazar sugerencia", key="reject_suggestion_btn"):
                service.resolve_suggestion(selected_key, "RECHAZAR")
                st.success("Sugerencia rechazada")
        with c:
            if st.button("Aplicar categoria manual", key="manual_suggestion_btn"):
                service.resolve_suggestion(
                    selected_key,
                    "MANUAL",
                    manual_category_id=category_id_by_name[manual_category],
                )
                st.success("Sugerencia resuelta manualmente")

    filters, active_filters = render_movement_filters(categories, key_prefix="movimientos")
    render_filter_chips(active_filters)

    df = service.list_for_table(filters)
    if df.empty:
        st.info("No hay movimientos para los filtros activos.")
        return

    editable_df = df[["id", "fecha", "detalle", "monto_ui", "categoria_id", "categoria", "nota_usuario", "unique_key"]].copy()
    editable_df["categoria"] = editable_df["categoria_id"].map(category_name_by_id)

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
        },
        key="movimientos_data_editor",
    )

    edited_records = edited.to_dict("records")
    original_by_id = {int(row["id"]): row for row in editable_df.to_dict("records")}
    updates = []

    for row in edited_records:
        rid = int(row["id"])
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
        if st.button("Guardar cambios", type="primary"):
            count = service.bulk_save(updates)
            st.success(f"Registros actualizados: {count}")

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
    selected_for_delete = st.multiselect("Selecciona movimientos a eliminar (tombstone)", options=keys)
    if st.button("Eliminar seleccionados"):
        done = sum(1 for k in selected_for_delete if service.delete_one(k))
        st.success(f"Movimientos marcados como borrados: {done}")

    selected_for_ignore = st.multiselect("Selecciona movimientos a ignorar", options=keys)
    if st.button("Ignorar seleccionados"):
        done = sum(1 for k in selected_for_ignore if service.ignore_one(k))
        st.success(f"Movimientos ignorados: {done}")
