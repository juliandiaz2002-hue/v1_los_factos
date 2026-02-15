"""Pagina de tabla editable, guardado masivo y acciones por fila."""

from __future__ import annotations

import hashlib
import html
from datetime import date, datetime
import time

import streamlit as st

from data.repositories.categorias_repo import CategoriaRepository
from services.movements_service import MovementFilters, MovementsService
from ui.components import render_filter_chips
from ui.pages.common import render_movement_filters
from utils.category_icons import get_category_icon
from utils.formatting import format_clp, format_date_display


def _filters_from_session_state(key_prefix: str) -> MovementFilters:
    current_date = date.today()
    text_filter = (str(st.session_state.get(f"{key_prefix}_text", "")).strip() or None)

    month_raw = st.session_state.get(f"{key_prefix}_month", current_date.month)
    month = int(month_raw) if month_raw not in {None, "", 0} else None

    year_raw = st.session_state.get(f"{key_prefix}_year", current_date.year)
    year = int(year_raw) if year_raw not in {None, "", 0} else None

    category_raw = st.session_state.get(f"{key_prefix}_cat", 0)
    category_id = int(category_raw) if category_raw not in {None, "", 0} else None

    date_range = st.session_state.get(f"{key_prefix}_range", ())
    date_from = None
    date_to = None
    if isinstance(date_range, tuple) and len(date_range) == 2:
        date_from, date_to = date_range

    return MovementFilters(
        text_filter=text_filter,
        month=month,
        year=year,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
    )


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
        controls_left, controls_right = st.columns([3.0, 1.2])
        with controls_left:
            st.caption(
                "Marca Aceptar para aplicar y sacar de la lista al instante. "
                "Si no te gusta, usa Rechazar y asigna categoria manual por fila."
            )
        with controls_right:
            refresh_backfill = st.button(
                "Actualizar sugerencias",
                key="refresh_pending_suggestions",
                icon=":material/refresh:",
                width="stretch",
            )

        backfill_state_key = "last_suggestion_backfill_ts"
        now_ts = float(time.time())
        last_backfill_ts = float(st.session_state.get(backfill_state_key, 0.0) or 0.0)
        should_backfill = refresh_backfill or (now_ts - last_backfill_ts) >= 90.0
        if should_backfill:
            updated_backfill = service.ensure_suggestions_for_uncategorized(limit=1500, batch_size=300)
            st.session_state[backfill_state_key] = now_ts
            if updated_backfill > 0:
                st.caption(f"Recomendaciones recalculadas para {updated_backfill} movimientos sin categoria.")

        pending_df = service.list_pending_suggestions(limit=120, ensure_backfill=False)
        if pending_df.empty:
            st.caption("No hay sugerencias pendientes.")
        else:
            if "manual_mode_keys" not in st.session_state:
                st.session_state.manual_mode_keys = []
            manual_mode_keys: set[str] = set(st.session_state.manual_mode_keys)
            pending_keys = set(pending_df["unique_key"].astype(str).tolist())
            manual_mode_keys = manual_mode_keys.intersection(pending_keys)
            st.session_state.manual_mode_keys = sorted(manual_mode_keys)

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

    probable_filters = _filters_from_session_state("movimientos")

    with st.expander("Probables duplicados", expanded=False):
        st.caption(
            "Alerta flexible: agrupa transacciones con mismo monto para revisar posibles duplicados "
            "y detecta montos pequenos sospechosos."
        )
        suspicious_threshold = int(
            st.number_input(
                "Umbral de monto sospechoso (< CLP)",
                min_value=100,
                max_value=5000,
                value=500,
                step=50,
                key="probable_duplicate_threshold",
            )
        )

        duplicate_pairs_df = service.list_probable_duplicate_pairs(probable_filters, limit_pairs=60)
        suspicious_df = service.list_suspicious_small_amounts(
            probable_filters,
            threshold_abs_clp=suspicious_threshold,
            limit_rows=80,
        )

        if "dismissed_probable_pairs" not in st.session_state:
            st.session_state.dismissed_probable_pairs = []
        if "dismissed_suspicious_keys" not in st.session_state:
            st.session_state.dismissed_suspicious_keys = []

        dismissed_pairs: set[str] = set(st.session_state.dismissed_probable_pairs)
        dismissed_suspicious: set[str] = set(st.session_state.dismissed_suspicious_keys)

        if not duplicate_pairs_df.empty:
            duplicate_pairs_df = duplicate_pairs_df[
                ~duplicate_pairs_df["pair_id"].astype(str).isin(dismissed_pairs)
            ].copy()
        if not suspicious_df.empty:
            suspicious_df = suspicious_df[
                ~suspicious_df["unique_key"].astype(str).isin(dismissed_suspicious)
            ].copy()

        if duplicate_pairs_df.empty and suspicious_df.empty:
            st.caption("No se detectaron candidatos en los filtros activos.")
        else:
            if not duplicate_pairs_df.empty:
                st.markdown("**Posibles duplicados (mismo monto)**")
                for item in duplicate_pairs_df.to_dict("records"):
                    pair_id = str(item["pair_id"])
                    pair_hash = hashlib.md5(pair_id.encode("utf-8")).hexdigest()[:12]
                    left_key = str(item["left_unique_key"])
                    right_key = str(item["right_unique_key"])
                    left_amount = format_clp(float(item["left_monto_ui"]), signed=True)
                    right_amount = format_clp(float(item["right_monto_ui"]), signed=True)

                    c1, c2, c3, c4, c5 = st.columns([2.8, 2.8, 1.2, 1.2, 1.2])
                    with c1:
                        st.markdown(
                            f"**A:** {item['left_detalle']}  \n{item['left_fecha']} | {left_amount}"
                        )
                    with c2:
                        st.markdown(
                            f"**B:** {item['right_detalle']}  \n{item['right_fecha']} | {right_amount}"
                        )
                    with c3:
                        if st.button("Mantener", key=f"keep_pair_{pair_hash}"):
                            dismissed_pairs.add(pair_id)
                            st.session_state.dismissed_probable_pairs = sorted(dismissed_pairs)
                            st.rerun()
                    with c4:
                        if st.button("Eliminar A", key=f"delete_pair_a_{pair_hash}"):
                            deleted = service.delete_one(left_key, reason="probable_duplicate")
                            if deleted:
                                session.commit()
                                dismissed_pairs.add(pair_id)
                                dismissed_suspicious.add(left_key)
                                st.session_state.dismissed_probable_pairs = sorted(dismissed_pairs)
                                st.session_state.dismissed_suspicious_keys = sorted(dismissed_suspicious)
                                st.success("Transaccion A eliminada.")
                            else:
                                st.error("No fue posible eliminar la transaccion A.")
                            st.rerun()
                    with c5:
                        if st.button("Eliminar B", key=f"delete_pair_b_{pair_hash}"):
                            deleted = service.delete_one(right_key, reason="probable_duplicate")
                            if deleted:
                                session.commit()
                                dismissed_pairs.add(pair_id)
                                dismissed_suspicious.add(right_key)
                                st.session_state.dismissed_probable_pairs = sorted(dismissed_pairs)
                                st.session_state.dismissed_suspicious_keys = sorted(dismissed_suspicious)
                                st.success("Transaccion B eliminada.")
                            else:
                                st.error("No fue posible eliminar la transaccion B.")
                            st.rerun()

                    st.caption(
                        f"Similitud detalle: {float(item['similarity_score']):.2f} | "
                        f"Dias de diferencia: {int(item['days_diff'])}"
                    )
                    st.markdown(
                        "<hr style='border:none;border-top:1px solid #F3F4F6;margin:6px 0 4px 0;'>",
                        unsafe_allow_html=True,
                    )

            if not suspicious_df.empty:
                st.markdown("**Montos sospechosos**")
                for item in suspicious_df.to_dict("records"):
                    unique_key = str(item["unique_key"])
                    amount_display = format_clp(float(item["monto_ui"]), signed=True)

                    c1, c2, c3 = st.columns([4.2, 1.2, 1.2])
                    with c1:
                        st.markdown(
                            f"**{item['detalle']}**  \n{item['fecha']} | {amount_display} | {item['categoria']}"
                        )
                    with c2:
                        if st.button("Mantener", key=f"keep_small_{unique_key}"):
                            dismissed_suspicious.add(unique_key)
                            st.session_state.dismissed_suspicious_keys = sorted(dismissed_suspicious)
                            st.rerun()
                    with c3:
                        if st.button("Eliminar", key=f"delete_small_{unique_key}"):
                            deleted = service.delete_one(unique_key, reason="suspicious_small_amount")
                            if deleted:
                                session.commit()
                                dismissed_suspicious.add(unique_key)
                                st.session_state.dismissed_suspicious_keys = sorted(dismissed_suspicious)
                                st.success("Transaccion sospechosa eliminada.")
                            else:
                                st.error("No fue posible eliminar la transaccion.")
                            st.rerun()

                    st.markdown(
                        "<hr style='border:none;border-top:1px solid #F3F4F6;margin:6px 0 4px 0;'>",
                        unsafe_allow_html=True,
                    )

    with st.expander("Filtros", expanded=False):
        filters, active_filters = render_movement_filters(
            categories,
            key_prefix="movimientos",
            show_title=False,
            compact=True,
            show_date_range=False,
        )
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
            width="stretch",
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
                width="stretch",
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
                    width="stretch",
                ):
                    if selected_category == category_name:
                        st.info("La categoria ya es la misma.")
                    else:
                        changed = service.reassign_category(unique_key, category_id_by_name[selected_category])
                        if changed:
                            session.commit()
                            st.success(f"Categoria actualizada a {selected_category}.")
                            st.rerun()
                        else:
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
                        session.commit()
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
