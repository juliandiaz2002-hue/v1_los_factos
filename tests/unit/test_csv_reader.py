from utils.csv_reader import parse_csv


def test_parse_csv_detects_delimiter_and_aliases():
    payload = (
        "Fecha;Glosa;Importe;Rubro\n"
        "2026-02-14;Uber Chile;-3990;Transporte\n"
    ).encode("utf-8")

    result = parse_csv(payload)
    assert result.delimiter == ";"
    assert result.encoding == "utf-8"
    assert len(result.rows) == 1
    row = result.rows[0]
    assert row["fecha"] == "2026-02-14"
    assert row["detalle"] == "Uber Chile"
    assert row["monto"] == "-3990"
    assert row["categoria"] == "Transporte"
