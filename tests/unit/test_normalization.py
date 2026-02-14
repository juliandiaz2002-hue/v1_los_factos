from utils.normalization import normalize_text, parse_amount, parse_date


def test_normalize_text_accents_and_spaces():
    assert normalize_text("  APP COPEC BIP\u00b3  ") == "app copec bip3"


def test_parse_amount_negative_is_expense():
    amount, movement_type = parse_amount("-79.305")
    assert amount == 79305
    assert movement_type == "GASTO"


def test_parse_amount_positive_is_income():
    amount, movement_type = parse_amount("12000")
    assert amount == 12000
    assert movement_type == "INGRESO"


def test_parse_date_formats():
    assert str(parse_date("2026-02-14", ["%Y-%m-%d"])) == "2026-02-14"
    assert str(parse_date("2026-14-02", ["%Y-%d-%m"])) == "2026-02-14"
