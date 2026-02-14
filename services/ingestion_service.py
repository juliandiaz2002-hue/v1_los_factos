"""Servicio de carga e ingesta robusta de CSV."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from data.models import Movimiento
from data.repositories import CategoriaRepository, MovimientoRepository
from services.category_suggestion_service import CategorySuggestionService
from utils.config import get_settings
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

        settings = get_settings()
        accepted_formats = date_formats or settings.default_date_formats
        parsed = parse_csv(payload)

        default_category = self.cat_repo.ensure_default_category()

        imported = 0
        duplicated = 0
        tombstoned = 0
        errors: list[IngestionRowError] = []
        pending: list[Movimiento] = []

        for idx, row in enumerate(parsed.rows, start=2):
            try:
                fecha = parse_date(str(row.get("fecha", "")), accepted_formats)
                detail_raw = str(row.get("detalle", "")).strip()
                if not detail_raw:
                    raise ValueError("Detalle vacio")

                detalle_norm = normalize_text(detail_raw)
                monto_abs_clp, tipo_movimiento = parse_amount(row.get("monto"))
                unique_key = build_unique_key(
                    fecha=fecha,
                    detalle_norm=detalle_norm,
                    monto_abs_clp=monto_abs_clp,
                )

                if self.mov_repo.is_tombstoned(unique_key):
                    tombstoned += 1
                    continue

                if self.mov_repo.exists_unique_key(unique_key):
                    duplicated += 1
                    continue

                provided_category = str(row.get("categoria", "")).strip()
                category = None
                suggestion_source = "none"
                suggestion_confidence = 0.0
                suggestion_category_id = None
                suggestion_status = "NA"

                if provided_category:
                    category = self.cat_repo.get_or_create(provided_category)
                    suggestion_source = "provided_in_csv"
                    suggestion_confidence = 1.0
                    suggestion_status = "ACEPTADA"
                else:
                    suggestion = self.suggestion_service.suggest(
                        detalle_norm=detalle_norm,
                        monto_abs_clp=monto_abs_clp,
                    )
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
                    detalle=detail_raw,
                    detalle_norm=detalle_norm,
                    monto_abs_clp=monto_abs_clp,
                    tipo_movimiento=tipo_movimiento,
                    categoria_id=category.id,
                    suggested_categoria_id=suggestion_category_id,
                    suggestion_source=suggestion_source if suggestion_source != "none" else None,
                    suggestion_confidence=suggestion_confidence if suggestion_confidence > 0 else None,
                    suggestion_status=suggestion_status,
                    nota_usuario=(str(row.get("nota_usuario", "")).strip() or None),
                    unique_key=unique_key,
                    fuente=source_label,
                    payload_raw=row,
                )
                pending.append(movement)
                imported += 1

                if provided_category:
                    self.mov_repo.learn_category_map(
                        detalle_norm=detalle_norm,
                        monto_abs_clp=monto_abs_clp,
                        categoria=category,
                        source=suggestion_source,
                        confidence=suggestion_confidence,
                    )
            except Exception as exc:  # noqa: BLE001
                errors.append(
                    IngestionRowError(
                        row_number=idx,
                        message=str(exc),
                        payload=row,
                    )
                )

        try:
            self.mov_repo.bulk_insert(pending)
        except Exception as exc:  # noqa: BLE001
            raise IngestionAppError(str(exc)) from exc

        return IngestionResult(
            total_rows=len(parsed.rows),
            imported=imported,
            duplicated=duplicated,
            tombstoned=tombstoned,
            errors=errors,
            encoding=parsed.encoding,
            delimiter=parsed.delimiter,
        )
