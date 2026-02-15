"""Servicio de tabla editable, guardado masivo y export."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
import io
from itertools import combinations

import pandas as pd

from data.models import Categoria, Movimiento
from data.repositories.movimientos_repo import MovimientoRepository
from services.dashboard_service import DashboardFilters, DashboardService
from utils.constants import MOVEMENT_TYPE_EXPENSE
from utils.config import get_settings
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
        self.settings = get_settings()

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
            if self.settings.assume_all_expenses:
                movement_type = MOVEMENT_TYPE_EXPENSE
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
        if self.settings.assume_all_expenses:
            movement_type = MOVEMENT_TYPE_EXPENSE
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

    def reassign_category(self, unique_key: str, categoria_id: int) -> bool:
        return self.repo.reassign_category(unique_key=unique_key, categoria_id=int(categoria_id))

    def list_probable_duplicate_pairs(self, filters: MovementFilters, *, limit_pairs: int = 80) -> pd.DataFrame:
        df = self.list_for_table(filters)
        if df.empty:
            return pd.DataFrame(
                columns=[
                    "pair_id",
                    "monto_abs_clp",
                    "similarity_score",
                    "days_diff",
                    "left_unique_key",
                    "left_fecha",
                    "left_detalle",
                    "left_monto_ui",
                    "right_unique_key",
                    "right_fecha",
                    "right_detalle",
                    "right_monto_ui",
                ]
            )

        data = df.copy()
        data["fecha"] = pd.to_datetime(data["fecha"])
        data["monto_abs_clp"] = data["monto_abs_clp"].astype(int)

        output_rows: list[dict] = []
        for _, group in data.groupby("monto_abs_clp"):
            if len(group) < 2:
                continue

            subset = group.sort_values(by=["fecha", "id"], ascending=[False, False]).head(8)
            for left_idx, right_idx in combinations(list(subset.index), 2):
                left = subset.loc[left_idx]
                right = subset.loc[right_idx]

                left_key = str(left["unique_key"])
                right_key = str(right["unique_key"])
                pair_id = "|".join(sorted([left_key, right_key]))

                similarity = self._detail_similarity(
                    str(left.get("detalle_norm", "")),
                    str(right.get("detalle_norm", "")),
                )
                days_diff = abs((left["fecha"] - right["fecha"]).days)
                score = round(similarity + max(0.0, (30 - days_diff) / 150), 3)

                output_rows.append(
                    {
                        "pair_id": pair_id,
                        "monto_abs_clp": int(left["monto_abs_clp"]),
                        "similarity_score": score,
                        "days_diff": int(days_diff),
                        "left_unique_key": left_key,
                        "left_fecha": left["fecha"].date().isoformat(),
                        "left_detalle": str(left["detalle"]),
                        "left_monto_ui": int(left["monto_ui"]),
                        "right_unique_key": right_key,
                        "right_fecha": right["fecha"].date().isoformat(),
                        "right_detalle": str(right["detalle"]),
                        "right_monto_ui": int(right["monto_ui"]),
                    }
                )

        if not output_rows:
            return pd.DataFrame(
                columns=[
                    "pair_id",
                    "monto_abs_clp",
                    "similarity_score",
                    "days_diff",
                    "left_unique_key",
                    "left_fecha",
                    "left_detalle",
                    "left_monto_ui",
                    "right_unique_key",
                    "right_fecha",
                    "right_detalle",
                    "right_monto_ui",
                ]
            )

        result = pd.DataFrame(output_rows)
        result = result.sort_values(
            by=["similarity_score", "days_diff", "monto_abs_clp"],
            ascending=[False, True, False],
        )
        result = result.drop_duplicates(subset=["pair_id"], keep="first").head(limit_pairs).reset_index(drop=True)
        return result

    def list_suspicious_small_amounts(
        self,
        filters: MovementFilters,
        *,
        threshold_abs_clp: int = 500,
        limit_rows: int = 120,
    ) -> pd.DataFrame:
        df = self.list_for_table(filters)
        if df.empty:
            return pd.DataFrame(columns=["unique_key", "fecha", "detalle", "monto_ui", "categoria"])

        suspicious = df[df["monto_abs_clp"].astype(int) < int(threshold_abs_clp)].copy()
        if suspicious.empty:
            return pd.DataFrame(columns=["unique_key", "fecha", "detalle", "monto_ui", "categoria"])

        suspicious["fecha"] = pd.to_datetime(suspicious["fecha"])
        suspicious = suspicious.sort_values(by=["fecha", "id"], ascending=[False, False]).head(limit_rows)
        suspicious["fecha"] = suspicious["fecha"].dt.date.astype(str)
        return suspicious[["unique_key", "fecha", "detalle", "monto_ui", "categoria"]].reset_index(drop=True)

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

    @staticmethod
    def _detail_similarity(left: str, right: str) -> float:
        return float(SequenceMatcher(None, left or "", right or "").ratio())
