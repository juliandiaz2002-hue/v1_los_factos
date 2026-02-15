"""Iconografia para categorias de gasto."""

from __future__ import annotations

import hashlib

from utils.normalization import normalize_text

CategoryIcon = tuple[str, str, str]

DEFAULT_ICON: CategoryIcon = ("receipt_long", "#64748B", "#F8FAFC")

EXACT_ICON_MAP: dict[str, CategoryIcon] = {
    "almuerzo": ("lunch_dining", "#EA580C", "#FFF7ED"),
    "ano nuevo": ("celebration", "#7C3AED", "#F3E8FF"),
    "arriendo": ("home", "#0EA5E9", "#E0F2FE"),
    "cafe": ("local_cafe", "#92400E", "#FEF3C7"),
    "carrete": ("nightlife", "#DB2777", "#FCE7F3"),
    "desayuno": ("breakfast_dining", "#F59E0B", "#FFFBEB"),
    "educacion": ("school", "#2563EB", "#DBEAFE"),
    "entretenimiento": ("stadia_controller", "#DB2777", "#FCE7F3"),
    "estacionamiento": ("local_parking", "#0369A1", "#E0F2FE"),
    "farmacia": ("local_pharmacy", "#DC2626", "#FEE2E2"),
    "gadgets": ("devices", "#4F46E5", "#EEF2FF"),
    "gym": ("fitness_center", "#059669", "#ECFDF5"),
    "la obra": ("home_repair_service", "#0F766E", "#CCFBF1"),
    "lima": ("flight_takeoff", "#0D9488", "#CCFBF1"),
    "otros": ("category", "#6B7280", "#F3F4F6"),
    "peluqueria": ("content_cut", "#14B8A6", "#F0FDFA"),
    "regalos": ("redeem", "#EC4899", "#FCE7F3"),
    "salida con amigos": ("groups", "#8B5CF6", "#F5F3FF"),
    "sin categoria": ("help", "#64748B", "#F8FAFC"),
    "snack": ("bakery_dining", "#FB7185", "#FFF1F2"),
    "supermercado": ("local_grocery_store", "#7C3AED", "#F3E8FF"),
    "suscripciones": ("subscriptions", "#0EA5E9", "#E0F2FE"),
    "tabaco": ("smoking_rooms", "#7C2D12", "#FEF2F2"),
    "transferencias": ("swap_horiz", "#334155", "#E2E8F0"),
    "transporte": ("commute", "#2563EB", "#DBEAFE"),
    "viaje": ("flight", "#F59E0B", "#FEF3C7"),
}

ICON_RULES: list[tuple[tuple[str, ...], CategoryIcon]] = [
    (("uber", "taxi", "bencina", "combustible", "peaje"), ("directions_car", "#2563EB", "#DBEAFE")),
    (("supermercado", "mercado", "comida"), ("local_grocery_store", "#7C3AED", "#F3E8FF")),
    (("delivery", "restaurante"), ("restaurant", "#EA580C", "#FFF7ED")),
    (("arriendo", "alquiler", "hogar", "casa"), ("home", "#0EA5E9", "#E0F2FE")),
    (("salud", "farmacia", "medico", "clinica"), ("local_hospital", "#DC2626", "#FEE2E2")),
    (("servicio", "agua", "luz", "gas", "internet", "telefono"), ("bolt", "#059669", "#D1FAE5")),
    (("cine", "juego", "spotify", "netflix"), ("movie", "#DB2777", "#FCE7F3")),
    (("educacion", "curso", "universidad", "colegio"), ("school", "#2563EB", "#DBEAFE")),
    (("viaje", "hotel", "vuelo", "pasaje"), ("flight", "#F59E0B", "#FEF3C7")),
    (("transferencia", "pago", "cuota", "deuda"), ("payments", "#334155", "#E2E8F0")),
]

FALLBACK_ICON_POOL: tuple[CategoryIcon, ...] = (
    ("wallet", "#334155", "#F1F5F9"),
    ("receipt_long", "#475569", "#F8FAFC"),
    ("category", "#6B7280", "#F3F4F6"),
    ("savings", "#0891B2", "#ECFEFF"),
    ("local_mall", "#7C3AED", "#F3E8FF"),
    ("storefront", "#2563EB", "#DBEAFE"),
    ("payments", "#0F766E", "#CCFBF1"),
    ("dashboard", "#4F46E5", "#EEF2FF"),
)


def _fallback_icon(normalized: str) -> CategoryIcon:
    digest = hashlib.sha1(normalized.encode("utf-8")).digest()
    idx = int.from_bytes(digest[:2], byteorder="big") % len(FALLBACK_ICON_POOL)
    return FALLBACK_ICON_POOL[idx]


def get_category_icon(category_name: str | None) -> CategoryIcon:
    if not category_name:
        return DEFAULT_ICON

    normalized = normalize_text(str(category_name))
    if normalized in EXACT_ICON_MAP:
        return EXACT_ICON_MAP[normalized]

    for keywords, icon_data in ICON_RULES:
        if any(keyword in normalized for keyword in keywords):
            return icon_data
    return _fallback_icon(normalized)
