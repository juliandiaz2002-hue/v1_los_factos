"""initial schema

Revision ID: 20260214_0001
Revises:
Create Date: 2026-02-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260214_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "categorias",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("nombre", name="uq_categorias_nombre"),
    )
    op.create_index("ix_categorias_nombre", "categorias", ["nombre"], unique=False)

    op.create_table(
        "movimientos",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("detalle", sa.Text(), nullable=False),
        sa.Column("detalle_norm", sa.Text(), nullable=False),
        sa.Column("monto_abs_clp", sa.BigInteger(), nullable=False),
        sa.Column("tipo_movimiento", sa.String(length=20), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("categoria_id", sa.BigInteger(), nullable=False),
        sa.Column("suggested_categoria_id", sa.BigInteger(), nullable=True),
        sa.Column("suggestion_source", sa.String(length=40), nullable=True),
        sa.Column("suggestion_confidence", sa.Float(), nullable=True),
        sa.Column("suggestion_status", sa.String(length=20), nullable=False, server_default=sa.text("'NA'")),
        sa.Column("nota_usuario", sa.Text(), nullable=True),
        sa.Column("unique_key", sa.String(length=64), nullable=False),
        sa.Column("fuente", sa.String(length=50), nullable=False, server_default=sa.text("'csv'")),
        sa.Column("payload_raw", sa.JSON(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["categoria_id"], ["categorias.id"], name="fk_movimientos_categoria_id"),
        sa.ForeignKeyConstraint(["suggested_categoria_id"], ["categorias.id"], name="fk_movimientos_suggested_categoria_id"),
        sa.UniqueConstraint("unique_key", name="uq_movimientos_unique_key"),
    )
    op.create_index("ix_movimientos_unique_key", "movimientos", ["unique_key"], unique=True)
    op.create_index("ix_movimientos_fecha", "movimientos", ["fecha"], unique=False)
    op.create_index("ix_movimientos_categoria", "movimientos", ["categoria_id"], unique=False)
    op.create_index("ix_movimientos_suggested_categoria", "movimientos", ["suggested_categoria_id"], unique=False)
    op.create_index("ix_movimientos_suggestion_status", "movimientos", ["suggestion_status"], unique=False)
    op.create_index("ix_movimientos_detalle_norm", "movimientos", ["detalle_norm"], unique=False)

    op.create_table(
        "categoria_map",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("detalle_norm", sa.Text(), nullable=False),
        sa.Column("monto_abs_clp", sa.BigInteger(), nullable=True),
        sa.Column("categoria_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False, server_default=sa.text("'manual'")),
        sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("hits", sa.BigInteger(), nullable=False, server_default=sa.text("1")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["categoria_id"], ["categorias.id"], name="fk_categoria_map_categoria_id"),
        sa.UniqueConstraint("detalle_norm", "monto_abs_clp", name="uq_categoria_map_detalle_monto"),
    )
    op.create_index("ix_categoria_map_detalle_norm", "categoria_map", ["detalle_norm"], unique=False)
    op.create_index("ix_categoria_map_monto_abs_clp", "categoria_map", ["monto_abs_clp"], unique=False)

    op.create_table(
        "movimientos_borrados",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("unique_key", sa.String(length=64), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=True),
        sa.Column("detalle_norm", sa.Text(), nullable=True),
        sa.Column("monto_abs_clp", sa.BigInteger(), nullable=True),
        sa.Column("deleted_reason", sa.String(length=120), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("unique_key", name="uq_movimientos_borrados_unique_key"),
    )
    op.create_index("ix_movimientos_borrados_unique_key", "movimientos_borrados", ["unique_key"], unique=True)
    op.create_index("ix_movimientos_borrados_detalle_norm", "movimientos_borrados", ["detalle_norm"], unique=False)

    op.create_table(
        "movimientos_ignorados",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("unique_key", sa.String(length=64), nullable=False),
        sa.Column("movimiento_id", sa.BigInteger(), nullable=True),
        sa.Column("reason", sa.String(length=120), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("ignored_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["movimiento_id"], ["movimientos.id"], name="fk_movimientos_ignorados_movimiento_id"),
        sa.UniqueConstraint("unique_key", name="uq_movimientos_ignorados_unique_key"),
    )
    op.create_index("ix_movimientos_ignorados_unique_key", "movimientos_ignorados", ["unique_key"], unique=True)

    op.execute(
        """
        INSERT INTO categorias (nombre, activa)
        VALUES ('Sin categoria', true)
        ON CONFLICT (nombre) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_movimientos_ignorados_unique_key", table_name="movimientos_ignorados")
    op.drop_table("movimientos_ignorados")

    op.drop_index("ix_movimientos_borrados_detalle_norm", table_name="movimientos_borrados")
    op.drop_index("ix_movimientos_borrados_unique_key", table_name="movimientos_borrados")
    op.drop_table("movimientos_borrados")

    op.drop_index("ix_categoria_map_monto_abs_clp", table_name="categoria_map")
    op.drop_index("ix_categoria_map_detalle_norm", table_name="categoria_map")
    op.drop_table("categoria_map")

    op.drop_index("ix_movimientos_detalle_norm", table_name="movimientos")
    op.drop_index("ix_movimientos_suggestion_status", table_name="movimientos")
    op.drop_index("ix_movimientos_suggested_categoria", table_name="movimientos")
    op.drop_index("ix_movimientos_categoria", table_name="movimientos")
    op.drop_index("ix_movimientos_fecha", table_name="movimientos")
    op.drop_index("ix_movimientos_unique_key", table_name="movimientos")
    op.drop_table("movimientos")

    op.drop_index("ix_categorias_nombre", table_name="categorias")
    op.drop_table("categorias")
