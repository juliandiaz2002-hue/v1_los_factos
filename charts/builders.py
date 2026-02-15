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


def _format_clp_short(value: float) -> str:
    num = float(value)
    if num >= 1_000_000:
        return f"${num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"${num / 1_000:.0f}K"
    return f"${num:,.0f}"


def _apply_figma_chart_style(fig):
    fig.update_layout(
        margin=dict(l=8, r=8, t=10, b=6),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Manrope, sans-serif", color="#171717", size=12),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.20,
            xanchor="left",
            x=0,
            font=dict(size=11),
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#0F172A",
            bordercolor="#0F172A",
            font=dict(color="#F8FAFC", size=12),
            namelength=-1,
        ),
        transition=dict(duration=380, easing="cubic-in-out"),
        dragmode=False,
    )
    fig.update_xaxes(
        showgrid=False,
        linecolor="#D4D4D4",
        tickfont=dict(color="#737373", size=12),
        title="",
        showspikes=True,
        spikethickness=1,
        spikecolor="#C7D2FE",
        spikemode="across",
        fixedrange=True,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#F1F1F1",
        zeroline=False,
        linecolor="#D4D4D4",
        tickfont=dict(color="#737373", size=12),
        title="",
        showspikes=False,
        fixedrange=True,
    )
    return fig


def category_distribution_chart(
    df: pd.DataFrame,
    *,
    top_n: int = 8,
    include_other: bool = True,
):
    if not PLOTLY_AVAILABLE:
        return None
    if df.empty:
        return _empty_chart("Sin datos para distribucion")

    grouped_full = (
        df.groupby("categoria", as_index=False)["monto_abs_clp"]
        .sum()
        .sort_values("monto_abs_clp", ascending=False)
    )
    if grouped_full.empty:
        return _empty_chart("Sin datos para distribucion")

    top_n = max(3, int(top_n))
    grouped = grouped_full.head(top_n).copy()
    if include_other and len(grouped_full) > top_n:
        other_value = float(grouped_full.iloc[top_n:]["monto_abs_clp"].sum())
        grouped = pd.concat(
            [
                grouped,
                pd.DataFrame([{"categoria": "Otros", "monto_abs_clp": other_value}]),
            ],
            ignore_index=True,
        )

    grouped["pct"] = grouped["monto_abs_clp"] / float(grouped["monto_abs_clp"].sum())
    grouped["categoria_short"] = grouped["categoria"].map(lambda value: _short_label(str(value), 13))
    grouped["pull"] = 0.0
    grouped.loc[grouped["monto_abs_clp"].idxmax(), "pull"] = 0.05

    total = float(grouped["monto_abs_clp"].sum())
    top_label = str(grouped.sort_values("monto_abs_clp", ascending=False).iloc[0]["categoria"])

    fig = go.Figure(
        data=[
            go.Pie(
                labels=grouped["categoria_short"],
                values=grouped["monto_abs_clp"],
                hole=0.62,
                marker=dict(colors=PALETTE, line=dict(color="#ffffff", width=2)),
                sort=False,
                direction="clockwise",
                pull=grouped["pull"],
                hovertext=grouped["categoria"],
                textinfo="none",
                hovertemplate=(
                    "<b>%{hovertext}</b><br>"
                    "Monto: $%{value:,.0f}<br>"
                    "Participacion: %{percent}<extra></extra>"
                ),
            )
        ]
    )
    fig.update_layout(
        showlegend=True,
        margin=dict(l=0, r=0, t=0, b=0),
        annotations=[
            dict(
                text=f"<b>{_format_clp_short(total)}</b><br><span style='font-size:11px;color:#6B7280'>Total</span>",
                x=0.5,
                y=0.50,
                showarrow=False,
                align="center",
                xref="paper",
                yref="paper",
            ),
            dict(
                text=f"<span style='font-size:11px;color:#6B7280'>Top: {top_label}</span>",
                x=0.5,
                y=0.40,
                showarrow=False,
                align="center",
                xref="paper",
                yref="paper",
            ),
        ],
    )
    return _apply_figma_chart_style(fig)


