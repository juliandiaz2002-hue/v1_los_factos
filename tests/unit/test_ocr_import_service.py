from services.ocr_import_service import OcrCandidateLine, parse_candidate_lines


def test_parse_candidate_lines_extracts_transactions_and_deduplicates():
    lines = [
        OcrCandidateLine(
            text="13-02 APP COPEC BIP3 $750",
            confidence=0.98,
            image_name="cap_1.png",
            order_index=1,
        ),
        OcrCandidateLine(
            text="13-02 APP COPEC BIP3 $750",
            confidence=0.91,
            image_name="cap_1.png",
            order_index=2,
        ),
    ]

    rows, rejected = parse_candidate_lines(
        lines,
        reference_year=2026,
        reference_month=2,
        force_expense=True,
    )

    assert len(rows) == 1
    assert len(rejected) == 0
    row = rows[0]
    assert row["fecha"] == "2026-02-13"
    assert row["detalle"] == "APP COPEC BIP3"
    assert row["monto"] == "-750"
    assert row["es_gasto"] == "1"


def test_parse_candidate_lines_supports_month_name():
    lines = [
        OcrCandidateLine(
            text="14 feb Uber Trip Chile $3.990",
            confidence=0.95,
            image_name="cap_2.png",
            order_index=1,
        )
    ]

    rows, rejected = parse_candidate_lines(
        lines,
        reference_year=2026,
        reference_month=2,
        force_expense=True,
    )

    assert len(rows) == 1
    assert len(rejected) == 0
    row = rows[0]
    assert row["fecha"] == "2026-02-14"
    assert row["detalle"] == "Uber Trip Chile"
    assert row["monto"] == "-3.990"


def test_parse_candidate_lines_deduplicates_similar_details_same_date_amount():
    lines = [
        OcrCandidateLine(
            text="13-02 APP COPEC BIP3 $750",
            confidence=0.70,
            image_name="cap_4.png",
            order_index=1,
        ),
        OcrCandidateLine(
            text="13-02 APP COPEC BIP $750",
            confidence=0.93,
            image_name="cap_5.png",
            order_index=1,
        ),
    ]

    rows, rejected = parse_candidate_lines(
        lines,
        reference_year=2026,
        reference_month=2,
        force_expense=True,
    )

    assert len(rows) == 1
    assert len(rejected) == 0
    row = rows[0]
    assert row["fecha"] == "2026-02-13"
    assert row["monto"] == "-750"
    assert row["confianza_ocr"] == 0.93


def test_parse_candidate_lines_rejects_noise_and_missing_amount():
    lines = [
        OcrCandidateLine(
            text="Saldo disponible $ 1.200.000",
            confidence=0.88,
            image_name="cap_3.png",
            order_index=1,
        ),
        OcrCandidateLine(
            text="15-02 Transferencia enviada",
            confidence=0.80,
            image_name="cap_3.png",
            order_index=2,
        ),
    ]

    rows, rejected = parse_candidate_lines(
        lines,
        reference_year=2026,
        reference_month=2,
        force_expense=True,
    )

    assert len(rows) == 0
    assert len(rejected) == 2
    reasons = {item.reason for item in rejected}
    assert "linea_descartada_por_ruido" in reasons
    assert "monto_no_detectado" in reasons


def test_parse_candidate_lines_rejects_truncated_amount_without_explicit_date():
    lines = [
        OcrCandidateLine(
            text="21/02/2026 MERCADOPAGO*SAL -$800",
            confidence=0.99,
            image_name="cap_6.png",
            order_index=1,
        ),
        OcrCandidateLine(
            text="MERCADOPAGO*SAL 008$-",
            confidence=0.98,
            image_name="cap_6.png",
            order_index=2,
        ),
    ]

    rows, rejected = parse_candidate_lines(
        lines,
        reference_year=2026,
        reference_month=2,
        force_expense=True,
    )

    assert len(rows) == 1
    assert rows[0]["detalle"] == "MERCADOPAGO*SAL"
    assert rows[0]["monto"] == "-800"
    reasons = {item.reason for item in rejected}
    assert "monto_sospechoso_ocr" in reasons


def test_parse_candidate_lines_prefers_explicit_date_when_duplicate_with_same_amount():
    lines = [
        OcrCandidateLine(
            text="19/02/2026 UNIMARC LAS TRANQUERAS -$18.829",
            confidence=0.82,
            image_name="cap_7.png",
            order_index=1,
        ),
        OcrCandidateLine(
            text="R UNIMARCLAS TRANQUERAS -$18.829",
            confidence=0.99,
            image_name="cap_7.png",
            order_index=2,
        ),
    ]

    rows, rejected = parse_candidate_lines(
        lines,
        reference_year=2026,
        reference_month=2,
        force_expense=True,
    )

    assert len(rows) == 1
    assert rows[0]["fecha"] == "2026-02-19"
    assert rows[0]["monto"] == "-18.829"
    assert not rows[0]["detalle"].startswith("R ")
    reasons = {item.reason for item in rejected}
    assert "fila_probable_duplicada_ocr" in reasons
