"""Servicio de carga e ingesta robusta de CSV."""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
import re
from typing import Any

from data.models import Movimiento
from data.repositories import CategoriaRepository, MovimientoRepository
from services.category_suggestion_service import CategorySuggestionService
from utils.config import get_settings
from utils.constants import MOVEMENT_TYPE_EXPENSE
from utils.csv_reader import parse_csv
from utils.errors import IngestionAppError
from utils.hashing import build_unique_key
from utils.normalization import normalize_text, parse_amount, parse_date


@dataclass
class IngestionRowError:
    row_number: int
    message: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestionResult:
    total_rows: int
    imported: int
    duplicated: int
    tombstoned: int
    errors: list[IngestionRowError]
    encoding: str
    delimiter: str


class IngestionService:
    def __init__(self, session):
        self.session = session
        self.cat_repo = CategoriaRepository(session)
        self.mov_repo = MovimientoRepository(session)
        self.suggestion_service = CategorySuggestionService(session)

    def ingest_csv(
        self,
        payload: bytes,
        *,
        source_label: str = "csv_upload",
        date_formats: tuple[str, ...] | None = None,
    ) -> IngestionResult:
        if not payload:
            raise IngestionAppError("Archivo vacio")

        parsed = parse_csv(payload)
        return self.ingest_rows(
            parsed.rows,
            source_label=source_label,
            date_formats=date_formats,
            encoding=parsed.encoding,
            delimiter=parsed.delimiter,
        )

    def ingest_rows(
        self,
        rows: list[dict[str, Any]],
        *,
        source_label: str = "streamlit_rows",
        date_formats: tuple[str, ...] | None = None,
        encoding: str = "in_memory",
        delimiter: str = "in_memory",
    ) -> IngestionResult:
        settings = get_settings()
        accepted_formats = date_formats or settings.default_date_formats

        default_category = self.cat_repo.ensure_default_category()

        imported = 0
        duplicated = 0
        tombstoned = 0
        errors: list[IngestionRowError] = []
        pending: list[Movimiento] = []
        local_ocr_seen: dict[tuple[str, int], list[str]] = {}
        remote_ocr_seen: dict[tuple[str, int], list[str]] = {}
        is_ocr_import = source_label.startswith("screenshot_ocr")

        prepared_rows: list[dict[str, Any]] = []
        for idx, row in enumerate(rows, start=2):
            try:
                fecha = parse_date(str(row.get("fecha", "")), accepted_formats)
                detail_raw = str(row.get("detalle", "")).strip()
                if not detail_raw:
                    raise ValueError("Detalle vacio")

                detalle_norm = normalize_text(detail_raw)
                raw_monto = row.get("monto")
                if raw_monto in {None, ""}:
                    raw_monto = row.get("monto_real")
                monto_abs_clp, tipo_movimiento = parse_amount(raw_monto)

                # Keep card uploads as expenses by default, even when raw sign is inconsistent.
                es_gasto_raw = str(row.get("es_gasto", "")).strip().lower()
                if settings.assume_all_expenses or es_gasto_raw in {"1", "true", "yes", "si", "sí"}:
                    tipo_movimiento = MOVEMENT_TYPE_EXPENSE
                unique_key = build_unique_key(
                    fecha=fecha,
                    detalle_norm=detalle_norm,
                    monto_abs_clp=monto_abs_clp,
                )
                prepared_rows.append(
                    {
                        "row": row,
                        "fecha": fecha,
                        "detalle_raw": detail_raw,
                        "detalle_norm": detalle_norm,
                        "monto_abs_clp": int(monto_abs_clp),
                        "tipo_movimiento": tipo_movimiento,
                        "unique_key": unique_key,
                        "provided_category": str(row.get("categoria", "")).strip(),
                        "nota_usuario": (str(row.get("nota_usuario", "")).strip() or None),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(
                    IngestionRowError(
                        row_number=idx,
                        message=str(exc),
                        payload=row,
                    )
                )

        incoming_unique_keys = [str(item["unique_key"]) for item in prepared_rows]
        tombstoned_keys = self.mov_repo.list_tombstoned_unique_keys(incoming_unique_keys)
        existing_keys = self.mov_repo.list_existing_unique_keys(incoming_unique_keys)
        seen_in_payload: set[str] = set()
        category_cache: dict[str, Any] = {normalize_text(default_category.nombre): default_category}
        suggestion_cache: dict[tuple[str, int], Any] = {}

        for item in prepared_rows:
            unique_key = str(item["unique_key"])
            if unique_key in tombstoned_keys:
                tombstoned += 1
                continue

            if unique_key in existing_keys or unique_key in seen_in_payload:
                duplicated += 1
                continue

            fecha = item["fecha"]
            detalle_norm = str(item["detalle_norm"])
            monto_abs_clp = int(item["monto_abs_clp"])

            if is_ocr_import and self._is_ocr_similar_duplicate(
                fecha=fecha,
                monto_abs_clp=monto_abs_clp,
                detalle_norm=detalle_norm,
                local_seen=local_ocr_seen,
                remote_seen=remote_ocr_seen,
            ):
                duplicated += 1
                continue

            provided_category = str(item["provided_category"])
            category = None
            suggestion_source = "none"
            suggestion_confidence = 0.0
            suggestion_category_id = None
            suggestion_status = "NA"

            if provided_category:
                normalized_category = normalize_text(provided_category)
                category = category_cache.get(normalized_category)
                if category is None:
                    category = self.cat_repo.get_or_create(provided_category)
                    category_cache[normalized_category] = category
                suggestion_source = "provided_in_csv"
                suggestion_confidence = 1.0
                suggestion_status = "ACEPTADA"
            else:
                suggestion_key = (detalle_norm, monto_abs_clp)
                suggestion = suggestion_cache.get(suggestion_key)
                if suggestion is None:
                    suggestion = self.suggestion_service.suggest(
                        detalle_norm=detalle_norm,
                        monto_abs_clp=monto_abs_clp,
                    )
                    suggestion_cache[suggestion_key] = suggestion
                if suggestion.categoria is not None:
                    category = default_category
                    suggestion_category_id = suggestion.categoria.id
                    suggestion_source = suggestion.source
                    suggestion_confidence = suggestion.confidence
                    suggestion_status = "PENDIENTE"

            if category is None:
                category = default_category

            movement = Movimiento(
                fecha=fecha,
                detalle=str(item["detalle_raw"]),
                detalle_norm=detalle_norm,
                monto_abs_clp=monto_abs_clp,
                tipo_movimiento=str(item["tipo_movimiento"]),
                categoria_id=category.id,
                suggested_categoria_id=suggestion_category_id,
                suggestion_source=suggestion_source if suggestion_source != "none" else None,
                suggestion_confidence=suggestion_confidence if suggestion_confidence > 0 else None,
                suggestion_status=suggestion_status,
                nota_usuario=item["nota_usuario"],
                unique_key=unique_key,
                fuente=source_label,
                payload_raw=item["row"],
            )
            pending.append(movement)
            imported += 1
            seen_in_payload.add(unique_key)

            if is_ocr_import:
                local_ocr_seen.setdefault((fecha.isoformat(), monto_abs_clp), []).append(detalle_norm)

            if provided_category:
                self.mov_repo.learn_category_map(
                    detalle_norm=detalle_norm,
                    monto_abs_clp=monto_abs_clp,
                    categoria=category,
                    source=suggestion_source,
                    confidence=suggestion_confidence,
                )

        try:
            self.mov_repo.bulk_insert(pending)
        except Exception as exc:  # noqa: BLE001
            raise IngestionAppError(str(exc)) from exc

        return IngestionResult(
            total_rows=len(rows),
            imported=imported,
            duplicated=duplicated,
            tombstoned=tombstoned,
            errors=errors,
            encoding=encoding,
            delimiter=delimiter,
        )

    def _is_ocr_similar_duplicate(
        self,
        *,
        fecha,
        monto_abs_clp: int,
        detalle_norm: str,
        local_seen: dict[tuple[str, int], list[str]],
        remote_seen: dict[tuple[str, int], list[str]],
    ) -> bool:
        bucket_key = (fecha.isoformat(), int(monto_abs_clp))
        for existing in local_seen.get(bucket_key, []):
            if self._details_similar(detalle_norm, existing):
                return True

        if bucket_key not in remote_seen:
            existing_rows = self.mov_repo.list_active_by_date_amount(fecha=fecha, monto_abs_clp=int(monto_abs_clp))
            remote_seen[bucket_key] = [str(item.detalle_norm or "") for item in existing_rows]

        for existing in remote_seen[bucket_key]:
            if self._details_similar(detalle_norm, existing):
                return True
        return False

    @staticmethod
    def _details_similar(left: str, right: str) -> bool:
        if left == right:
            return True
        left_tokens = IngestionService._detail_tokens(left)
        right_tokens = IngestionService._detail_tokens(right)
        if left_tokens and right_tokens:
            overlap = left_tokens.intersection(right_tokens)
            union = left_tokens.union(right_tokens)
            if union:
                jaccard = len(overlap) / len(union)
                if jaccard >= 0.6:
                    return True
        return SequenceMatcher(None, left, right).ratio() >= 0.82

    @staticmethod
    def _detail_tokens(value: str) -> set[str]:
        tokens = set(re.findall(r"[a-z0-9]+", str(value or "")))
        return {
            token
            for token in tokens
            if len(token) >= 3 and not token.isdigit()
        }
