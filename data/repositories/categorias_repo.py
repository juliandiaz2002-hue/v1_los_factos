"""Repositorio de categorias."""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from data.models import Categoria, CategoriaMap, Movimiento
from utils.constants import DEFAULT_CATEGORY_NAME
from utils.normalization import normalize_text


class CategoriaRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_active(self) -> list[Categoria]:
        stmt = select(Categoria).where(Categoria.activa.is_(True)).order_by(Categoria.nombre.asc())
        return list(self.session.scalars(stmt).all())

    def get_or_create(self, name: str) -> Categoria:
        cleaned = name.strip() or DEFAULT_CATEGORY_NAME
        existing = self.session.scalar(select(Categoria).where(Categoria.nombre == cleaned))
        if existing:
            if not existing.activa:
                existing.activa = True
            return existing

        category = Categoria(nombre=cleaned, activa=True)
        self.session.add(category)
        self.session.flush()
        return category

    def ensure_default_category(self) -> Categoria:
        return self.get_or_create(DEFAULT_CATEGORY_NAME)

    def add_category(self, name: str) -> Categoria:
        return self.get_or_create(name)

    def rename_category(self, category_id: int, new_name: str) -> Categoria:
        category = self.session.get(Categoria, category_id)
        if not category:
            raise ValueError("Categoria no encontrada")
        category.nombre = new_name.strip()
        self.session.flush()
        return category

    def delete_category_and_reassign(self, category_id: int, reassign_name: str = DEFAULT_CATEGORY_NAME) -> None:
        category = self.session.get(Categoria, category_id)
        if not category:
            raise ValueError("Categoria no encontrada")

        normalized_reassign = normalize_text(reassign_name)
        target = self.session.scalar(
            select(Categoria).where(Categoria.nombre == reassign_name)
        )
        if not target:
            target = Categoria(nombre=reassign_name, activa=True)
            self.session.add(target)
            self.session.flush()

        if normalize_text(category.nombre) == normalized_reassign:
            return

        self.session.execute(
            update(Movimiento)
            .where(Movimiento.categoria_id == category.id)
            .values(categoria_id=target.id)
        )
        self.session.execute(
            update(CategoriaMap)
            .where(CategoriaMap.categoria_id == category.id)
            .values(categoria_id=target.id)
        )
        category.activa = False
