"""Pagina de carga CSV e ingesta confiable."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from services.ingestion_service import IngestionService
from services.ocr_import_service import OcrImportService


MONTH_OPTIONS = [
    (1, "Enero"),
    (2, "Febrero"),
    (3, "Marzo"),
    (4, "Abril"),
    (5, "Mayo"),
    (6, "Junio"),
    (7, "Julio"),
    (8, "Agosto"),
    (9, "Septiembre"),
    (10, "Octubre"),
    (11, "Noviembre"),
    (12, "Diciembre"),
]


def _render_ingestion_result(result) -> None:
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
        st.dataframe(error_df, width="stretch")


def _render_csv_ingestion_tab(session) -> None:
    uploaded = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_ingestion_uploader")
    formats = st.multiselect(
        "Formatos de fecha permitidos",
        options=["%Y-%m-%d", "%Y-%d-%m"],
        default=["%Y-%m-%d", "%Y-%d-%m"],
        key="csv_date_formats",
    )

    if not uploaded:
        st.info("Sube un archivo para iniciar la ingesta CSV.")
        return

    if st.button("Ingerir CSV", type="primary", key="csv_ingest_button"):
        service = IngestionService(session)
        payload = uploaded.getvalue()
        result = service.ingest_csv(
            payload,
            source_label="streamlit_upload",
            date_formats=tuple(formats),
        )
        _render_ingestion_result(result)


def _render_screenshot_ingestion_tab(session) -> None:
    st.caption("Sube pantallazos de movimientos y el OCR los convierte en filas editables antes de importar.")
    ocr_service = OcrImportService()
    if not ocr_service.available:
        st.error(ocr_service.availability_message)
        st.code("pip install rapidocr-onnxruntime", language="bash")
        return

    images = st.file_uploader(
        "Pantallazos de movimientos",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        key="ocr_screenshot_uploader",
    )
    current_date = date.today()
    ctl1, ctl2, ctl3 = st.columns([1.1, 1.1, 1.6])
    with ctl1:
        reference_year = st.number_input(
            "Ano de referencia",
            min_value=2020,
            max_value=2100,
            value=current_date.year,
            step=1,
            key="ocr_reference_year",
        )
    with ctl2:
        month_values = [value for value, _ in MONTH_OPTIONS]
        reference_month = st.selectbox(
            "Mes de referencia",
            options=month_values,
            index=month_values.index(current_date.month),
            format_func=lambda value: dict(MONTH_OPTIONS)[value],
            key="ocr_reference_month",
        )
    with ctl3:
        force_expense = st.checkbox(
            "Forzar todas las filas como gasto",
            value=True,
            key="ocr_force_expense",
            help="Recomendado para tus capturas de tarjeta.",
        )

    process_clicked = st.button(
        "Procesar pantallazos",
        type="primary",
        key="ocr_process_button",
        disabled=not images,
    )

    if process_clicked and images:
        with st.spinner("Leyendo texto de capturas y estructurando movimientos..."):
            extraction = ocr_service.extract_from_images(
                [(image.name, image.getvalue()) for image in images],
                reference_year=int(reference_year),
                reference_month=int(reference_month),
                force_expense=bool(force_expense),
            )
        st.session_state["ocr_preview_rows"] = extraction.rows
        st.session_state["ocr_rejected_rows"] = [
            {
                "origen_imagen": item.image_name,
                "linea_ocr": item.text,
                "razon": item.reason,
                "confianza_ocr": round(float(item.confidence), 3),
            }
            for item in extraction.rejected_lines
        ]
        st.session_state["ocr_summary"] = {
            "images": extraction.total_images,
            "lines": extraction.total_lines,
            "rows": extraction.extracted_rows,
            "avg_confidence": extraction.average_confidence,
        }

    preview_rows = st.session_state.get("ocr_preview_rows", [])
    summary = st.session_state.get("ocr_summary")
    rejected_rows = st.session_state.get("ocr_rejected_rows", [])

    if summary:
        a, b, c, d = st.columns(4)
        a.metric("Capturas", summary["images"])
        b.metric("Lineas OCR", summary["lines"])
        c.metric("Movimientos detectados", summary["rows"])
        d.metric("Confianza media", f"{summary['avg_confidence']:.2f}")

    if not preview_rows:
        st.info("Procesa al menos un pantallazo para previsualizar movimientos.")
        return

    preview_df = pd.DataFrame(preview_rows)
    preview_df = preview_df[
        [
            "fecha",
            "detalle",
            "monto",
            "categoria",
            "nota_usuario",
            "confianza_ocr",
            "origen_imagen",
            "linea_ocr",
            "es_gasto",
        ]
    ].copy()
    edited_df = st.data_editor(
        preview_df,
        width="stretch",
        hide_index=True,
        num_rows="dynamic",
        disabled=["confianza_ocr", "origen_imagen", "linea_ocr", "es_gasto"],
        key="ocr_preview_editor",
        column_config={
            "fecha": st.column_config.TextColumn("Fecha", help="Formato recomendado: YYYY-MM-DD"),
            "detalle": st.column_config.TextColumn("Detalle"),
            "monto": st.column_config.TextColumn("Monto"),
            "categoria": st.column_config.TextColumn("Categoria"),
            "nota_usuario": st.column_config.TextColumn("Nota"),
            "confianza_ocr": st.column_config.NumberColumn("Confianza OCR", format="%.2f"),
            "origen_imagen": st.column_config.TextColumn("Imagen"),
            "linea_ocr": st.column_config.TextColumn("Linea OCR original"),
            "es_gasto": st.column_config.TextColumn("Es gasto"),
        },
    )

    action1, action2 = st.columns([1.5, 1.0])
    with action1:
        if st.button("Importar filas de captura a movimientos", type="primary", key="ocr_ingest_button"):
            payload_df = edited_df.copy()
            for column in ("fecha", "detalle", "monto", "categoria", "nota_usuario"):
                payload_df[column] = payload_df[column].fillna("").astype(str).str.strip()
            payload_df = payload_df[
                (payload_df["fecha"] != "")
                & (payload_df["detalle"] != "")
                & (payload_df["monto"] != "")
            ].copy()
            if payload_df.empty:
                st.warning("No hay filas validas para importar.")
            else:
                payload_df["es_gasto"] = "1" if force_expense else ""
                payload_rows = payload_df[
                    ["fecha", "detalle", "monto", "categoria", "nota_usuario", "es_gasto"]
                ].to_dict(orient="records")
                service = IngestionService(session)
                with st.spinner("Ingestando movimientos en la base de datos..."):
                    result = service.ingest_rows(
                        payload_rows,
                        source_label="screenshot_ocr_upload",
                        date_formats=("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y-%d-%m"),
                    )
                _render_ingestion_result(result)
                if result.imported > 0:
                    st.session_state["ocr_preview_rows"] = []
                    st.session_state["ocr_rejected_rows"] = []
                    st.session_state["ocr_summary"] = None
    with action2:
        if st.button("Limpiar previsualizacion", key="ocr_clear_button"):
            st.session_state["ocr_preview_rows"] = []
            st.session_state["ocr_rejected_rows"] = []
            st.session_state["ocr_summary"] = None
            st.rerun()

    if rejected_rows:
        with st.expander(f"Lineas descartadas ({len(rejected_rows)})", expanded=False):
            st.dataframe(pd.DataFrame(rejected_rows), width="stretch", hide_index=True)


def render_ingestion_page(session) -> None:
    st.title("Carga e ingesta")
    st.caption("Carga CSV robusta + OCR de pantallazos con previsualizacion editable y deduplicacion segura.")
    tab_csv, tab_ocr = st.tabs(["Importar CSV", "Importar pantallazo OCR"])
    with tab_csv:
        _render_csv_ingestion_tab(session)
    with tab_ocr:
        _render_screenshot_ingestion_tab(session)
