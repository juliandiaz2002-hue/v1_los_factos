from datetime import date

from utils.hashing import build_unique_key


def test_build_unique_key_is_deterministic():
    one = build_unique_key(fecha=date(2026, 2, 14), detalle_norm="uber chile", monto_abs_clp=3990)
    two = build_unique_key(fecha=date(2026, 2, 14), detalle_norm="uber chile", monto_abs_clp=3990)
    assert one == two
    assert one.startswith("k:")
