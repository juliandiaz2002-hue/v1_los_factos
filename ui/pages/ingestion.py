"""Pagina de carga CSV e ingesta confiable."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from services.ingestion_service import IngestionService


def render_ingestion_page(session) -> None:
    st.title("Carga e ingesta")
    st.caption("Carga CSV robusta: encoding, delimitador, aliases, deduplicacion y tombstones")

    uploaded = st.file_uploader("Selecciona CSV", type=["csv"])
    formats = st.multiselect(
        "Formatos de fecha permitidos",
        options=["%Y-%m-%d", "%Y-%d-%m"],
        default=["%Y-%m-%d", "%Y-%d-%m"],
    )

    if not uploaded:
        st.info("Sube un archivo para iniciar la ingesta.")
        return

    if st.button("Ingerir archivo", type="primary"):
        service = IngestionService(session)
        payload = uploaded.getvalue()
        result = service.ingest_csv(
            payload,
            source_label="streamlit_upload",
            date_formats=tuple(formats),
        )

        st.success("Ingesta finalizada")
        a, b, c, d = st.columns(4)
        a.metric("Total filas", result.total_rows)
        b.metric("Importadas", result.imported)
        c.metric("Duplicadas", result.duplicated)
        d.metric("Tombstones", result.tombstoned)

        st.caption(f"Encoding detectado: {result.encoding} | Delimitador detectado: {repr(result.delimiter)}")

        if result.errors:
            st.warning(f"Se registraron {len(result.errors)} errores de fila")
            error_df = pd.DataFrame(
                [
                    {
                        "fila": e.row_number,
                        "mensaje": e.message,
                        "payload": str(e.payload),
                    }
                    for e in result.errors
                ]
            )
            st.dataframe(error_df, use_container_width=True)
