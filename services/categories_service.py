"""Servicio de gestion de categorias."""

from __future__ import annotations

from data.repositories.categorias_repo import CategoriaRepository


class CategoriesService:
    def __init__(self, session):
        self.repo = CategoriaRepository(session)

    def list_active(self):
        return self.repo.list_active()

    def add(self, name: str):
        return self.repo.add_category(name)

    def rename(self, category_id: int, new_name: str):
        return self.repo.rename_category(category_id, new_name)

    def delete(self, category_id: int):
        self.repo.delete_category_and_reassign(category_id)
