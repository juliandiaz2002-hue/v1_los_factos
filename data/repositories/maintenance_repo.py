"""Repositorio para diagnostico y reparaciones."""

from __future__ import annotations

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from data.models import Movimiento, MovimientoBorrado
from utils.constants import MOVEMENT_STATUS_ACTIVE


class MaintenanceRepository:
    def __init__(self, session: Session):
        self.session = session

    def diagnostics(self) -> dict[str, int]:
        total = self.session.scalar(select(func.count(Movimiento.id))) or 0
        active = self.session.scalar(select(func.count(Movimiento.id)).where(Movimiento.estado == MOVEMENT_STATUS_ACTIVE)) or 0
        tombstones = self.session.scalar(select(func.count(MovimientoBorrado.id))) or 0
        duplicated_unique_keys = self.session.scalar(
            text(
                """
                SELECT COUNT(*) FROM (
                  SELECT unique_key
                  FROM movimientos
                  GROUP BY unique_key
                  HAVING COUNT(*) > 1
                ) dup
                """
            )
        ) or 0

        invalid_amounts = self.session.scalar(
            select(func.count(Movimiento.id)).where(Movimiento.monto_abs_clp <= 0)
        ) or 0

        return {
            "movimientos_total": int(total),
            "movimientos_activos": int(active),
            "tombstones": int(tombstones),
            "duplicados_unique_key": int(duplicated_unique_keys),
            "montos_invalidos": int(invalid_amounts),
        }

    def repair_inconsistent_amounts(self) -> int:
        stmt = (
            update(Movimiento)
            .where(Movimiento.monto_abs_clp < 0)
            .values(monto_abs_clp=func.abs(Movimiento.monto_abs_clp))
        )
        result = self.session.execute(stmt)
        return int(result.rowcount or 0)
