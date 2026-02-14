"""Funciones de formato para UI."""

from __future__ import annotations

from datetime import date, datetime


def format_clp(amount: int | float | None, *, signed: bool = False) -> str:
    if amount is None:
        return "-"
    value = int(round(float(amount)))
    if signed and value > 0:
        prefix = "+"
    elif signed and value < 0:
        prefix = "-"
    else:
        prefix = ""
    return f"{prefix}$ {abs(value):,}".replace(",", ".")


def format_date_display(value: date | datetime | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, datetime):
        value = value.date()
    return value.strftime("%d-%m-%Y")
