"""Bootstrap de base de datos para dev y validacion de esquema."""

from __future__ import annotations

from sqlalchemy import inspect, select

from data.models import Base, Categoria
from data.session import get_engine, get_session_factory
from utils.constants import DEFAULT_CATEGORY_NAME


REQUIRED_TABLES = {
    "categorias",
    "movimientos",
    "categoria_map",
    "movimientos_borrados",
    "movimientos_ignorados",
}


def ensure_database_ready(database_url: str | None = None) -> None:
    engine = get_engine(database_url)
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    backend = engine.url.get_backend_name()

    if backend == "sqlite":
        if not REQUIRED_TABLES.issubset(existing):
            Base.metadata.create_all(bind=engine)
    else:
        missing = REQUIRED_TABLES - existing
        if missing:
            missing_csv = ", ".join(sorted(missing))
            raise RuntimeError(
                f"Esquema incompleto ({missing_csv}). Ejecuta: alembic upgrade head"
            )

    session_factory = get_session_factory(database_url)
    session = session_factory()
    try:
        default_category = session.scalar(
            select(Categoria).where(Categoria.nombre == DEFAULT_CATEGORY_NAME)
        )
        if default_category is None:
            session.add(Categoria(nombre=DEFAULT_CATEGORY_NAME, activa=True))
            session.commit()
    finally:
        session.close()
