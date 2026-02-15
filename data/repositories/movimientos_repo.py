"""Repositorio de movimientos, tombstones e ignorados."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, insert, select
from sqlalchemy.orm import Session

from data.models import Categoria, CategoriaMap, Movimiento, MovimientoBorrado, MovimientoIgnorado
from utils.constants import (
    MOVEMENT_STATUS_ACTIVE,
    MOVEMENT_STATUS_DELETED,
    MOVEMENT_STATUS_IGNORED,
)


class MovimientoRepository:
    def __init__(self, session: Session):
        self.session = session

    def exists_unique_key(self, unique_key: str) -> bool:
        stmt = select(func.count(Movimiento.id)).where(Movimiento.unique_key == unique_key)
        return bool(self.session.scalar(stmt))

    def is_tombstoned(self, unique_key: str) -> bool:
        stmt = select(func.count(MovimientoBorrado.id)).where(MovimientoBorrado.unique_key == unique_key)
        return bool(self.session.scalar(stmt))

    def bulk_insert(self, movements: list[Movimiento]) -> None:
        if not movements:
            return
        self.session.add_all(movements)
        self.session.flush()

    def list_active(
        self,
        *,
        text_filter: str | None = None,
        month: int | None = None,
        year: int | None = None,
        date_from=None,
        date_to=None,
        category_id: int | None = None,
    ) -> list[Movimiento]:
        conditions = [Movimiento.estado == MOVEMENT_STATUS_ACTIVE]

        if text_filter:
            like_value = f"%{text_filter.lower()}%"
            conditions.append(func.lower(Movimiento.detalle).like(like_value))
        if month:
            conditions.append(func.extract("month", Movimiento.fecha) == month)
        if year:
            conditions.append(func.extract("year", Movimiento.fecha) == year)
        if date_from:
            conditions.append(Movimiento.fecha >= date_from)
        if date_to:
            conditions.append(Movimiento.fecha <= date_to)
        if category_id:
            conditions.append(Movimiento.categoria_id == category_id)

        stmt = (
            select(Movimiento)
            .where(and_(*conditions))
            .order_by(Movimiento.fecha.desc(), Movimiento.id.desc())
        )
        return list(self.session.scalars(stmt).all())

    def bulk_update(self, updates: list[dict[str, Any]]) -> int:
        updated = 0
        for item in updates:
            movement = self.session.get(Movimiento, int(item["id"]))
            if not movement:
                continue
            if "monto_abs_clp" in item:
                movement.monto_abs_clp = int(item["monto_abs_clp"])
            if "categoria_id" in item:
                movement.categoria_id = int(item["categoria_id"])
            if "nota_usuario" in item:
                movement.nota_usuario = item["nota_usuario"]
            if "tipo_movimiento" in item:
                movement.tipo_movimiento = str(item["tipo_movimiento"])
            updated += 1
        return updated

    def soft_delete(self, unique_key: str, reason: str = "manual") -> bool:
        movement = self.session.scalar(select(Movimiento).where(Movimiento.unique_key == unique_key))
        if not movement:
            return False

        movement.estado = MOVEMENT_STATUS_DELETED
        movement.deleted_at = datetime.now(timezone.utc)

        exists_tombstone = self.session.scalar(
            select(MovimientoBorrado).where(MovimientoBorrado.unique_key == unique_key)
        )
        if not exists_tombstone:
            tombstone = MovimientoBorrado(
                unique_key=unique_key,
                fecha=movement.fecha,
                detalle_norm=movement.detalle_norm,
                monto_abs_clp=movement.monto_abs_clp,
                deleted_reason=reason,
            )
            self.session.add(tombstone)

        return True

    def ignore(self, unique_key: str, reason: str = "manual") -> bool:
        movement = self.session.scalar(select(Movimiento).where(Movimiento.unique_key == unique_key))
        if not movement:
            return False

        movement.estado = MOVEMENT_STATUS_IGNORED

        existing = self.session.scalar(select(MovimientoIgnorado).where(MovimientoIgnorado.unique_key == unique_key))
        if existing:
            existing.active = True
            existing.reason = reason
            existing.restored_at = None
        else:
            self.session.add(
                MovimientoIgnorado(
                    unique_key=unique_key,
                    movimiento_id=movement.id,
                    reason=reason,
                    active=True,
                )
            )
        return True

    def restore_ignored(self, unique_key: str) -> bool:
        ignored = self.session.scalar(select(MovimientoIgnorado).where(MovimientoIgnorado.unique_key == unique_key))
        movement = self.session.scalar(select(Movimiento).where(Movimiento.unique_key == unique_key))
        if not ignored or not movement:
            return False

        ignored.active = False
        ignored.restored_at = datetime.now(timezone.utc)
        movement.estado = MOVEMENT_STATUS_ACTIVE
        return True

    def list_ignored(self, limit: int = 200) -> list[MovimientoIgnorado]:
        stmt = (
            select(MovimientoIgnorado)
            .where(MovimientoIgnorado.active.is_(True))
            .order_by(MovimientoIgnorado.ignored_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def list_pending_suggestions(self, limit: int = 200) -> list[Movimiento]:
        stmt = (
            select(Movimiento)
            .where(
                Movimiento.estado == MOVEMENT_STATUS_ACTIVE,
                Movimiento.suggestion_status == "PENDIENTE",
                Movimiento.suggested_categoria_id.is_not(None),
            )
            .order_by(Movimiento.fecha.desc(), Movimiento.id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def resolve_suggestion(self, unique_key: str, decision: str, manual_category_id: int | None = None) -> bool:
        movement = self.session.scalar(select(Movimiento).where(Movimiento.unique_key == unique_key))
        if not movement:
            return False

        normalized_decision = decision.upper()
        target_category: Categoria | None = None

        if normalized_decision == "ACEPTAR":
            if movement.suggested_categoria_id is None:
                return False
            movement.categoria_id = int(movement.suggested_categoria_id)
            movement.suggestion_status = "ACEPTADA"
            target_category = self.session.get(Categoria, movement.categoria_id)
        elif normalized_decision == "RECHAZAR":
            movement.suggestion_status = "RECHAZADA"
            return True
        elif normalized_decision == "MANUAL":
            if manual_category_id is None:
                return False
            movement.categoria_id = int(manual_category_id)
            movement.suggestion_status = "MANUAL"
            target_category = self.session.get(Categoria, movement.categoria_id)
        else:
            raise ValueError(f"Decision no soportada: {decision}")

        if target_category:
            self.learn_category_map(
                detalle_norm=movement.detalle_norm,
                monto_abs_clp=movement.monto_abs_clp,
                categoria=target_category,
                source=f"suggestion_{normalized_decision.lower()}",
                confidence=float(movement.suggestion_confidence or 1.0),
            )

        return True

    def reassign_category(self, unique_key: str, categoria_id: int, source: str = "manual_row_change") -> bool:
        movement = self.session.scalar(
            select(Movimiento).where(
                Movimiento.unique_key == unique_key,
                Movimiento.estado == MOVEMENT_STATUS_ACTIVE,
            )
        )
        if not movement:
            return False

        target_category = self.session.get(Categoria, int(categoria_id))
        if not target_category:
            return False

        movement.categoria_id = int(categoria_id)
        movement.suggestion_status = "MANUAL"
        movement.suggested_categoria_id = None

        self.learn_category_map(
            detalle_norm=movement.detalle_norm,
            monto_abs_clp=movement.monto_abs_clp,
            categoria=target_category,
            source=source,
            confidence=1.0,
        )
        return True

    def learn_category_map(
        self,
        *,
        detalle_norm: str,
        monto_abs_clp: int | None,
        categoria: Categoria,
        source: str,
        confidence: float,
    ) -> None:
        stmt = select(CategoriaMap).where(
            CategoriaMap.detalle_norm == detalle_norm,
            CategoriaMap.monto_abs_clp == monto_abs_clp,
        )
        existing = self.session.scalar(stmt)

        if existing:
            existing.categoria_id = categoria.id
            existing.source = source
            existing.confidence = confidence
            existing.hits = int(existing.hits) + 1
            existing.last_used_at = datetime.now(timezone.utc)
            return

        self.session.execute(
            insert(CategoriaMap).values(
                detalle_norm=detalle_norm,
                monto_abs_clp=monto_abs_clp,
                categoria_id=categoria.id,
                source=source,
                confidence=confidence,
                hits=1,
            )
        )

    def list_category_map_exact(self, detalle_norm: str, monto_abs_clp: int | None = None) -> list[CategoriaMap]:
        stmt = select(CategoriaMap).where(CategoriaMap.detalle_norm == detalle_norm)
        if monto_abs_clp is not None:
            stmt = stmt.where(CategoriaMap.monto_abs_clp == monto_abs_clp)
        stmt = stmt.order_by(CategoriaMap.confidence.desc(), CategoriaMap.hits.desc())
        return list(self.session.scalars(stmt).all())
