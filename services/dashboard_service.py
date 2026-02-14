"""Servicio de insights y metricas."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date

import pandas as pd
from sqlalchemy import func, select

from data.models import Categoria, Movimiento
from data.repositories.movimientos_repo import MovimientoRepository
from utils.constants import MOVEMENT_STATUS_ACTIVE, MOVEMENT_TYPE_EXPENSE


@dataclass
class DashboardFilters:
    text_filter: str | None = None
    month: int | None = None
    year: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    category_id: int | None = None


class DashboardService:
    def __init__(self, session):
        self.session = session
        self.mov_repo = MovimientoRepository(session)

    def list_categories(self) -> list[Categoria]:
        stmt = select(Categoria).where(Categoria.activa.is_(True)).order_by(Categoria.nombre.asc())
        return list(self.session.scalars(stmt).all())

    def get_movements_df(self, filters: DashboardFilters) -> pd.DataFrame:
        rows = self.mov_repo.list_active(
            text_filter=filters.text_filter,
            month=filters.month,
            year=filters.year,
            date_from=filters.date_from,
            date_to=filters.date_to,
            category_id=filters.category_id,
        )

        records = [
            {
                "id": row.id,
                "fecha": row.fecha,
                "detalle": row.detalle,
                "detalle_norm": row.detalle_norm,
                "monto_abs_clp": row.monto_abs_clp,
                "tipo_movimiento": row.tipo_movimiento,
                "categoria_id": row.categoria_id,
                "categoria": row.categoria.nombre if row.categoria else "Sin categoria",
                "categoria_sugerida": row.suggested_categoria.nombre if row.suggested_categoria else "",
                "suggestion_status": row.suggestion_status,
                "nota_usuario": row.nota_usuario or "",
                "unique_key": row.unique_key,
            }
            for row in rows
        ]

        if not records:
            return pd.DataFrame(
                columns=[
                    "id",
                    "fecha",
                    "detalle",
                    "detalle_norm",
                    "monto_abs_clp",
                    "tipo_movimiento",
                    "categoria_id",
                    "categoria",
                    "categoria_sugerida",
                    "suggestion_status",
                    "nota_usuario",
                    "unique_key",
                ]
            )

        df = pd.DataFrame.from_records(records)
        return df

    def get_kpis(self, df: pd.DataFrame) -> dict[str, float]:
        if df.empty:
            return {
                "total_gasto": 0,
                "cantidad_movimientos": 0,
                "ticket_promedio": 0,
            }

        total_gasto = float(df["monto_abs_clp"].sum())
        count = int(df.shape[0])
        ticket = float(df["monto_abs_clp"].mean()) if count else 0.0

        return {
            "total_gasto": total_gasto,
            "cantidad_movimientos": count,
            "ticket_promedio": ticket,
        }

    def get_month_comparison(self, *, year: int, month: int) -> dict[str, float]:
        prev_month = 12 if month == 1 else month - 1
        prev_year = year - 1 if month == 1 else year

        current_stmt = select(func.coalesce(func.sum(Movimiento.monto_abs_clp), 0)).where(
            Movimiento.estado == MOVEMENT_STATUS_ACTIVE,
            Movimiento.tipo_movimiento == MOVEMENT_TYPE_EXPENSE,
            func.extract("year", Movimiento.fecha) == year,
            func.extract("month", Movimiento.fecha) == month,
        )
        previous_stmt = select(func.coalesce(func.sum(Movimiento.monto_abs_clp), 0)).where(
            Movimiento.estado == MOVEMENT_STATUS_ACTIVE,
            Movimiento.tipo_movimiento == MOVEMENT_TYPE_EXPENSE,
            func.extract("year", Movimiento.fecha) == prev_year,
            func.extract("month", Movimiento.fecha) == prev_month,
        )

        current = float(self.session.scalar(current_stmt) or 0)
        previous = float(self.session.scalar(previous_stmt) or 0)
        variation_pct = ((current - previous) / previous * 100) if previous else 0.0
        return {
            "current": current,
            "previous": previous,
            "variation_pct": variation_pct,
        }

    def get_projection_by_stable_categories(self, df: pd.DataFrame, *, year: int, month: int) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=["categoria", "proyeccion"])

        gastos_df = df[df["tipo_movimiento"] == MOVEMENT_TYPE_EXPENSE].copy()
        if gastos_df.empty:
            return pd.DataFrame(columns=["categoria", "proyeccion"])

        gastos_df["fecha"] = pd.to_datetime(gastos_df["fecha"])
        day_of_month = int(gastos_df["fecha"].dt.day.max())
        days_in_month = monthrange(year, month)[1]
        if day_of_month <= 0:
            return pd.DataFrame(columns=["categoria", "proyeccion"])

        grouped = gastos_df.groupby("categoria", as_index=False).agg(total=("monto_abs_clp", "sum"), count=("id", "count"))
        stable = grouped[grouped["count"] >= 2].copy()
        if stable.empty:
            return pd.DataFrame(columns=["categoria", "proyeccion"])

        stable["proyeccion"] = (stable["total"] / day_of_month) * days_in_month
        stable = stable[["categoria", "proyeccion"]].sort_values("proyeccion", ascending=False)
        return stable
