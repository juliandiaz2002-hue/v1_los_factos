import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from data.models import Base
from data.repositories.movimientos_repo import MovimientoRepository
from services.ingestion_service import IngestionService


@pytest.fixture(scope="module")
def db_url():
    value = os.getenv("TEST_DATABASE_URL")
    if not value:
        pytest.skip("TEST_DATABASE_URL no configurada")
    return value


@pytest.fixture(scope="module")
def db_session_factory(db_url):
    engine = create_engine(db_url)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    yield factory
    Base.metadata.drop_all(bind=engine)


def test_ingestion_respects_tombstones(db_session_factory):
    csv_payload = (
        "fecha,detalle,monto,categoria\n"
        "2026-02-14,Uber Chile,-3990,Transporte\n"
    ).encode("utf-8")

    session = db_session_factory()
    try:
        service = IngestionService(session)
        first = service.ingest_csv(csv_payload)
        assert first.imported == 1

        mov_repo = MovimientoRepository(session)
        movement = mov_repo.list_active()[0]
        assert mov_repo.soft_delete(movement.unique_key)
        session.commit()

        second = service.ingest_csv(csv_payload)
        assert second.imported == 0
        assert second.tombstoned == 1
    finally:
        session.close()
