"""Servicio de tabla editable, guardado masivo y export."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import io

import pandas as pd

from data.models import Categoria, Movimiento
from data.repositories.movimientos_repo import MovimientoRepository
from services.dashboard_service import DashboardFilters, DashboardService
from utils.constants import MOVEMENT_TYPE_EXPENSE
from utils.hashing import build_unique_key
from utils.normalization import normalize_text, parse_amount


@dataclass
class MovementFilters:
    text_filter: str | None = None
    month: int | None = None
    year: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    category_id: int | None = None


class MovementsService:
    def __init__(self, session):
        self.session = session
        self.repo = MovimientoRepository(session)
        self.dashboard = DashboardService(session)

    def list_for_table(self, filters: MovementFilters) -> pd.DataFrame:
        dash_filters = DashboardFilters(
            text_filter=filters.text_filter,
            month=filters.month,
            year=filters.year,
            date_from=filters.date_from,
            date_to=filters.date_to,
            category_id=filters.category_id,
        )
        df = self.dashboard.get_movements_df(dash_filters)
        if df.empty:
            return df

        df = df.copy()
        df["monto_ui"] = df.apply(
            lambda row: -int(row["monto_abs_clp"]) if row["tipo_movimiento"] == MOVEMENT_TYPE_EXPENSE else int(row["monto_abs_clp"]),
            axis=1,
        )
        return df

    def bulk_save(self, edited_rows: list[dict]) -> int:
        payload = []
        for row in edited_rows:
            monto_abs, movement_type = parse_amount(row.get("monto_ui"))
            payload.append(
                {
                    "id": int(row["id"]),
                    "monto_abs_clp": monto_abs,
                    "categoria_id": int(row["categoria_id"]),
                    "nota_usuario": (row.get("nota_usuario") or "").strip() or None,
                    "tipo_movimiento": movement_type,
                }
            )
        return self.repo.bulk_update(payload)

    def add_manual_entry(
        self,
        *,
        fecha: date,
        detalle: str,
        monto_ui: int | float | str,
        categoria_id: int,
        nota_usuario: str | None = None,
    ) -> str:
        detalle_clean = detalle.strip()
        if not detalle_clean:
            raise ValueError("Detalle requerido")

        detalle_norm = normalize_text(detalle_clean)
        monto_abs, movement_type = parse_amount(monto_ui)
        unique_key = build_unique_key(fecha=fecha, detalle_norm=detalle_norm, monto_abs_clp=monto_abs)

        if self.repo.is_tombstoned(unique_key):
            raise ValueError("El movimiento fue eliminado previamente y esta bloqueado por tombstone")
        if self.repo.exists_unique_key(unique_key):
            raise ValueError("Ya existe un movimiento con el mismo unique_key")

        movement = Movimiento(
            fecha=fecha,
            detalle=detalle_clean,
            detalle_norm=detalle_norm,
            monto_abs_clp=monto_abs,
            tipo_movimiento=movement_type,
            categoria_id=int(categoria_id),
            nota_usuario=(nota_usuario or "").strip() or None,
            unique_key=unique_key,
            fuente="manual_ui",
            suggestion_status="NA",
        )
        self.session.add(movement)

        category = self.session.get(Categoria, int(categoria_id))
        if category:
            self.repo.learn_category_map(
                detalle_norm=detalle_norm,
                monto_abs_clp=monto_abs,
                categoria=category,
                source="manual_entry",
                confidence=1.0,
            )
        self.session.flush()
        return unique_key

    def delete_one(self, unique_key: str, reason: str = "manual_ui") -> bool:
        return self.repo.soft_delete(unique_key, reason=reason)

    def ignore_one(self, unique_key: str, reason: str = "manual_ui") -> bool:
        return self.repo.ignore(unique_key, reason=reason)

    def restore_ignored(self, unique_key: str) -> bool:
        return self.repo.restore_ignored(unique_key)

    def list_pending_suggestions(self, limit: int = 200) -> pd.DataFrame:
        rows = self.repo.list_pending_suggestions(limit=limit)
        if not rows:
            return pd.DataFrame(
                columns=[
                    "unique_key",
                    "fecha",
                    "detalle",
                    "monto_ui",
                    "categoria_actual",
                    "categoria_sugerida",
                    "fuente_sugerencia",
                    "confianza",
                ]
            )

        records = []
        for movement in rows:
            monto_ui = -int(movement.monto_abs_clp) if movement.tipo_movimiento == MOVEMENT_TYPE_EXPENSE else int(movement.monto_abs_clp)
            records.append(
                {
                    "unique_key": movement.unique_key,
                    "fecha": movement.fecha,
                    "detalle": movement.detalle,
                    "monto_ui": monto_ui,
                    "categoria_actual": movement.categoria.nombre if movement.categoria else "",
                    "categoria_sugerida": movement.suggested_categoria.nombre if movement.suggested_categoria else "",
                    "fuente_sugerencia": movement.suggestion_source or "",
                    "confianza": movement.suggestion_confidence or 0.0,
                }
            )
        return pd.DataFrame.from_records(records)

    def resolve_suggestion(self, unique_key: str, decision: str, manual_category_id: int | None = None) -> bool:
        return self.repo.resolve_suggestion(
            unique_key=unique_key,
            decision=decision,
            manual_category_id=manual_category_id,
        )

    def export_filtered_csv(self, filters: MovementFilters) -> bytes:
        df = self.list_for_table(filters)
        if df.empty:
            return b""

        ordered_cols = [
            "id",
            "fecha",
            "detalle",
            "monto_ui",
            "monto_abs_clp",
            "tipo_movimiento",
            "categoria",
            "nota_usuario",
            "detalle_norm",
            "unique_key",
        ]
        output = io.StringIO()
        df[ordered_cols].to_csv(output, index=False)
        return output.getvalue().encode("utf-8")