def month_comparison_by_category_chart(
    df: pd.DataFrame,
    *,
    target_year: int | None = None,
    target_month: int | None = None,
    day_cutoff: int | None = None,
    top_n: int = 6,
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
    merged["max_value"] = merged[["este_mes", "mes_anterior"]].max(axis=1)
    merged = merged.sort_values("max_value", ascending=False).head(max(3, int(top_n)))
    merged["categoria_short"] = merged["categoria"].map(lambda value: _short_label(str(value), 13))
    merged["delta"] = merged["este_mes"] - merged["mes_anterior"]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=merged["categoria_short"],
            y=merged["este_mes"],
            name="Este mes",
            marker_color="#6366F1",
            marker_line_width=0,
            opacity=0.95,
            customdata=merged[["categoria", "delta"]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Este mes: $%{y:,.0f}<br>"
                "Delta: $%{customdata[1]:,.0f}<extra></extra>"
            ),
        )
    )
    fig.add_trace(
        go.Bar(
            x=merged["categoria_short"],
            y=merged["mes_anterior"],
            name="Mes anterior",
            marker_color="#D9D9D9",
            marker_line_width=0,
            opacity=0.88,
            customdata=merged[["categoria", "delta"]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Mes anterior: $%{y:,.0f}<br>"
                "Delta: $%{customdata[1]:,.0f}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        barmode="group",
        bargap=0.30,
        bargroupgap=0.14,
        barcornerradius=6,
    )
    fig.update_xaxes(tickangle=-10)
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
    grouped["trend"] = grouped["monto_abs_clp"].rolling(window=min(3, len(grouped)), min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=grouped["periodo"],
            y=grouped["monto_abs_clp"],
            mode="lines+markers",
            name="Gastos",
            line=dict(color="#6366F1", width=3.2, shape="spline", smoothing=0.45),
            marker=dict(size=8, color="#6366F1", line=dict(color="white", width=1.5)),
            fill="tozeroy",
            fillcolor="rgba(99, 102, 241, 0.12)",
            hovertemplate="%{x}<br>Gastos: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=grouped["periodo"],
            y=grouped["trend"],
            mode="lines",
            name="Tendencia",
            line=dict(color="#A78BFA", width=2, dash="dot"),
            hovertemplate="%{x}<br>Tendencia: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=grouped["periodo"],
            y=[budget] * len(grouped),
            mode="lines",
            name="Presupuesto",
            line=dict(color="#BDBDBD", width=2, dash="dash"),
            hovertemplate="%{x}<br>Presupuesto: $%{y:,.0f}<extra></extra>",
        )
    )
    if not grouped.empty:
        latest = grouped.iloc[-1]
        fig.add_annotation(
            x=latest["periodo"],
            y=latest["monto_abs_clp"],
            text=f"{_format_clp_short(float(latest['monto_abs_clp']))}",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-28,
            bgcolor="rgba(99,102,241,0.14)",
            bordercolor="#C7D2FE",
            font=dict(size=11, color="#4338CA"),
        )
    fig.update_yaxes(tickprefix="$", separatethousands=True, tickformat="~s")
    return _apply_figma_chart_style(fig)


def projection_chart(df: pd.DataFrame, *, top_n: int = 8):
    if not PLOTLY_AVAILABLE:
        return None
    if df.empty:
        return _empty_chart("Sin categorias estables para proyectar")

    work = df.head(max(4, int(top_n))).copy()
    work["categoria_short"] = work["categoria"].map(lambda value: _short_label(str(value), 13))
    color_map = {"Alta": "#6366F1", "Media": "#8B5CF6", "Baja": "#94A3B8"}
    work["bar_color"] = work["recurrencia_label"].map(color_map).fillna("#6366F1")
    work = work.sort_values("proyeccion", ascending=True)
    fig = go.Figure(
        data=[
            go.Bar(
                x=work["proyeccion"],
                y=work["categoria_short"],
                orientation="h",
                marker_color=work["bar_color"],
                marker_line_width=0,
                customdata=work[["categoria", "proyeccion", "recurrencia_label"]],
                text=work["proyeccion"].map(_format_clp_short),
                textposition="outside",
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Proyeccion: $%{customdata[1]:,.0f}<br>"
                    "Recurrencia: %{customdata[2]}<extra></extra>"
                ),
                showlegend=False,
            )
        ]
    )
    fig.update_layout(
        bargap=0.24,
        barcornerradius=6,
    )
    fig.update_xaxes(tickprefix="$", separatethousands=True, tickformat="~s")
    fig.update_yaxes(tickfont=dict(size=11))
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
                fillcolor="rgba(6, 182, 212, 0.14)",
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
                line=dict(color="#0A0A0A", width=3.2, shape="spline", smoothing=0.45),
                marker=dict(size=7, color="#0A0A0A", line=dict(color="white", width=1.3)),
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
            line=dict(color="#06B6D4", width=3.2, dash="dot", shape="spline", smoothing=0.45),
            marker=dict(size=7, color="#06B6D4", line=dict(color="white", width=1.2)),
            hovertemplate="%{x}<br>Proyeccion: $%{y:,.0f}<extra></extra>",
        )
    )

    if len(df) > 1:
        current_label = str(df.iloc[1]["mes"])
        fig.add_vline(x=current_label, line_width=1, line_dash="dash", line_color="#CBD5E1")
        fig.add_annotation(
            x=current_label,
            y=1.02,
            yref="paper",
            text="Mes actual",
            showarrow=False,
            font=dict(size=10, color="#64748B"),
            bgcolor="rgba(248,250,252,0.95)",
            bordercolor="#CBD5E1",
            borderwidth=1,
            borderpad=4,
        )

    fig.update_yaxes(tickprefix="$", separatethousands=True, tickformat="~s")
    return _apply_figma_chart_style(fig)
