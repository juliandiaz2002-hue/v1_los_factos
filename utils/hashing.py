"""Funciones deterministas de hashing para llaves de negocio."""

from __future__ import annotations

import hashlib
from datetime import date


def build_unique_key(*, fecha: date, detalle_norm: str, monto_abs_clp: int) -> str:
    canonical = f"{fecha.isoformat()}|{detalle_norm.strip()}|{int(monto_abs_clp)}"
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"k:{digest[:16]}"
