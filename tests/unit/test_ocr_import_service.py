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
