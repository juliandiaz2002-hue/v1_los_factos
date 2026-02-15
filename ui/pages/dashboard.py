"""Pagina principal de insights."""

from __future__ import annotations

from calendar import monthrange
import re
from datetime import date

import pandas as pd
import streamlit as st

from charts import (
    PLOTLY_AVAILABLE,
    category_distribution_chart,
    month_comparison_by_category_chart,
    monthly_trend_chart,
    projection_horizon_chart,
    projection_chart,
)
from services.dashboard_service import DashboardFilters, DashboardService
from ui.components import render_filter_chips, render_insight_card, render_kpi_card
from ui.pages.common import render_movement_filters
from utils.constants import MOVEMENT_TYPE_EXPENSE
from utils.formatting import format_clp

MONTH_SHORT = {
    1: "Ene",
    2: "Feb",
    3: "Mar",
    4: "Abr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dic",
}


def _render_chart_header(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="lf-chart-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="lf-chart-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def _render_section_header(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="lf-section-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="lf-section-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def _plotly_interactive_config() -> dict:
    return {
        "displaylogo": False,
        "responsive": True,
        "scrollZoom": False,
        "modeBarButtonsToRemove": [
            "lasso2d",
            "select2d",
            "pan2d",
            "zoom2d",
            "zoomIn2d",
            "zoomOut2d",
            "autoScale2d",
            "resetScale2d",
            "toggleSpikelines",
        ],
    }


def _period_label(period: pd.Period) -> str:
    return f"{MONTH_SHORT.get(int(period.month), str(period.month))} {str(period.year)[2:]}"


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _calibrate_recurrence_params(
    *,
    previous_months: pd.Series,
    by_cat_month: pd.DataFrame,
    lookback_periods: pd.PeriodIndex,
    sensitivity_mode: str,
) -> dict[str, float]:
    mode = (sensitivity_mode or "Balanceado").strip().lower()
    defaults = {
        "high_threshold": 0.60,
        "mid_threshold": 0.35,
        "high_weight": 0.95,
        "mid_weight": 0.55,
        "low_weight": 0.15,
        "low_recurrence_multiplier": 0.40,
        "spike_peak_factor": 1.30,
        "spike_avg_factor": 1.80,
    }

    if by_cat_month.empty or len(lookback_periods) == 0:
        calibrated = defaults.copy()
    else:
        rec_scores = ((by_cat_month > 0).sum(axis=1) / max(len(lookback_periods), 1)).astype(float)
        rec_q40 = float(rec_scores.quantile(0.40)) if not rec_scores.empty else defaults["mid_threshold"]
        rec_q75 = float(rec_scores.quantile(0.75)) if not rec_scores.empty else defaults["high_threshold"]

        mean_prev = float(previous_months.mean()) if not previous_months.empty else 0.0
        cv_prev = (
            float(previous_months.std(ddof=0) / mean_prev)
            if len(previous_months) >= 2 and mean_prev > 0
            else 0.45
        )
        stability = _clamp(1 - cv_prev, 0.2, 1.0)

        high_threshold = _clamp(max(0.55, rec_q75), 0.55, 0.85)
        mid_threshold = _clamp(min(high_threshold - 0.10, max(0.22, rec_q40)), 0.22, 0.62)
        high_weight = _clamp(0.78 + (stability * 0.18), 0.75, 0.98)
        mid_weight = _clamp(0.42 + (stability * 0.16), 0.34, 0.72)
        low_weight = _clamp(0.09 + (stability * 0.08), 0.08, 0.24)
        low_recurrence_multiplier = _clamp(0.45 - ((1 - stability) * 0.12), 0.25, 0.50)
        spike_peak_factor = _clamp(1.15 + ((1 - stability) * 0.35), 1.10, 1.65)
        spike_avg_factor = _clamp(1.55 + ((1 - stability) * 0.45), 1.40, 2.10)

        calibrated = {
            "high_threshold": high_threshold,
            "mid_threshold": mid_threshold,
            "high_weight": high_weight,
            "mid_weight": mid_weight,
            "low_weight": low_weight,
            "low_recurrence_multiplier": low_recurrence_multiplier,
            "spike_peak_factor": spike_peak_factor,
            "spike_avg_factor": spike_avg_factor,
        }

    if mode == "conservador":
        calibrated["high_threshold"] = _clamp(calibrated["high_threshold"] + 0.05, 0.58, 0.90)
        calibrated["mid_threshold"] = _clamp(calibrated["mid_threshold"] + 0.03, 0.24, 0.70)
        calibrated["high_weight"] = _clamp(calibrated["high_weight"] * 0.88, 0.65, 0.95)
        calibrated["mid_weight"] = _clamp(calibrated["mid_weight"] * 0.82, 0.28, 0.68)
        calibrated["low_weight"] = _clamp(calibrated["low_weight"] * 0.70, 0.05, 0.20)
        calibrated["low_recurrence_multiplier"] = _clamp(
            calibrated["low_recurrence_multiplier"] * 0.82, 0.20, 0.50
        )
    elif mode == "agresivo":
        calibrated["high_threshold"] = _clamp(calibrated["high_threshold"] - 0.05, 0.50, 0.82)
        calibrated["mid_threshold"] = _clamp(calibrated["mid_threshold"] - 0.03, 0.18, 0.58)
        calibrated["high_weight"] = _clamp(calibrated["high_weight"] * 1.08, 0.78, 1.05)
        calibrated["mid_weight"] = _clamp(calibrated["mid_weight"] * 1.12, 0.34, 0.84)
        calibrated["low_weight"] = _clamp(calibrated["low_weight"] * 1.20, 0.08, 0.28)
        calibrated["low_recurrence_multiplier"] = _clamp(
            calibrated["low_recurrence_multiplier"] * 1.08, 0.25, 0.62
        )

    calibrated["mode"] = mode
    return calibrated


def _build_projection_insights(
    *,
    comparison: dict[str, float],
    comparison_cutoff_day: int,
    projection_bundle: dict,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    risk_pct = float(projection_bundle["risk_pct"])
    delta_vs_baseline = float(projection_bundle["delta_vs_baseline"])
    top_category_name = str(projection_bundle["top_category_name"])
    top_category_share = float(projection_bundle["top_category_share"])
    category_projection_df = projection_bundle["category_projection_df"]
    next_month_projection = float(projection_bundle["next_month_projection"])
    second_month_projection = float(projection_bundle["second_month_projection"])
    third_month_projection = float(projection_bundle["third_month_projection"])

    current = float(comparison["current"])
    previous = float(comparison["previous"])
    variation_pct = float(comparison["variation_pct"])
    if variation_pct > 0:
        comparison_phrase = "subio"
    elif variation_pct < 0:
        comparison_phrase = "bajo"
    else:
        comparison_phrase = "se mantuvo"

    if risk_pct > 0:
        risk_copy = f"Riesgo de cierre: +{risk_pct:.1f}% vs promedio reciente ({format_clp(delta_vs_baseline)})."
    elif risk_pct < 0:
        risk_copy = f"Cierre bajo el promedio: {risk_pct:.1f}% ({format_clp(abs(delta_vs_baseline))})."
    else:
        risk_copy = "Cierre alineado con el promedio reciente."

    if top_category_share > 0:
        concentration_copy = (
            f"{top_category_name} concentraria {top_category_share * 100:.1f}% del cierre proyectado."
        )
    else:
        concentration_copy = "Todavia no hay una categoria claramente dominante en la proyeccion."

    core = [
        {
            "title": "Core 1: Ritmo al dia",
            "body": (
                f"Dia {comparison_cutoff_day}: {format_clp(current)} vs {format_clp(previous)} "
                f"(mes anterior). El gasto {comparison_phrase} {abs(variation_pct):.1f}%."
            ),
            "explanation": (
                "Compara el mes filtrado contra el anterior usando el mismo corte de dias del calendario."
            ),
            "icon": "speed",
            "variant": "core",
        },
        {
            "title": "Core 2: Riesgo de cierre",
            "body": risk_copy,
            "explanation": (
                "Riesgo = (cierre proyectado - promedio ultimos 3 meses) / promedio ultimos 3 meses."
            ),
            "icon": "warning",
            "variant": "core",
        },
        {
            "title": "Core 3: Concentracion",
            "body": concentration_copy,
            "explanation": (
                "Mide la concentracion de gasto en la categoria con mayor peso dentro del cierre proyectado."
            ),
            "icon": "donut_large",
            "variant": "core",
        },
    ]

    dynamic_candidates: list[dict[str, str | int]] = []
    if risk_pct >= 12:
        dynamic_candidates.append(
            {
                "priority": 100,
                "title": "Dinamico: Alerta de sobregasto",
                "body": (
                    f"Para volver a tu promedio, necesitas recortar ~{format_clp(abs(delta_vs_baseline))} "
                    "en lo que queda del mes."
                ),
                "explanation": "Se activa cuando la proyeccion supera en al menos 12% el promedio reciente.",
                "icon": "trending_up",
                "variant": "dynamic",
            }
        )
    elif risk_pct <= -12:
        dynamic_candidates.append(
            {
                "priority": 95,
                "title": "Dinamico: Colchon favorable",
                "body": (
                    f"Vas por debajo de tu ritmo historico. Margen potencial: {format_clp(abs(delta_vs_baseline))}."
                ),
                "explanation": "Se activa cuando la proyeccion queda 12% o mas por debajo del promedio reciente.",
                "icon": "savings",
                "variant": "dynamic",
            }
        )

    if top_category_share >= 0.42 and top_category_name != "Sin datos":
        dynamic_candidates.append(
            {
                "priority": 90,
                "title": "Dinamico: Dependencia alta",
                "body": (
                    f"Casi la mitad del cierre depende de {top_category_name}. "
                    "Controlar esa categoria mueve el resultado total."
                ),
                "explanation": "Se activa cuando la categoria lider supera 42% de la proyeccion.",
                "icon": "hub",
                "variant": "dynamic",
            }
        )

    if not category_projection_df.empty:
        sporadic = category_projection_df[
            (category_projection_df["recurrencia_label"] == "Baja")
            & (category_projection_df["gasto_actual"] > 0)
        ].copy()
        if not sporadic.empty:
            sporadic = sporadic.sort_values("gasto_actual", ascending=False)
            top_sporadic = sporadic.iloc[0]
            dynamic_candidates.append(
                {
                    "priority": 85,
                    "title": "Dinamico: Pico esporadico",
                    "body": (
                        f"{top_sporadic['categoria']} aparece como gasto puntual alto. "
                        "La proyeccion lo penaliza para no sobreestimar meses futuros."
                    ),
                    "explanation": (
                        "Detecta categorias de baja recurrencia con ticket alto y reduce su crecimiento esperado."
                    ),
                    "icon": "auto_awesome",
                    "variant": "dynamic",
                }
            )

    dynamic_candidates.append(
        {
            "priority": 70,
            "title": "Dinamico: Ventana 90 dias",
            "body": (
                f"Escenario esperado: {format_clp(next_month_projection)} -> {format_clp(second_month_projection)} "
                f"-> {format_clp(third_month_projection)}."
            ),
            "explanation": (
                "Proyeccion de 3 meses hacia adelante anclada al cierre estimado del mes seleccionado."
            ),
            "icon": "timeline",
            "variant": "dynamic",
        }
    )

    ordered = sorted(dynamic_candidates, key=lambda item: int(item["priority"]), reverse=True)
    selected_dynamic = [
        {
            "title": str(item["title"]),
            "body": str(item["body"]),
            "explanation": str(item["explanation"]),
            "icon": str(item.get("icon", "insights")),
            "variant": str(item.get("variant", "dynamic")),
        }
        for item in ordered[:2]
    ]

    while len(selected_dynamic) < 2:
        selected_dynamic.append(
            {
                "title": "Dinamico: Sin alerta",
                "body": "No se detectaron desvíos criticos fuera de tu rango habitual.",
                "explanation": "Este bloque se completa cuando no hay eventos dinamicos prioritarios.",
                "icon": "check_circle",
                "variant": "dynamic",
            }
        )

    return core, selected_dynamic


def _get_top_place(df: pd.DataFrame) -> str:
    if df.empty or "detalle" not in df.columns:
        return "Sin datos"
    details = df["detalle"].fillna("").astype(str).str.strip()
    details = details[details != ""]
    if details.empty:
        return "Sin datos"
    top_place = str(details.value_counts().index[0])
    cleaned = re.sub(r"[^A-Za-z0-9 ]+", " ", top_place)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return "Sin datos"
    cleaned = cleaned.title()
    return cleaned if len(cleaned) <= 20 else f"{cleaned[:17]}..."


def _build_history_filters(filters, *, selected_year: int, selected_month: int) -> DashboardFilters:
    selected_period = pd.Period(year=selected_year, month=selected_month, freq="M")
    lookback_start_period = selected_period - 7
    lookback_start = date(lookback_start_period.year, lookback_start_period.month, 1)

    if filters.date_to:
        cutoff = filters.date_to
    else:
        cutoff = date(selected_year, selected_month, monthrange(selected_year, selected_month)[1])

    if filters.date_from:
        history_start = min(filters.date_from, lookback_start)
    else:
        history_start = lookback_start

    return DashboardFilters(
        text_filter=filters.text_filter,
        month=None,
        year=None,
        date_from=history_start,
        date_to=cutoff,
        category_id=filters.category_id,
    )


def _month_comparison_from_history(
    df: pd.DataFrame,
    *,
    year: int,
    month: int,
    day_cutoff: int,
) -> dict[str, float]:
    if df.empty:
        return {"current": 0.0, "previous": 0.0, "variation_pct": 0.0}

    work = df.copy()
    work["fecha"] = pd.to_datetime(work["fecha"])
    work = work[work["fecha"].dt.day <= int(day_cutoff)]
    if work.empty:
        return {"current": 0.0, "previous": 0.0, "variation_pct": 0.0}

    periods = work["fecha"].dt.to_period("M")
    current_period = pd.Period(year=year, month=month, freq="M")
    previous_period = current_period - 1

    current = float(work.loc[periods == current_period, "monto_abs_clp"].sum())
    previous = float(work.loc[periods == previous_period, "monto_abs_clp"].sum())
    variation_pct = ((current - previous) / previous * 100) if previous else 0.0
    return {"current": current, "previous": previous, "variation_pct": variation_pct}


def _build_projection_bundle(
    *,
    df_history: pd.DataFrame,
    df_period: pd.DataFrame,
    projection_df: pd.DataFrame,
    selected_year: int,
    selected_month: int,
    sensitivity_mode: str,
) -> dict:
    del projection_df  # la proyeccion ahora se calcula con recurrencia historica
    selected_period = pd.Period(year=selected_year, month=selected_month, freq="M")
    days_in_month = monthrange(selected_year, selected_month)[1]
    current_total = float(df_period["monto_abs_clp"].sum()) if not df_period.empty else 0.0
    today_period = pd.Period(date.today(), freq="M")
    month_is_complete = selected_period < today_period
    progress_day = days_in_month if month_is_complete else min(date.today().day, days_in_month)
    progress_pct = min(1.0, progress_day / days_in_month) if days_in_month else 0.0
    remaining_ratio = max(0.0, 1 - progress_pct)

    if df_history.empty:
        history = pd.DataFrame(columns=["fecha", "categoria", "monto_abs_clp"])
    else:
        history = df_history.copy()
        history["fecha"] = pd.to_datetime(history["fecha"])

    if not history.empty:
        history["period"] = history["fecha"].dt.to_period("M")
        monthly_totals = history.groupby("period")["monto_abs_clp"].sum().sort_index()
    else:
        monthly_totals = pd.Series(dtype="float64")

    lookback_len = 6
    lookback_periods = pd.period_range(start=selected_period - lookback_len, end=selected_period - 1, freq="M")
    previous_months = monthly_totals.reindex(lookback_periods, fill_value=0.0) if len(lookback_periods) else pd.Series(dtype="float64")
    baseline = float(previous_months.tail(3).mean()) if not previous_months.empty else float(current_total)
    volatility = float(previous_months.std(ddof=0)) if len(previous_months) >= 2 else float(max(baseline * 0.08, 1))

    if not history.empty:
        by_cat_month = (
            history[history["period"] < selected_period]
            .groupby(["categoria", "period"])["monto_abs_clp"]
            .sum()
            .unstack(fill_value=0.0)
        )
    else:
        by_cat_month = pd.DataFrame()

    if len(lookback_periods):
        by_cat_month = by_cat_month.reindex(columns=lookback_periods, fill_value=0.0)

    calibration = _calibrate_recurrence_params(
        previous_months=previous_months,
        by_cat_month=by_cat_month,
        lookback_periods=lookback_periods,
        sensitivity_mode=sensitivity_mode,
    )
    high_threshold = float(calibration["high_threshold"])
    mid_threshold = float(calibration["mid_threshold"])
    high_weight = float(calibration["high_weight"])
    mid_weight = float(calibration["mid_weight"])
    low_weight = float(calibration["low_weight"])
    low_recurrence_multiplier = float(calibration["low_recurrence_multiplier"])
    spike_peak_factor = float(calibration["spike_peak_factor"])
    spike_avg_factor = float(calibration["spike_avg_factor"])

    if df_period.empty:
        current_by_cat = pd.Series(dtype="float64")
    else:
        current_by_cat = df_period.groupby("categoria")["monto_abs_clp"].sum()

    recurring_candidates: list[str] = []
    if not by_cat_month.empty:
        recurrence_ref = (by_cat_month > 0).sum(axis=1) / max(len(lookback_periods), 1)
        recurring_candidates = recurrence_ref[recurrence_ref >= high_threshold].index.tolist()
    category_pool = sorted(set(current_by_cat.index.tolist()) | set(recurring_candidates))

    rows: list[dict] = []
    for category in category_pool:
        current_value = float(current_by_cat.get(category, 0.0))
        if category in by_cat_month.index and len(lookback_periods):
            series = by_cat_month.loc[category].reindex(lookback_periods, fill_value=0.0)
            active_months = int((series > 0).sum())
            recurrence = active_months / len(lookback_periods)
            avg_monthly = float(series.mean())
            peak_monthly = float(series.max())
        else:
            active_months = 0
            recurrence = 0.0
            avg_monthly = 0.0
            peak_monthly = 0.0

        if month_is_complete:
            projected_value = current_value
        else:
            if recurrence >= high_threshold:
                expected_remaining = avg_monthly * remaining_ratio * high_weight
            elif recurrence >= mid_threshold:
                expected_remaining = avg_monthly * remaining_ratio * mid_weight
            else:
                expected_remaining = avg_monthly * remaining_ratio * low_weight

            if current_value == 0 and recurrence < 0.5:
                expected_remaining = 0.0
            if recurrence < mid_threshold:
                expected_remaining *= low_recurrence_multiplier

            sporadic_spike = recurrence < mid_threshold and current_value > max(
                peak_monthly * spike_peak_factor,
                avg_monthly * spike_avg_factor,
                1,
            )
            if sporadic_spike:
                expected_remaining = 0.0

            projected_value = current_value + max(0.0, expected_remaining)

        projected_value = max(current_value, projected_value)
        if projected_value <= 0 and current_value <= 0:
            continue

        if recurrence >= high_threshold:
            rec_label = "Alta"
        elif recurrence >= mid_threshold:
            rec_label = "Media"
        else:
            rec_label = "Baja"

        rows.append(
            {
                "categoria": str(category),
                "gasto_actual": current_value,
                "proyeccion": float(projected_value),
                "recurrencia_score": float(recurrence),
                "recurrencia_label": rec_label,
                "meses_activos": int(active_months),
            }
        )

    effective_projection = pd.DataFrame.from_records(rows)
    if effective_projection.empty:
        effective_projection = pd.DataFrame(
            columns=[
                "categoria",
                "gasto_actual",
                "proyeccion",
                "recurrencia_score",
                "recurrencia_label",
                "meses_activos",
            ]
        )

    if not effective_projection.empty:
        effective_projection = effective_projection.sort_values("proyeccion", ascending=False).reset_index(drop=True)

    projected_close = float(effective_projection["proyeccion"].sum()) if not effective_projection.empty else float(current_total)
    projected_close = max(projected_close, current_total)

    growth_series = previous_months.pct_change().replace([float("inf"), float("-inf")], 0).dropna()
    avg_growth = float(growth_series.tail(4).mean()) if not growth_series.empty else 0.0
    avg_growth = max(-0.20, min(0.20, avg_growth))

    anchor = float(projected_close if projected_close > 0 else baseline)
    next_1 = max(0.0, anchor * (1 + (avg_growth * 0.55)))
    next_2 = max(0.0, next_1 * (1 + (avg_growth * 0.50)))
    next_3 = max(0.0, next_2 * (1 + (avg_growth * 0.45)))

    prev_period = selected_period - 1
    prev_total = float(monthly_totals.get(prev_period, 0.0))
    vol_base = float(max(volatility, projected_close * 0.08, 1.0))
    horizon_rows = [
        {
            "mes": _period_label(prev_period),
            "real": float(prev_total),
            "proyeccion": None,
            "banda_inf": None,
            "banda_sup": None,
        },
        {
            "mes": _period_label(selected_period),
            "real": float(current_total),
            "proyeccion": float(projected_close),
            "banda_inf": max(0.0, float(projected_close) - (vol_base * 0.8)),
            "banda_sup": float(projected_close) + (vol_base * 0.8),
        },
    ]
    for offset, value in enumerate([next_1, next_2, next_3], start=1):
        margin = max(vol_base * (1 + (offset * 0.1)), value * 0.10, 1.0)
        horizon_rows.append(
            {
                "mes": _period_label(selected_period + offset),
                "real": None,
                "proyeccion": float(value),
                "banda_inf": max(0.0, float(value) - margin),
                "banda_sup": float(value) + margin,
            }
        )
    horizon_df = pd.DataFrame.from_records(horizon_rows)

    top_category_name = "Sin datos"
    top_category_share = 0.0
    if not effective_projection.empty and projected_close > 0:
        top = effective_projection.iloc[0]
        top_category_name = str(top["categoria"])
        top_category_share = float(top["proyeccion"]) / float(projected_close)

    risk_pct = ((projected_close - baseline) / baseline * 100) if baseline else 0.0
    delta_vs_baseline = float(projected_close - baseline)

    methodology_summary = (
        "Cierre proyectado = gasto acumulado + aporte esperado por recurrencia historica de cada categoria."
    )
    methodology_detail = (
        "Se analiza cada categoria en los ultimos 6 meses para estimar recurrencia (meses activos/6). "
        f"En modo {calibration['mode']}, los umbrales calibrados quedan en Alta>={high_threshold:.2f} y "
        f"Media>={mid_threshold:.2f}. Categorias de recurrencia baja tienen aporte futuro reducido "
        "y, si muestran ticket esporadico alto, no se agrega crecimiento adicional. "
        "El escenario 90 dias usa ese cierre estimado como ancla y proyecta 3 meses "
        "con tendencia reciente y una banda de incertidumbre."
    )

    return {
        "current_total": current_total,
        "projected_close": float(projected_close),
        "progress_pct": float(progress_pct),
        "baseline": float(baseline),
        "risk_pct": float(risk_pct),
        "delta_vs_baseline": delta_vs_baseline,
        "next_month_projection": float(next_1),
        "second_month_projection": float(next_2),
        "third_month_projection": float(next_3),
        "top_category_name": top_category_name,
        "top_category_share": float(top_category_share),
        "horizon_df": horizon_df,
        "category_projection_df": effective_projection,
        "methodology_summary": methodology_summary,
        "methodology_detail": methodology_detail,
        "calibration": calibration,
    }


def render_dashboard_page(session) -> None:
    service = DashboardService(session)
    categories = service.list_categories()
    sensitivity_labels = ["Conservador", "Balanceado", "Agresivo"]
    current_sensitivity = st.session_state.get("dashboard_projection_sensitivity", "Balanceado")
    if current_sensitivity not in sensitivity_labels:
        current_sensitivity = "Balanceado"
    with st.expander("Filtros", expanded=False):
        filters, active_filters = render_movement_filters(
            categories,
            key_prefix="dashboard",
            show_title=False,
        )
        projection_sensitivity = st.selectbox(
            "Sensibilidad de proyeccion",
            options=sensitivity_labels,
            index=sensitivity_labels.index(current_sensitivity),
            key="dashboard_projection_sensitivity",
            help=(
                "Conservador reduce crecimiento esperado en categorias inestables. "
                "Agresivo proyecta mayor continuidad. Balanceado usa calibracion intermedia."
            ),
        )
    render_filter_chips(active_filters)

    dash_filters = DashboardFilters(
        text_filter=filters.text_filter,
        month=filters.month,
        year=filters.year,
        date_from=filters.date_from,
        date_to=filters.date_to,
        category_id=filters.category_id,
    )
    df_period = service.get_movements_df(dash_filters)
    df_period = df_period[df_period["tipo_movimiento"] == MOVEMENT_TYPE_EXPENSE].copy()

    selected_year = filters.year or (filters.date_to.year if filters.date_to else date.today().year)
    selected_month = filters.month or (filters.date_to.month if filters.date_to else date.today().month)
    comparison_cutoff_day = min(date.today().day, monthrange(selected_year, selected_month)[1])

    history_filters = _build_history_filters(
        filters,
        selected_year=selected_year,
        selected_month=selected_month,
    )
    df_history = service.get_movements_df(history_filters)
    df_history = df_history[df_history["tipo_movimiento"] == MOVEMENT_TYPE_EXPENSE].copy()

    kpis = service.get_kpis(df_period)
    comparison = _month_comparison_from_history(
        df_history,
        year=selected_year,
        month=selected_month,
        day_cutoff=comparison_cutoff_day,
    )
    projection_df = service.get_projection_by_stable_categories(
        df_period,
        year=selected_year,
        month=selected_month,
    )
    projection_bundle = _build_projection_bundle(
        df_history=df_history,
        df_period=df_period,
        projection_df=projection_df,
        selected_year=selected_year,
        selected_month=selected_month,
        sensitivity_mode=projection_sensitivity,
    )

    monthly_avg = 0.0
    if not df_history.empty:
        month_group = df_history.copy()
        month_group["fecha"] = pd.to_datetime(month_group["fecha"])
        monthly_avg = float(month_group.groupby(month_group["fecha"].dt.to_period("M"))["monto_abs_clp"].sum().mean())

    days = int(pd.to_datetime(df_period["fecha"]).dt.date.nunique()) if not df_period.empty else 0
    avg_daily = (kpis["total_gasto"] / days) if days > 0 else 0

    variation_pct = float(comparison["variation_pct"])
    variation_amt = float(comparison["current"] - comparison["previous"])
    if variation_pct == 0:
        variation_tone = "neutral"
    elif variation_pct > 0:
        variation_tone = "negative"
    else:
        variation_tone = "positive"
    variation_arrow = "↑" if variation_pct > 0 else ("↓" if variation_pct < 0 else "→")
    top_place = _get_top_place(df_period)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        render_kpi_card(
            "Gasto Total",
            format_clp(kpis["total_gasto"]),
            delta=f"{variation_arrow} {abs(variation_pct):.1f}% vs mes anterior (dia {comparison_cutoff_day})",
            icon="account_balance_wallet",
            icon_color="#525252",
            delta_tone=variation_tone,
        )
    with col2:
        render_kpi_card("Promedio Diario", format_clp(avg_daily), icon="monitoring", icon_color="#8B5CF6")
    with col3:
        render_kpi_card("Promedio Mensual", format_clp(monthly_avg), icon="trending_up", icon_color="#10B981")
    with col4:
        render_kpi_card(
            "Variacion Mensual",
            f"{variation_pct:+.1f}%",
            delta=f"{variation_arrow} {format_clp(abs(variation_amt))}",
            icon="trending_down",
            icon_color="#EF4444" if variation_pct > 0 else "#10B981",
            delta_tone=variation_tone,
        )
    with col5:
        render_kpi_card("Lugar Top", top_place, icon="location_on", icon_color="#F59E0B", value_compact=True)

    insight_cols = st.columns(2)
    with insight_cols[0]:
        if variation_pct > 0:
            variation_phrase = "subio"
        elif variation_pct < 0:
            variation_phrase = "bajo"
        else:
            variation_phrase = "se mantuvo"
        render_insight_card(
            f"Comparacion al dia {comparison_cutoff_day}",
            (
                f"Mes seleccionado: {format_clp(comparison['current'])} | "
                f"Mes anterior (mismo dia): {format_clp(comparison['previous'])} | "
                f"El gasto {variation_phrase} {abs(variation_pct):.1f}%."
            ),
            explanation=(
                "Compara ambos meses hasta el mismo dia del calendario. "
                "Ejemplo: si hoy es dia 14, compara del dia 1 al 14 en ambos meses."
            ),
        )
    with insight_cols[1]:
        if df_period.empty:
            body = "No hay suficientes movimientos en el periodo para generar lectura."
        else:
            top_category_period = (
                df_period.groupby("categoria", as_index=False)["monto_abs_clp"]
                .sum()
                .sort_values("monto_abs_clp", ascending=False)
            )
            top_row = top_category_period.iloc[0]
            body = (
                f"Categoria dominante del periodo: {top_row['categoria']} "
                f"({format_clp(top_row['monto_abs_clp'])})."
            )
        render_insight_card(
            "Lectura rapida del periodo",
            body,
            explanation="Resume la categoria de mayor gasto observado dentro del periodo filtrado.",
        )

    if df_period.empty and df_history.empty:
        st.info("No hay movimientos para los filtros seleccionados.")
        return

    _render_section_header(
        "Analitica del periodo",
        "Comportamiento real del mes seleccionado y contexto comparativo.",
    )

    if PLOTLY_AVAILABLE:
        chart_config = _plotly_interactive_config()
        c1, c2, c3 = st.columns(3)
        with c1:
            with st.container(border=True):
                head1, head2 = st.columns([3.0, 1.2])
                with head1:
                    _render_chart_header("Distribucion por Categoria", "Total gastado este mes por categoria")
                with head2:
                    dist_top_n = st.selectbox(
                        "Top categorias distribucion",
                        options=[5, 8, 10],
                        index=1,
                        format_func=lambda value: f"Top {value}",
                        key="dashboard_dist_top_n",
                        label_visibility="collapsed",
                    )
                st.plotly_chart(
                    category_distribution_chart(
                        df_period,
                        top_n=dist_top_n,
                        include_other=True,
                    ),
                    use_container_width=True,
                    config=chart_config,
                )
        with c2:
            with st.container(border=True):
                head1, head2 = st.columns([3.2, 1.2])
                with head1:
                    _render_chart_header("Tendencia Mensual", "Gastos vs presupuesto")
                with head2:
                    trend_period = st.selectbox(
                        "Periodo tendencia",
                        options=[3, 6, 12],
                        index=1,
                        format_func=lambda value: f"{value} meses",
                        key="dashboard_trend_period",
                        label_visibility="collapsed",
                    )
                st.plotly_chart(
                    monthly_trend_chart(
                        df_history,
                        periods=trend_period,
                        target_year=selected_year,
                        target_month=selected_month,
                    ),
                    use_container_width=True,
                    config=chart_config,
                )
        with c3:
            with st.container(border=True):
                head1, head2 = st.columns([3.0, 1.2])
                with head1:
                    _render_chart_header(
                        "Comparacion Mensual",
                        f"Hasta dia {comparison_cutoff_day}: mes seleccionado vs anterior",
                    )
                with head2:
                    comp_top_n = st.selectbox(
                        "Top categorias comparacion",
                        options=[4, 6, 8],
                        index=1,
                        format_func=lambda value: f"Top {value}",
                        key="dashboard_comp_top_n",
                        label_visibility="collapsed",
                    )
                st.plotly_chart(
                    month_comparison_by_category_chart(
                        df_history,
                        target_year=selected_year,
                        target_month=selected_month,
                        day_cutoff=comparison_cutoff_day,
                        top_n=comp_top_n,
                    ),
                    use_container_width=True,
                    config=chart_config,
                )

    else:
        st.warning("Plotly no esta instalado. Mostrando graficos de compatibilidad para prueba local.")

        c1, c2, c3 = st.columns(3)
        with c1:
            dist = df_period.groupby("categoria", as_index=False)["monto_abs_clp"].sum().set_index("categoria")
            st.bar_chart(dist)
        with c2:
            trend = df_history.copy()
            trend["fecha"] = pd.to_datetime(trend["fecha"])
            trend["mes"] = trend["fecha"].dt.to_period("M").astype(str)
            month_df = trend.groupby("mes", as_index=False)["monto_abs_clp"].sum().set_index("mes")
            st.line_chart(month_df)
        with c3:
            comp = df_history.groupby("categoria", as_index=False)["monto_abs_clp"].sum().head(8).set_index("categoria")
            st.bar_chart(comp)

    _render_section_header(
        "Proyecciones e Insights",
        "Escenarios de cierre y senales accionables para anticipar decisiones.",
    )
    st.markdown(
        """
<div class="lf-projection-banner">
  <span class="icon">insights</span>
  <div>
    <div class="title">Centro de proyeccion financiera</div>
    <div class="copy">Lecturas de riesgo, concentracion y tendencia futura para tomar decisiones accionables.</div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    projected_close = projection_bundle["projected_close"]
    baseline = projection_bundle["baseline"]
    risk_pct = projection_bundle["risk_pct"]
    delta_vs_baseline = projection_bundle["delta_vs_baseline"]
    next_month_projection = projection_bundle["next_month_projection"]
    progress_pct = projection_bundle["progress_pct"]
    calibration = projection_bundle["calibration"]
    core_insights, dynamic_insights = _build_projection_insights(
        comparison=comparison,
        comparison_cutoff_day=comparison_cutoff_day,
        projection_bundle=projection_bundle,
    )

    proj_summary_cols = st.columns(3)
    with proj_summary_cols[0]:
        render_insight_card(
            "Cierre proyectado del mes",
            (
                f"{format_clp(projected_close)} estimado al cierre. "
                f"Progreso del mes: {progress_pct * 100:.0f}%."
            ),
            explanation=(
                "Se calcula desde el gasto acumulado y el aporte esperado de cada categoria segun su recurrencia historica."
            ),
            icon="target",
            variant="projection",
        )
    with proj_summary_cols[1]:
        render_insight_card(
            "Escenario proximo mes",
            (
                f"Proyeccion: {format_clp(next_month_projection)}. "
                f"Promedio reciente (3m): {format_clp(baseline)}."
            ),
            explanation=(
                "Parte del cierre proyectado actual y aplica la tendencia promedio reciente para estimar el siguiente mes."
            ),
            icon="timeline",
            variant="projection",
        )
    with proj_summary_cols[2]:
        if risk_pct > 0:
            risk_copy = f"Riesgo de cierre sobre promedio: +{risk_pct:.1f}% ({format_clp(delta_vs_baseline)})."
        elif risk_pct < 0:
            risk_copy = f"Cierre bajo promedio: {risk_pct:.1f}% ({format_clp(abs(delta_vs_baseline))})."
        else:
            risk_copy = "Cierre alineado al promedio reciente."
        render_insight_card(
            "Riesgo vs promedio",
            risk_copy,
            explanation=(
                "Compara el cierre proyectado vs el promedio de los ultimos 3 meses. "
                "Positivo = riesgo de sobregasto, negativo = cierre por debajo del ritmo historico."
            ),
            icon="monitoring",
            variant="projection",
        )

    insight_row = core_insights + dynamic_insights
    insight_cols = st.columns(5)
    for column, item in zip(insight_cols, insight_row):
        with column:
            render_insight_card(
                item["title"],
                item["body"],
                explanation=item["explanation"],
                icon=item.get("icon"),
                variant=item.get("variant", "default"),
            )

    if PLOTLY_AVAILABLE:
        chart_config = _plotly_interactive_config()
        p1, p2 = st.columns([1.8, 1.2])
        with p1:
            with st.container(border=True):
                _render_chart_header(
                    "Escenario 90 dias",
                    "Mes anterior (real) + mes actual (real/proyectado) + proyeccion de 3 meses",
                )
                st.plotly_chart(
                    projection_horizon_chart(projection_bundle["horizon_df"]),
                    use_container_width=True,
                    config=chart_config,
                )
                st.caption(projection_bundle["methodology_summary"])
                with st.expander("Ver metodologia del escenario 90 dias", expanded=False):
                    st.write(projection_bundle["methodology_detail"])
                    st.write(
                        "Calibracion activa: "
                        f"Modo {calibration['mode'].capitalize()} | "
                        f"Alta>={calibration['high_threshold']:.2f}, "
                        f"Media>={calibration['mid_threshold']:.2f}, "
                        f"Pesos(H/M/B): {calibration['high_weight']:.2f}/"
                        f"{calibration['mid_weight']:.2f}/{calibration['low_weight']:.2f}."
                    )
        with p2:
            with st.container(border=True):
                head1, head2 = st.columns([3.0, 1.2])
                with head1:
                    _render_chart_header("Presion por Categoria", "Categorias con mayor peso esperado al cierre")
                with head2:
                    pressure_top_n = st.selectbox(
                        "Top presion categorias",
                        options=[5, 8, 10],
                        index=1,
                        format_func=lambda value: f"Top {value}",
                        key="dashboard_pressure_top_n",
                        label_visibility="collapsed",
                    )
                st.plotly_chart(
                    projection_chart(
                        projection_bundle["category_projection_df"],
                        top_n=pressure_top_n,
                    ),
                    use_container_width=True,
                    config=chart_config,
                )
                category_table = projection_bundle["category_projection_df"].copy()
                if not category_table.empty:
                    category_table = category_table.head(6).copy()
                    category_table["Gasto actual"] = category_table["gasto_actual"].map(format_clp)
                    category_table["Proyeccion"] = category_table["proyeccion"].map(format_clp)
                    category_table["Recurrencia"] = (category_table["recurrencia_score"] * 100).round(0).astype(int).astype(str) + "%"
                    category_table["Categoria"] = category_table["categoria"]
                    st.dataframe(
                        category_table[["Categoria", "Gasto actual", "Proyeccion", "Recurrencia", "recurrencia_label"]].rename(
                            columns={"recurrencia_label": "Nivel"}
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )
    else:
        p1, p2 = st.columns(2)
        with p1:
            horizon_fallback = projection_bundle["horizon_df"][["mes", "proyeccion"]].set_index("mes")
            st.line_chart(horizon_fallback)
        with p2:
            category_fallback = projection_bundle["category_projection_df"]
            if not category_fallback.empty:
                st.bar_chart(category_fallback.set_index("categoria")[["proyeccion"]])
