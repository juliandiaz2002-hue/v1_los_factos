"""Funciones puras para construir graficos."""

from __future__ import annotations

import pandas as pd

try:
    import plotly.express as px
    import plotly.graph_objects as go
except ModuleNotFoundError:  # pragma: no cover - fallback de entorno local
    px = None
    go = None


PLOTLY_AVAILABLE = px is not None and go is not None

PALETTE = [
    "#6366F1",
    "#8B5CF6",
    "#EC4899",
    "#F59E0B",
    "#10B981",
    "#06B6D4",
    "#F43F5E",
    "#84CC16",
]

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


def _empty_chart(message: str):
    if px is None:
        return None
    return px.scatter(title=message)


def _short_label(value: str, limit: int = 14) -> str:
    text = str(value).strip()
    return text if len(text) <= limit else f"{text[: limit - 1]}…"


def _apply_figma_chart_style(fig):
    fig.update_layout(
        margin=dict(l=8, r=8, t=6, b=6),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Manrope, sans-serif", color="#171717", size=12),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.16,
            xanchor="left",
            x=0,
            font=dict(size=11),
        ),
        hovermode="x",
    )
    fig.update_xaxes(
        showgrid=False,
        linecolor="#D4D4D4",
        tickfont=dict(color="#737373", size=12),
        title="",
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#F1F1F1",
        zeroline=False,
        linecolor="#D4D4D4",
        tickfont=dict(color="#737373", size=12),
        title="",
    )
    return fig


def category_distribution_chart(df: pd.DataFrame):
    if not PLOTLY_AVAILABLE:
        return None
    if df.empty:
        return _empty_chart("Sin datos para distribucion")

    grouped = (
        df.groupby("categoria", as_index=False)["monto_abs_clp"]
        .sum()
        .sort_values("monto_abs_clp", ascending=False)
        .head(8)
    )
    grouped["categoria_short"] = grouped["categoria"].map(lambda value: _short_label(str(value), 13))
    fig = px.pie(
        grouped,
        names="categoria_short",
        values="monto_abs_clp",
        color="categoria_short",
        color_discrete_sequence=PALETTE,
        hole=0.56,
    )
    fig.update_traces(
        textinfo="none",
        customdata=grouped[["categoria"]],
        hovertemplate="%{customdata[0]}: $%{value:,.0f}<extra></extra>",
        marker=dict(line=dict(color="#ffffff", width=2)),
    )
    fig.update_layout(
        showlegend=True,
        margin=dict(l=0, r=0, t=4, b=0),
    )
    return _apply_figma_chart_style(fig)


def month_comparison_by_category_chart(
    df: pd.DataFrame,
    *,
    target_year: int | None = None,
    target_month: int | None = None,
    day_cutoff: int | None = None,
):
    if not PLOTLY_AVAILABLE:
        return None
    if df.empty:
        return _empty_chart("Sin datos para comparacion mensual")

    work = df.copy()
    work["fecha"] = pd.to_datetime(work["fecha"])
    if day_cutoff and day_cutoff > 0:
        work = work[work["fecha"].dt.day <= int(day_cutoff)]
    if work.empty:
        return _empty_chart("Sin datos para comparacion mensual")

    if target_year and target_month:
        current_period = pd.Period(year=int(target_year), month=int(target_month), freq="M")
    else:
        current_period = work["fecha"].max().to_period("M")
    previous_period = current_period - 1

    work["period"] = work["fecha"].dt.to_period("M")
    current = (
        work[work["period"] == current_period]
        .groupby("categoria", as_index=False)["monto_abs_clp"]
        .sum()
        .rename(columns={"monto_abs_clp": "este_mes"})
    )
    previous = (
        work[work["period"] == previous_period]
        .groupby("categoria", as_index=False)["monto_abs_clp"]
        .sum()
        .rename(columns={"monto_abs_clp": "mes_anterior"})
    )
    merged = current.merge(previous, on="categoria", how="outer").fillna(0)
    if merged.empty:
        return _empty_chart("Sin datos para comparacion mensual")
    merged = merged.sort_values("este_mes", ascending=False).head(6)
    merged["categoria_short"] = merged["categoria"].map(lambda value: _short_label(str(value), 13))

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=merged["categoria_short"],
            y=merged["este_mes"],
            name="Este mes",
            marker_color="#6366F1",
            marker_line_width=0,
            customdata=merged[["categoria"]],
            hovertemplate="%{customdata[0]}<br>Este mes: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=merged["categoria_short"],
            y=merged["mes_anterior"],
            name="Mes anterior",
            marker_color="#D9D9D9",
            marker_line_width=0,
            customdata=merged[["categoria"]],
            hovertemplate="%{customdata[0]}<br>Mes anterior: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        barmode="group",
        bargap=0.26,
    )
    fig.update_xaxes(tickangle=-12)
    fig.update_yaxes(tickprefix="$", separatethousands=True, tickformat="~s")
    return _apply_figma_chart_style(fig)


