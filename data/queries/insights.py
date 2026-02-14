"""Consultas de agregacion para dashboard."""

from __future__ import annotations

from sqlalchemy import case, func, select

from data.models import Movimiento
from utils.constants import MOVEMENT_STATUS_ACTIVE, MOVEMENT_TYPE_EXPENSE


def expense_base_query():
    return select(Movimiento).where(
        Movimiento.estado == MOVEMENT_STATUS_ACTIVE,
        Movimiento.tipo_movimiento == MOVEMENT_TYPE_EXPENSE,
    )


def category_distribution_query():
    return (
        select(
            Movimiento.categoria_id,
            func.count(Movimiento.id).label("frecuencia"),
            func.sum(Movimiento.monto_abs_clp).label("monto_total"),
        )
        .where(Movimiento.estado == MOVEMENT_STATUS_ACTIVE)
        .group_by(Movimiento.categoria_id)
    )


def month_comparison_query(year: int, month: int):
    current_month = month
    previous_month = 12 if month == 1 else month - 1
    previous_year = year - 1 if month == 1 else year

    return (
        select(
            func.sum(
                case(
                    (func.extract("year", Movimiento.fecha) == year, case((func.extract("month", Movimiento.fecha) == current_month, Movimiento.monto_abs_clp), else_=0)),
                    else_=0,
                )
            ).label("current_total"),
            func.sum(
                case(
                    (func.extract("year", Movimiento.fecha) == previous_year, case((func.extract("month", Movimiento.fecha) == previous_month, Movimiento.monto_abs_clp), else_=0)),
                    else_=0,
                )
            ).label("previous_total"),
        )
        .where(Movimiento.estado == MOVEMENT_STATUS_ACTIVE)
    )
