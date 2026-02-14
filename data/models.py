"""Modelos SQLAlchemy para Los Factos v2."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from utils.constants import (
    DEFAULT_CATEGORY_NAME,
    MOVEMENT_STATUS_ACTIVE,
    MOVEMENT_TYPE_EXPENSE,
)


class Base(DeclarativeBase):
    pass


ID_PK_TYPE = BigInteger().with_variant(Integer, "sqlite")
ID_FK_TYPE = BigInteger().with_variant(Integer, "sqlite")


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Categoria(TimestampMixin, Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(ID_PK_TYPE, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    movimientos: Mapped[list["Movimiento"]] = relationship(
        back_populates="categoria",
        foreign_keys="Movimiento.categoria_id",
    )
    maps: Mapped[list["CategoriaMap"]] = relationship(back_populates="categoria")


class Movimiento(TimestampMixin, Base):
    __tablename__ = "movimientos"

    id: Mapped[int] = mapped_column(ID_PK_TYPE, primary_key=True, autoincrement=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    detalle: Mapped[str] = mapped_column(Text, nullable=False)
    detalle_norm: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    monto_abs_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tipo_movimiento: Mapped[str] = mapped_column(String(20), nullable=False, default=MOVEMENT_TYPE_EXPENSE)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default=MOVEMENT_STATUS_ACTIVE, index=True)
    categoria_id: Mapped[int] = mapped_column(ID_FK_TYPE, ForeignKey("categorias.id"), nullable=False, index=True)
    suggested_categoria_id: Mapped[Optional[int]] = mapped_column(
        ID_FK_TYPE,
        ForeignKey("categorias.id"),
        nullable=True,
        index=True,
    )
    suggestion_source: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    suggestion_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    suggestion_status: Mapped[str] = mapped_column(String(20), nullable=False, default="NA", index=True)
    nota_usuario: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unique_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    fuente: Mapped[str] = mapped_column(String(50), nullable=False, default="csv")
    payload_raw: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    categoria: Mapped[Categoria] = relationship(back_populates="movimientos", foreign_keys=[categoria_id])
    suggested_categoria: Mapped[Optional[Categoria]] = relationship(foreign_keys=[suggested_categoria_id])

class CategoriaMap(Base):
    __tablename__ = "categoria_map"

    id: Mapped[int] = mapped_column(ID_PK_TYPE, primary_key=True, autoincrement=True)
    detalle_norm: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    monto_abs_clp: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    categoria_id: Mapped[int] = mapped_column(ID_FK_TYPE, ForeignKey("categorias.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    hits: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    categoria: Mapped[Categoria] = relationship(back_populates="maps")

    __table_args__ = (
        UniqueConstraint("detalle_norm", "monto_abs_clp", name="uq_categoria_map_detalle_monto"),
    )


class MovimientoBorrado(Base):
    __tablename__ = "movimientos_borrados"

    id: Mapped[int] = mapped_column(ID_PK_TYPE, primary_key=True, autoincrement=True)
    unique_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    fecha: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    detalle_norm: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    monto_abs_clp: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    deleted_reason: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MovimientoIgnorado(Base):
    __tablename__ = "movimientos_ignorados"

    id: Mapped[int] = mapped_column(ID_PK_TYPE, primary_key=True, autoincrement=True)
    unique_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    movimiento_id: Mapped[Optional[int]] = mapped_column(ID_FK_TYPE, ForeignKey("movimientos.id"), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    ignored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    restored_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


def bootstrap_default_category_rows() -> list[dict[str, object]]:
    return [{"nombre": DEFAULT_CATEGORY_NAME, "activa": True}]