def category_frequency_chart(df: pd.DataFrame):
    if not PLOTLY_AVAILABLE:
        return None
    if df.empty:
        return _empty_chart("Sin datos para frecuencia por categoria")

    grouped = (
        df.groupby("categoria", as_index=False)["id"]
        .count()
        .rename(columns={"id": "frecuencia"})
        .sort_values("frecuencia", ascending=False)
        .head(8)
    )
    grouped["categoria_short"] = grouped["categoria"].map(lambda value: _short_label(str(value), 13))
    fig = px.bar(
        grouped,
        x="categoria_short",
        y="frecuencia",
        color="categoria_short",
        color_discrete_sequence=PALETTE,
    )
    fig.update_layout(showlegend=False)
    fig.update_xaxes(tickangle=-14, title="")
    fig.update_traces(
        customdata=grouped[["categoria"]],
        hovertemplate="%{customdata[0]}<br>Frecuencia: %{y}<extra></extra>",
    )
    return _apply_figma_chart_style(fig)


def weekday_chart(df: pd.DataFrame):
    if not PLOTLY_AVAILABLE:
        return None
    if df.empty:
        return _empty_chart("Sin datos para dia de semana")

    weekdays = {
        0: "Lunes",
        1: "Martes",
        2: "Miercoles",
        3: "Jueves",
        4: "Viernes",
        5: "Sabado",
        6: "Domingo",
    }
    work = df.copy()
    work["fecha"] = pd.to_datetime(work["fecha"])
    work["weekday"] = work["fecha"].dt.weekday
    grouped = work.groupby("weekday", as_index=False)["monto_abs_clp"].sum()
    grouped["dia"] = grouped["weekday"].map(weekdays)
    grouped = grouped.sort_values("weekday")

    fig = px.bar(
        grouped,
        x="dia",
        y="monto_abs_clp",
        color="dia",
        color_discrete_sequence=PALETTE,
    )
    fig.update_layout(showlegend=False)
    fig.update_yaxes(tickprefix="$", separatethousands=True, tickformat="~s")
    fig.update_traces(hovertemplate="%{x}<br>Gasto: $%{y:,.0f}<extra></extra>")
    return _apply_figma_chart_style(fig)


