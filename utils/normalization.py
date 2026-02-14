"""Normalizacion de texto, fechas y montos."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Iterable

from .constants import (
    MOVEMENT_TYPE_EXPENSE,
    MOVEMENT_TYPE_INCOME,
    MOVEMENT_TYPE_NEUTRAL,
)
from .errors import ValidationAppError

_SPACES_RE = re.compile(r"\s+")
_AMOUNT_CLEAN_RE = re.compile(r"[^0-9,.-]")


def normalize_text(value: str) -> str:
    if value is None:
        return ""
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().strip()
    value = _SPACES_RE.sub(" ", value)
    return value


def parse_date(value: str, allowed_formats: Iterable[str]) -> date:
    raw = str(value).strip()
    if not raw:
        raise ValidationAppError("Fecha vacia")

    for fmt in allowed_formats:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue

    raise ValidationAppError(f"Formato de fecha invalido: {raw}")


def _to_decimal(raw: str) -> Decimal:
    cleaned = _AMOUNT_CLEAN_RE.sub("", raw.replace(" ", ""))
    if cleaned.count(",") > 0 and cleaned.count(".") > 0:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "")
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif cleaned.count(",") > 0:
        right = cleaned.split(",")[-1]
        if len(right) in {1, 2}:
            cleaned = cleaned.replace(".", "")
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif cleaned.count(".") == 1:
        right = cleaned.split(".")[-1]
        if len(right) == 3:
            cleaned = cleaned.replace(".", "")
    elif cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "")

    if cleaned in {"", "-", ".", "-,", "-."}:
        raise ValidationAppError("Monto vacio o invalido")

    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValidationAppError(f"Monto invalido: {raw}") from exc


def parse_amount(value: object) -> tuple[int, str]:
    raw = "" if value is None else str(value).strip()
    if raw == "":
        raise ValidationAppError("Monto vacio")

    decimal_value = _to_decimal(raw)
    rounded_abs = int(abs(decimal_value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    if decimal_value < 0:
        movement_type = MOVEMENT_TYPE_EXPENSE
    elif decimal_value > 0:
        movement_type = MOVEMENT_TYPE_INCOME
    else:
        movement_type = MOVEMENT_TYPE_NEUTRAL

    return rounded_abs, movement_type
