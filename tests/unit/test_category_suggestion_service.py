from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from data.models import Base, Categoria, Movimiento
from services.ingestion_service import IngestionService
from services.category_suggestion_service import CategorySuggestionService
from utils.constants import DEFAULT_CATEGORY_NAME, MOVEMENT_TYPE_EXPENSE
from utils.hashing import build_unique_key
from utils.normalization import normalize_text


def _make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return factory()


def test_suggestion_fallback_uses_active_non_default_category() -> None:
    session = _make_session()
    try:
        default = Categoria(nombre=DEFAULT_CATEGORY_NAME, activa=True)
        session.add(default)
        session.add(Categoria(nombre="Transporte", activa=True))
        session.commit()

        service = CategorySuggestionService(session)
        suggestion = service.suggest(detalle_norm=normalize_text("suscripcion nube pro"), monto_abs_clp=12990)

        assert suggestion.categoria is not None
        assert suggestion.categoria.nombre == "Transporte"
        assert suggestion.source in {"global_dominant_fallback", "active_category_baseline", "similarity_fallback"}
    finally:
        session.close()


def test_suggestion_never_returns_default_category() -> None:
    session = _make_session()
    try:
        default = Categoria(nombre=DEFAULT_CATEGORY_NAME, activa=True)
        transporte = Categoria(nombre="Transporte", activa=True)
        session.add_all([default, transporte])
        session.flush()

        movement_default = Movimiento(
            fecha=date(2026, 2, 10),
            detalle="compra farmacia",
            detalle_norm=normalize_text("compra farmacia"),
            monto_abs_clp=20000,
            tipo_movimiento=MOVEMENT_TYPE_EXPENSE,
            categoria_id=default.id,
            unique_key=build_unique_key(
                fecha=date(2026, 2, 10),
                detalle_norm=normalize_text("compra farmacia"),
                monto_abs_clp=20000,
            ),
            suggestion_status="NA",
        )
        movement_non_default = Movimiento(
            fecha=date(2026, 2, 11),
            detalle="uber chile",
            detalle_norm=normalize_text("uber chile"),
            monto_abs_clp=3990,
            tipo_movimiento=MOVEMENT_TYPE_EXPENSE,
            categoria_id=transporte.id,
            unique_key=build_unique_key(
                fecha=date(2026, 2, 11),
                detalle_norm=normalize_text("uber chile"),
                monto_abs_clp=3990,
            ),
            suggestion_status="NA",
        )
        session.add_all([movement_default, movement_non_default])
        session.commit()

        service = CategorySuggestionService(session)
        suggestion = service.suggest(detalle_norm=normalize_text("viaje auto"), monto_abs_clp=5000)
        assert suggestion.categoria is not None
        assert suggestion.categoria.nombre != DEFAULT_CATEGORY_NAME
    finally:
        session.close()


def test_ingestion_without_categoria_creates_pending_suggestion() -> None:
    session = _make_session()
    try:
        session.add(Categoria(nombre=DEFAULT_CATEGORY_NAME, activa=True))
        session.add(Categoria(nombre="Transporte", activa=True))
        session.commit()

        payload = (
            "fecha,detalle,monto\n"
            "2026-02-14,Pago streaming,-5990\n"
        ).encode("utf-8")
        result = IngestionService(session).ingest_csv(payload)
        session.commit()

        assert result.imported == 1

        movement = session.scalar(select(Movimiento).limit(1))
        assert movement is not None
        assert movement.suggestion_status == "PENDIENTE"
        assert movement.suggested_categoria_id is not None
    finally:
        session.close()
