"""Sesion y engine de base de datos."""

from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker

from utils.config import get_settings
from utils.errors import DatabaseAppError


def normalize_database_url(database_url: str) -> str:
    parsed = make_url(database_url)
    drivername = parsed.drivername
    if drivername == "postgres":
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if drivername == "postgresql":
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


@lru_cache(maxsize=1)
def get_engine(database_url: str | None = None) -> Engine:
    url = normalize_database_url(database_url or get_settings().database_url)
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite":
        return create_engine(url, future=True, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True, future=True)


@lru_cache(maxsize=1)
def get_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(database_url), autoflush=False, autocommit=False, expire_on_commit=False)


@contextmanager
def session_scope(database_url: str | None = None) -> Iterator[Session]:
    factory = get_session_factory(database_url)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception as exc:
        session.rollback()
        raise DatabaseAppError(str(exc)) from exc
    finally:
        session.close()