def monthly_trend_chart(
    df: pd.DataFrame,
    *,
    periods: int = 6,
    target_year: int | None = None,
    target_month: int | None = None,
):
    if not PLOTLY_AVAILABLE:
        return None
    if df.empty:
        return _empty_chart("Sin datos para tendencia mensual")

    work = df.copy()
    work["fecha"] = pd.to_datetime(work["fecha"])
    monthly_series = work.groupby(work["fecha"].dt.to_period("M"))["monto_abs_clp"].sum()

    if target_year and target_month:
        end_period = pd.Period(year=int(target_year), month=int(target_month), freq="M")
    else:
        end_period = monthly_series.index.max() if not monthly_series.empty else None

    if end_period is None:
        return _empty_chart("Sin datos para tendencia mensual")

    window = max(1, int(periods))
    start_period = end_period - (window - 1)
    full_range = pd.period_range(start=start_period, end=end_period, freq="M")

    if monthly_series.empty:
        monthly_series = pd.Series(0.0, index=full_range)
    else:
        monthly_series = monthly_series.reindex(full_range, fill_value=0.0)

    monthly_series.index.name = "period_obj"
    grouped = monthly_series.rename("monto_abs_clp").reset_index()
    grouped["periodo"] = grouped["period_obj"].map(
        lambda period: f"{MONTH_SHORT.get(period.month, str(period.month))} {str(period.year)[2:]}"
    )
    non_zero = grouped[grouped["monto_abs_clp"] > 0]["monto_abs_clp"]
    budget = float(non_zero.mean()) if not non_zero.empty else float(grouped["monto_abs_clp"].mean())

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=grouped["periodo"],
            y=grouped["monto_abs_clp"],
            mode="lines+markers",
            name="Gastos",
            line=dict(color="#6366F1", width=3),
            marker=dict(size=8, color="#6366F1"),
            hovertemplate="%{x}<br>Gastos: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=grouped["periodo"],
            y=[budget] * len(grouped),
            mode="lines+markers",
            name="Presupuesto",
            line=dict(color="#BDBDBD", width=2, dash="dash"),
            marker=dict(size=6, color="#BDBDBD"),
            hovertemplate="%{x}<br>Presupuesto: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.update_yaxes(tickprefix="$", separatethousands=True, tickformat="~s")
    return _apply_figma_chart_style(fig)


def projection_chart(df: pd.DataFrame):
    if not PLOTLY_AVAILABLE:
        return None
    if df.empty:
        return _empty_chart("Sin categorias estables para proyectar")

    work = df.head(8).copy()
    work["categoria_short"] = work["categoria"].map(lambda value: _short_label(str(value), 13))
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(work))]
    fig = go.Figure(
        data=[
            go.Bar(
                x=work["categoria_short"],
                y=work["proyeccion"],
                marker_color=colors,
                marker_line_width=0,
                customdata=work[["categoria", "proyeccion"]],
                hovertemplate="%{customdata[0]}<br>Proyeccion: $%{customdata[1]:,.0f}<extra></extra>",
                showlegend=False,
            )
        ]
    )
    fig.update_xaxes(tickangle=-14)
    fig.update_yaxes(tickprefix="$", separatethousands=True, tickformat="~s")
    return _apply_figma_chart_style(fig)


def projection_horizon_chart(df: pd.DataFrame):
    if not PLOTLY_AVAILABLE:
        return None
    if df.empty:
        return _empty_chart("Sin datos para escenario proyectado")

    fig = go.Figure()

    if {"banda_inf", "banda_sup"}.issubset(df.columns):
        band_df = df[df["banda_inf"].notna() & df["banda_sup"].notna()].copy()
    else:
        band_df = pd.DataFrame()

    if not band_df.empty:
        fig.add_trace(
            go.Scatter(
                x=band_df["mes"],
                y=band_df["banda_sup"],
                mode="lines",
                line=dict(width=0),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=band_df["mes"],
                y=band_df["banda_inf"],
                mode="lines",
                fill="tonexty",
                fillcolor="rgba(6, 182, 212, 0.12)",
                line=dict(width=0),
                hoverinfo="skip",
                name="Rango esperado",
            )
        )

    if "real" in df.columns and df["real"].notna().any():
        real_df = df[df["real"].notna()].copy()
        fig.add_trace(
            go.Scatter(
                x=real_df["mes"],
                y=real_df["real"],
                mode="lines+markers",
                name="Real",
                line=dict(color="#0A0A0A", width=3),
                marker=dict(size=7, color="#0A0A0A"),
                hovertemplate="%{x}<br>Real: $%{y:,.0f}<extra></extra>",
            )
        )

    proj_df = df[df["proyeccion"].notna()].copy()
    fig.add_trace(
        go.Scatter(
            x=proj_df["mes"],
            y=proj_df["proyeccion"],
            mode="lines+markers",
            name="Proyeccion",
            line=dict(color="#06B6D4", width=3, dash="dash"),
            marker=dict(size=7, color="#06B6D4"),
            hovertemplate="%{x}<br>Proyeccion: $%{y:,.0f}<extra></extra>",
        )
    )

    fig.update_yaxes(tickprefix="$", separatethousands=True, tickformat="~s")
    return _apply_figma_chart_style(fig)
