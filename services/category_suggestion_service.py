"""Sugerencias de categoria por mapa, historial y similitud."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from data.models import Categoria, Movimiento
from data.repositories.movimientos_repo import MovimientoRepository
from utils.constants import DEFAULT_CATEGORY_NAME, MOVEMENT_STATUS_ACTIVE


@dataclass
class CategorySuggestion:
    categoria: Categoria | None
    source: str
    confidence: float
    reason: str


class CategorySuggestionService:
    def __init__(self, session: Session):
        self.session = session
        self.mov_repo = MovimientoRepository(session)
        self._suggest_cache: dict[tuple[str, int], CategorySuggestion] = {}
        self._category_cache: dict[int, Categoria | None] = {}
        self._global_dominant_cache: CategorySuggestion | None = None
        self._first_active_cache: CategorySuggestion | None = None
        self._similarity_pool: list[Movimiento] | None = None

    def suggest(self, *, detalle_norm: str, monto_abs_clp: int) -> CategorySuggestion:
        cache_key = (str(detalle_norm), int(monto_abs_clp))
        cached = self._suggest_cache.get(cache_key)
        if cached is not None:
            return cached

        exact = self._by_exact_map(detalle_norm=detalle_norm, monto_abs_clp=monto_abs_clp)
        if exact:
            self._suggest_cache[cache_key] = exact
            return exact

        dominant = self._by_dominant_history(detalle_norm=detalle_norm)
        if dominant:
            self._suggest_cache[cache_key] = dominant
            return dominant

        similar = self._by_similarity(detalle_norm=detalle_norm, monto_abs_clp=monto_abs_clp)
        if similar:
            self._suggest_cache[cache_key] = similar
            return similar

        fallback_similar = self._by_similarity(
            detalle_norm=detalle_norm,
            monto_abs_clp=monto_abs_clp,
            score_threshold=0.35,
            use_amount_window=False,
            source="similarity_fallback",
            reason="Fallback por similitud relajada",
        )
        if fallback_similar:
            self._suggest_cache[cache_key] = fallback_similar
            return fallback_similar

        global_dominant = self._by_global_dominant()
        if global_dominant:
            self._suggest_cache[cache_key] = global_dominant
            return global_dominant

        first_active = self._by_first_active_category()
        if first_active:
            self._suggest_cache[cache_key] = first_active
            return first_active

        suggestion = CategorySuggestion(categoria=None, source="none", confidence=0.0, reason="Sin match")
        self._suggest_cache[cache_key] = suggestion
        return suggestion

    def _by_exact_map(self, *, detalle_norm: str, monto_abs_clp: int) -> CategorySuggestion | None:
        mapped = self.mov_repo.list_category_map_exact(detalle_norm, monto_abs_clp)
        if not mapped:
            mapped = self.mov_repo.list_category_map_exact(detalle_norm, None)
        if not mapped:
            return None

        first = mapped[0]
        category = self._get_category(int(first.categoria_id))
        if not category or not self._is_suggestible_category(category):
            return None
        confidence = min(0.99, max(0.70, float(first.confidence)))
        return CategorySuggestion(
            categoria=category,
            source="map_exact",
            confidence=confidence,
            reason="Match exacto desde categoria_map",
        )

    def _by_dominant_history(self, *, detalle_norm: str) -> CategorySuggestion | None:
        stmt = (
            select(
                Movimiento.categoria_id,
                func.count(Movimiento.id).label("freq"),
            )
            .join(Categoria, Categoria.id == Movimiento.categoria_id)
            .where(
                Movimiento.detalle_norm == detalle_norm,
                Movimiento.estado == MOVEMENT_STATUS_ACTIVE,
                Categoria.activa.is_(True),
                Categoria.nombre != DEFAULT_CATEGORY_NAME,
            )
            .group_by(Movimiento.categoria_id)
            .order_by(desc("freq"))
            .limit(2)
        )
        rows = list(self.session.execute(stmt).all())
        if not rows:
            return None

        top_cid, top_freq = rows[0]
        total = sum(int(freq) for _, freq in rows)
        ratio = float(top_freq) / float(total) if total else 0.0
        if ratio < 0.60:
            return None

        category = self._get_category(int(top_cid))
        if not category or not self._is_suggestible_category(category):
            return None

        confidence = min(0.95, 0.55 + ratio * 0.4)
        return CategorySuggestion(
            categoria=category,
            source="history_dominant",
            confidence=confidence,
            reason="Historial dominante por detalle_norm",
        )

    def _by_similarity(
        self,
        *,
        detalle_norm: str,
        monto_abs_clp: int,
        score_threshold: float = 0.82,
        use_amount_window: bool = True,
        source: str = "similarity_name_amount",
        reason: str = "Similitud por nombre + monto",
    ) -> CategorySuggestion | None:
        candidates = self._load_similarity_pool()
        if use_amount_window:
            amount_floor = max(0, int(monto_abs_clp * 0.70))
            amount_ceil = int(monto_abs_clp * 1.30) if monto_abs_clp > 0 else 0
            candidates = [
                item
                for item in candidates
                if int(item.monto_abs_clp) >= amount_floor and int(item.monto_abs_clp) <= amount_ceil
            ]
        if not candidates:
            return None

        best: tuple[float, Movimiento, Categoria] | None = None
        for item in candidates:
            category = self._get_category(int(item.categoria_id))
            if not category or not self._is_suggestible_category(category):
                continue

            text_score = SequenceMatcher(None, detalle_norm, item.detalle_norm or "").ratio()
            amount_score = 1.0 - min(1.0, abs(item.monto_abs_clp - monto_abs_clp) / max(1, monto_abs_clp))
            score = (text_score * 0.7) + (amount_score * 0.3)
            if not use_amount_window:
                score = (text_score * 0.9) + (amount_score * 0.1)
            if best is None or float(score) > float(best[0]):
                best = (float(score), item, category)

        if not best:
            return None
        score, _, category = best
        if score < score_threshold:
            return None

        confidence = float(score)
        if not use_amount_window:
            confidence = min(confidence, 0.65)

        return CategorySuggestion(
            categoria=category,
            source=source,
            confidence=round(confidence, 3),
            reason=reason,
        )

    def _by_global_dominant(self) -> CategorySuggestion | None:
        if self._global_dominant_cache is not None:
            return self._global_dominant_cache
        stmt = (
            select(
                Movimiento.categoria_id,
                func.count(Movimiento.id).label("freq"),
            )
            .join(Categoria, Categoria.id == Movimiento.categoria_id)
            .where(
                Movimiento.estado == MOVEMENT_STATUS_ACTIVE,
                Categoria.activa.is_(True),
                Categoria.nombre != DEFAULT_CATEGORY_NAME,
            )
            .group_by(Movimiento.categoria_id)
            .order_by(desc("freq"))
            .limit(1)
        )
        top = self.session.execute(stmt).first()
        if not top:
            return None

        category = self._get_category(int(top[0]))
        if not category or not self._is_suggestible_category(category):
            return None

        self._global_dominant_cache = CategorySuggestion(
            categoria=category,
            source="global_dominant_fallback",
            confidence=0.40,
            reason="Fallback por categoria dominante global",
        )
        return self._global_dominant_cache

    def _by_first_active_category(self) -> CategorySuggestion | None:
        if self._first_active_cache is not None:
            return self._first_active_cache
        stmt = (
            select(Categoria)
            .where(
                Categoria.activa.is_(True),
                Categoria.nombre != DEFAULT_CATEGORY_NAME,
            )
            .order_by(Categoria.nombre.asc())
            .limit(1)
        )
        category = self.session.scalar(stmt)
        if not category:
            return None
        self._first_active_cache = CategorySuggestion(
            categoria=category,
            source="active_category_baseline",
            confidence=0.25,
            reason="Fallback por primera categoria activa",
        )
        return self._first_active_cache

    def _load_similarity_pool(self, limit: int = 350) -> list[Movimiento]:
        if self._similarity_pool is None:
            stmt = (
                select(Movimiento)
                .where(Movimiento.estado == MOVEMENT_STATUS_ACTIVE)
                .order_by(Movimiento.fecha.desc())
                .limit(limit)
            )
            self._similarity_pool = list(self.session.scalars(stmt).all())
        return self._similarity_pool

    def _get_category(self, category_id: int) -> Categoria | None:
        if category_id in self._category_cache:
            return self._category_cache[category_id]
        category = self.session.get(Categoria, int(category_id))
        self._category_cache[category_id] = category
        return category

    @staticmethod
    def _is_suggestible_category(category: Categoria) -> bool:
        if not bool(category.activa):
            return False
        return str(category.nombre).strip().lower() != DEFAULT_CATEGORY_NAME.lower()
