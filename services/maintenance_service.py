"""Servicio de mantenimiento y confiabilidad."""

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
from sqlalchemy import select

from data.models import Categoria, CategoriaMap, Movimiento, MovimientoBorrado, MovimientoIgnorado
from data.repositories.maintenance_repo import MaintenanceRepository
from data.repositories.movimientos_repo import MovimientoRepository


class MaintenanceService:
    def __init__(self, session):
        self.session = session
        self.repo = MaintenanceRepository(session)
        self.mov_repo = MovimientoRepository(session)

    def diagnostics(self) -> dict[str, int]:
        return self.repo.diagnostics()

    def repair_inconsistent_amounts(self) -> int:
        return self.repo.repair_inconsistent_amounts()

    def list_ignored(self):
        return self.mov_repo.list_ignored()

    def restore_ignored(self, unique_key: str) -> bool:
        return self.mov_repo.restore_ignored(unique_key)

    def export_full_backup(self) -> bytes:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        buffer = io.BytesIO()

        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            self._to_df(select(Movimiento), "movimientos", writer)
            self._to_df(select(Categoria), "categorias", writer)
            self._to_df(select(CategoriaMap), "categoria_map", writer)
            self._to_df(select(MovimientoBorrado), "movimientos_borrados", writer)
            self._to_df(select(MovimientoIgnorado), "movimientos_ignorados", writer)

        buffer.seek(0)
        return buffer.read()

    def _to_df(self, stmt, sheet_name: str, writer) -> None:
        rows = self.session.execute(stmt).scalars().all()
        dict_rows = [item.__dict__ for item in rows]
        for row in dict_rows:
            row.pop("_sa_instance_state", None)
        df = pd.DataFrame(dict_rows)
        if df.empty:
            df = pd.DataFrame(columns=["empty"])
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
