from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from data.models import Base, Categoria, Movimiento
from services.movements_service import MovementsService
from utils.constants import DEFAULT_CATEGORY_NAME, MOVEMENT_TYPE_EXPENSE
from utils.hashing import build_unique_key
from utils.normalization import normalize_text


def _make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return factory()


def test_backfill_pending_suggestions_for_existing_uncategorized() -> None:
    session = _make_session()
    try:
        cat_default = Categoria(nombre=DEFAULT_CATEGORY_NAME, activa=True)
        cat_transporte = Categoria(nombre="Transporte", activa=True)
        session.add_all([cat_default, cat_transporte])
        session.flush()

        existing = Movimiento(
            fecha=date(2026, 2, 14),
            detalle="Pago app movilidad",
            detalle_norm=normalize_text("Pago app movilidad"),
            monto_abs_clp=3990,
            tipo_movimiento=MOVEMENT_TYPE_EXPENSE,
            categoria_id=int(cat_default.id),
            unique_key=build_unique_key(
                fecha=date(2026, 2, 14),
                detalle_norm=normalize_text("Pago app movilidad"),
                monto_abs_clp=3990,
            ),
            suggestion_status="NA",
        )
        session.add(existing)
        session.commit()

        service = MovementsService(session)
        pending_df = service.list_pending_suggestions(limit=50)
        session.commit()

        assert not pending_df.empty

        refreshed = session.scalar(
            select(Movimiento).where(Movimiento.unique_key == existing.unique_key)
        )
        assert refreshed is not None
        assert refreshed.suggested_categoria_id is not None
        assert refreshed.suggestion_status == "PENDIENTE"
        assert int(refreshed.suggested_categoria_id) != int(cat_default.id)
    finally:
        session.close()
