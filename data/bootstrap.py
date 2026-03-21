"""Bootstrap de base de datos para dev y validacion de esquema."""

from __future__ import annotations

from sqlalchemy import inspect, select
from sqlalchemy.exc import SQLAlchemyError

from data.models import Base, Categoria
from data.session import get_engine, get_session_factory
from utils.constants import DEFAULT_CATEGORY_NAME
from utils.errors import ConfigurationAppError


REQUIRED_TABLES = {
    "categorias",
    "movimientos",
    "categoria_map",
    "movimientos_borrados",
    "movimientos_ignorados",
}


def _build_database_bootstrap_error(exc: Exception) -> ConfigurationAppError:
    detail = str(exc).lower()
    if "tenant or user not found" in detail:
        return ConfigurationAppError(
            "No fue posible conectar a PostgreSQL. "
            "El DATABASE_URL configurado en Streamlit Cloud parece invalido para Supabase "
            "(tenant o usuario no encontrado). Revisa Settings > Secrets y vuelve a pegar "
            "la cadena de conexion completa."
        )
    if "password authentication failed" in detail:
        return ConfigurationAppError(
            "No fue posible autenticar contra PostgreSQL. "
            "Revisa usuario y password dentro de DATABASE_URL en Streamlit Cloud > Settings > Secrets."
        )
    if "could not translate host name" in detail or "name or service not known" in detail:
        return ConfigurationAppError(
            "No fue posible resolver el host de PostgreSQL. "
            "Revisa el host dentro de DATABASE_URL en Streamlit Cloud > Settings > Secrets."
        )
    return ConfigurationAppError(
        "No fue posible conectar a la base de datos configurada. "
        "Revisa DATABASE_URL en Streamlit Cloud > Settings > Secrets."
    )


def ensure_database_ready(database_url: str | None = None) -> None:
    try:
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
    except SQLAlchemyError as exc:
        raise _build_database_bootstrap_error(exc) from exc
