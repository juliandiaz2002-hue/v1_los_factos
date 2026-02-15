from utils.category_icons import get_category_icon


def test_known_categories_get_specific_icons():
    assert get_category_icon("Transporte")[0] == "commute"
    assert get_category_icon("Café")[0] == "local_cafe"
    assert get_category_icon("Sin categoría")[0] == "help"
    assert get_category_icon("Transferencias")[0] == "swap_horiz"


def test_unknown_category_fallback_is_deterministic():
    icon_a = get_category_icon("Categoria Ultra Especial")
    icon_b = get_category_icon("Categoria Ultra Especial")
    assert icon_a == icon_b
    assert len(icon_a) == 3
    assert icon_a[1].startswith("#")
    assert icon_a[2].startswith("#")
