"""Pagina de mantenimiento y confiabilidad."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from services.maintenance_service import MaintenanceService


def render_mantenimiento_page(session) -> None:
    st.title("Mantenimiento")
    st.caption("Diagnostico de base, reparaciones y backup completo")

    service = MaintenanceService(session)

    st.subheader("Diagnostico")
    diag = service.diagnostics()
    cols = st.columns(len(diag))
    for idx, (name, value) in enumerate(diag.items()):
        cols[idx].metric(name, value)

    st.subheader("Reparar montos inconsistentes")
    if st.button("Ejecutar reparacion de montos"):
        repaired = service.repair_inconsistent_amounts()
        st.success(f"Montos reparados: {repaired}")

    st.subheader("Reincorporar ignorados")
    ignored = service.list_ignored()
    if not ignored:
        st.info("No hay movimientos ignorados activos.")
    else:
        options = {item.unique_key: item.reason or "(sin motivo)" for item in ignored}
        selected = st.multiselect("Selecciona unique_key a reincorporar", options=list(options.keys()))
        if st.button("Reincorporar seleccionados"):
            restored = sum(1 for key in selected if service.restore_ignored(key))
            st.success(f"Reincorporados: {restored}")

    st.subheader("Backup completo")
    backup_bytes = service.export_full_backup()
    backup_name = f"los_factos_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    st.download_button(
        "Descargar backup completo",
        data=backup_bytes,
        file_name=backup_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
